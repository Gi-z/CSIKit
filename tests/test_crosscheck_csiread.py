"""Cross-check CSIKit against csiread, an independent CSI parser.

Optional: skipped unless csiread is installed (``pip install -e .[crosscheck]``).
Agreement between two independent implementations is strong evidence both
are right; disagreements that haven't been resolved are marked non-strict
xfail and tracked in NEEDS_GROUND_TRUTH.
"""
import collections
import contextlib
import io

import numpy as np
import pytest

from CSIKit.reader import ATHBeamformReader, IWLBeamformReader, NEXBeamformReader, PicoScenesBeamformReader
from csikit_testing import read_cached, read_quietly, repo_path
from csikit_testing.known_issues import NEEDS_GROUND_TRUTH
from csikit_testing.samples import get
from csikit_testing.synthetic import atheros_record

csiread = pytest.importorskip("csiread")


def unverified(what):
    return pytest.mark.xfail(strict=False, reason=f"unresolved disagreement ({what}), see {NEEDS_GROUND_TRUTH.ref}")


def quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


# --- Nexmon ---------------------------------------------------------------------

NEXMON = [
    ("CSIKit/data/nexmon/example_4339.pcap", "4339"),
    ("CSIKit/data/nexmon/example_43455c0.pcap", "43455c0"),
    ("CSIKit/data/nexmon/test.pcap", "43455c0"),
    ("CSIKit/data/nexmon/example_4358.pcap", "4358"),
    ("CSIKit/data/nexmon/example_4366c0.pcap", "4366c0"),
]


@pytest.mark.parametrize(
    "path, chip",
    [pytest.param(p, c, id=p.rsplit("/", 1)[-1], marks=get(p).marks()) for p, c in NEXMON],
)
def test_nexmon_matches_csiread(path, chip):
    ref = quiet(csiread.Nexmon, str(repo_path(path)), chip=chip, bw=80)
    quiet(ref.read)
    # Sequence numbers repeat (and multi-stream frames share one), so match on
    # capture time + stream identity, falling back to stream identity alone for
    # the extra streams merged into a multi-stream frame.
    by_time = collections.defaultdict(list)
    by_stream = collections.defaultdict(list)
    for i, (sec, usec, seq, core, ss) in enumerate(zip(ref.sec, ref.usec, ref.seq, ref.core, ref.spatial)):
        by_time[(int(sec), int(usec), int(seq), int(core), int(ss))].append(i)
        by_stream[(int(seq), int(core), int(ss))].append(i)

    data = read_quietly(NEXBeamformReader(fill_skipped_frames=False), repo_path(path))
    compared = 0
    for frame in data.frames:
        matrix = frame.csi_matrix.reshape(256, -1)
        if matrix.shape[1] == 1:
            sec = int(frame.timestamp)
            usec = int(round((frame.timestamp - sec) * 1e6))
            candidates = [by_time[(sec, usec + d, frame.sequence_no, frame.core, frame.spatial_stream)]
                          for d in (0, -1, 1)]
            candidates = [[i for c in candidates for i in c]]
        else:  # (256, spatial_stream, core) batched frame
            candidates = [by_stream[(frame.sequence_no, 0, ss)] for ss in range(matrix.shape[1])]
        for col, cands in enumerate(candidates):
            assert cands, f"no csiread packet for seq {frame.sequence_no}, column {col}"
            assert any(np.allclose(matrix[:, col], ref.csi[i], atol=1e-6) for i in cands)
            compared += 1
    assert compared > 0


# --- Intel IWL5300 (.dat) ---------------------------------------------------------

@pytest.mark.parametrize("path", ["CSIKit/data/intel/example.dat", "CSIKit/data/intel/log.all_csi.6.7.6.dat"])
def test_iwl5300_matches_csiread(path):
    ref = quiet(csiread.Intel, str(repo_path(path)), nrxnum=3, ntxnum=3, if_report=False)
    quiet(ref.read)
    data = read_cached(path)
    assert ref.count == len(data.frames)
    for i, frame in enumerate(data.frames):
        n_rx, n_tx = frame.n_rx, frame.n_tx
        np.testing.assert_allclose(frame.csi_matrix, ref.csi[i, :, :n_rx, :n_tx], atol=1e-6)


# --- PicoScenes ---------------------------------------------------------------------

def _picoscenes_ref(path):
    ref = quiet(csiread.Picoscenes, str(repo_path(path)), {"CSI": [64, 3, 4]}, if_report=False)
    quiet(ref.read)
    return ref.raw["CSI"]


def _kept_tones(subcarrier_index):
    """csiread lists the tones it kept (pilots removed), then pads by repeating the last one."""
    kept = []
    for k in (int(k) for k in subcarrier_index):
        if kept and k <= kept[-1]:
            break
        kept.append(k)
    return kept


AX2XX = [
    pytest.param("CSIKit/data/pico/picoscenes_ax200_example.csi", id="ax200_example"),
    pytest.param("CSIKit/data/intel/rx_7_211206_160935.csi", id="ax210"),
    pytest.param("CSIKit/data/intel/rx_8_211119_171706.csi", id="ax200"),
]


@pytest.mark.parametrize("path", AX2XX)
def test_picoscenes_ax2xx_dimensions_match_csiread(path):
    # These captures mix 52-tone legacy and 56-tone HT frames; both parsers
    # must agree on every frame's tone and antenna counts.
    ref = _picoscenes_ref(path)
    data = read_cached(path)
    assert len(ref) == len(data.frames)
    for i, frame in enumerate(data.frames):
        info = ref["Info"][i]
        assert frame.csi_matrix.shape == (int(info["NumTones"]), int(info["NumRx"]), int(info["NumTx"]))


@unverified("AX2xx tone indexing: csiread drops 4 tones per frame and relabels the rest")
@pytest.mark.parametrize("path", AX2XX)
def test_picoscenes_ax2xx_values_match_csiread(path):
    # CSIKit keeps every tone except DC, pilots included. csiread drops 4
    # tones, but the indices it labels the remainder with don't line up with
    # the standard pilot positions, so aligning the two is unresolved.
    ref = _picoscenes_ref(path)
    for i, frame in enumerate(read_cached(path).frames):
        nt, nrx, ntx = frame.csi_matrix.shape
        tones = _kept_tones(ref["SubcarrierIndex"][i][:nt])
        positions = [k + nt // 2 if k < 0 else k + nt // 2 - 1 for k in tones]
        np.testing.assert_allclose(frame.csi_matrix[positions], ref["CSI"][i][:len(tones), :nrx, :ntx], atol=1e-6)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(get("CSIKit/data/pico/picoscenes_iwl5300_example.csi").path, id="2rx",
                     marks=get("CSIKit/data/pico/picoscenes_iwl5300_example.csi").marks()),
        pytest.param(get("CSIKit/data/pico/picoscenes_iwl5300_example2.csi").path, id="3rx",
                     marks=[*get("CSIKit/data/pico/picoscenes_iwl5300_example2.csi").marks(),
                            unverified("IWL5300 antenna permutation")]),
    ],
)
def test_picoscenes_iwl5300_matches_csiread(path):
    ref = _picoscenes_ref(path)
    data = read_cached(path)
    for i, frame in enumerate(data.frames):
        nt, nrx, ntx = frame.csi_matrix.shape
        np.testing.assert_allclose(frame.csi_matrix, ref["CSI"][i][:nt, :nrx, :ntx], atol=1e-6)


# --- ESP32 ----------------------------------------------------------------------------

ESP32 = "CSIKit/data/esp32/example_fast_100hz_pitraffic.csv"


@pytest.fixture(scope="module")
def esp32_ref(tmp_path_factory):
    # csiread expects the CSV without its header line.
    headerless = tmp_path_factory.mktemp("esp32") / "noheader.csv"
    headerless.write_text(repo_path(ESP32).read_text().split("\n", 1)[1])
    ref = quiet(csiread.ESP32, str(headerless), csi_only=True)
    quiet(ref.read)
    return ref.csi


def test_esp32_amplitude_matches_csiread(esp32_ref):
    data = read_cached(ESP32)
    assert len(esp32_ref) == len(data.frames)
    for frame, expected in zip(data.frames, esp32_ref):
        np.testing.assert_allclose(np.abs(frame.csi_matrix[:, 0]), np.abs(expected), rtol=1e-6)


def test_esp32_complex_values_match_csiread(esp32_ref):
    for frame, expected in zip(read_cached(ESP32).frames, esp32_ref):
        np.testing.assert_allclose(frame.csi_matrix[:, 0], expected, atol=1e-6)


# --- Atheros (synthetic) --------------------------------------------------------------

@unverified("Atheros element order and +1 offset")
def test_atheros_matches_csiread(tmp_path):
    rng = np.random.default_rng(7)
    shape = (56, 3, 2)
    truth = [rng.integers(-500, 500, shape) + 1j * rng.integers(-500, 500, shape) for _ in range(3)]
    path = tmp_path / "atheros.dat"
    path.write_bytes(b"".join(atheros_record(i, csi) for i, csi in enumerate(truth)))
    ref = quiet(csiread.Atheros, str(path), nrxnum=3, ntxnum=2, tones=56, if_report=False)
    quiet(ref.read)
    data = read_quietly(ATHBeamformReader(), path)
    for frame, expected in zip(data.frames, ref.csi):
        np.testing.assert_allclose(frame.csi_matrix.transpose(0, 2, 1), expected, atol=1e-6)
