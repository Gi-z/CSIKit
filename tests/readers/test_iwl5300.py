"""Linux 802.11n CSI Tool (Intel IWL5300) .dat reader.

Bit-exact agreement with the toolkit's own MATLAB parser is covered in
tests/matlab/intel/test_intel.py; these tests cover structure and timing.
"""
import math

import numpy as np
import pytest

from CSIKit.reader import IWLBeamformReader
from csikit_testing import read_cached, read_fresh, read_quietly, repo_path
from csikit_testing.known_issues import INFO_INTEL_RSSI_NOT_DBM, known_bug
from csikit_testing.samples import IWL, by_reader
from csikit_testing.synthetic import IWL_BFEE_CODE, iwl_records, set_iwl_timestamps

IWL_SAMPLES = [pytest.param(s.path, id=s.id) for s in by_reader(IWL)]
EXAMPLE = "CSIKit/data/intel/example.dat"


def complete_bfee_records(raw: bytes) -> int:
    return sum(
        1 for off, size, code in iwl_records(raw)
        if code == IWL_BFEE_CODE and off + 2 + size <= len(raw)
    )


@pytest.mark.parametrize("path", IWL_SAMPLES)
def test_one_frame_per_complete_bfee_record(path):
    assert len(read_cached(path).frames) == complete_bfee_records(repo_path(path).read_bytes())


@pytest.mark.parametrize("path", IWL_SAMPLES)
def test_matrix_shape_matches_header(path):
    for frame in read_cached(path).frames:
        assert frame.csi_matrix.shape == (30, frame.n_rx, frame.n_tx)
        assert 1 <= frame.n_rx <= 3 and 1 <= frame.n_tx <= 3


@pytest.mark.parametrize("path", IWL_SAMPLES)
def test_timestamps_are_seconds_since_first_frame(path):
    # Not asserting monotonicity: the los_*.dat captures contain genuine
    # backwards jumps in the card's timestamp_low between consecutive frames.
    data = read_cached(path)
    raw = np.array([f.timestamp_low for f in data.frames], dtype=np.int64)
    np.testing.assert_allclose(data.timestamps, (raw - raw[0]) * 1e-6, atol=1e-9)


def _with_timestamps(tmp_path, start, step):
    raw = repo_path(EXAMPLE).read_bytes()
    n = complete_bfee_records(raw)
    path = tmp_path / "patched.dat"
    path.write_bytes(set_iwl_timestamps(raw, [start + i * step for i in range(n)]))
    return read_quietly(IWLBeamformReader(), path), n


def test_timestamps_are_microseconds_since_first_frame(tmp_path):
    data, n = _with_timestamps(tmp_path, start=5_000_000, step=10_000)
    np.testing.assert_allclose(data.timestamps, np.arange(n) * 0.01, atol=1e-9)


def test_timestamp_low_wraparound_keeps_time_increasing(tmp_path):
    # timestamp_low is a 32-bit microsecond counter: it wraps every ~71.6 minutes.
    data, n = _with_timestamps(tmp_path, start=2**32 - 5 * 10_000, step=10_000)
    np.testing.assert_allclose(data.timestamps, np.arange(n) * 0.01, atol=1e-9)


def test_timestamp_low_wraps_repeatedly(tmp_path):
    step = 2**30  # a quarter of the counter range (~18 minutes): wraps every 4 frames
    data, n = _with_timestamps(tmp_path, start=0, step=step)
    np.testing.assert_allclose(data.timestamps, np.arange(n) * step * 1e-6, rtol=1e-12)


@pytest.mark.parametrize(
    "rssi, agc, expected",
    [
        ((30, 0, 0), 20, 30 - 44 - 20),  # zero RSSIs are ignored
        ((30, 30, 0), 20, 10 * math.log10(2 * 10 ** 3) - 44 - 20),
        ((30, 30, 30), 0, 10 * math.log10(3 * 10 ** 3) - 44),
    ],
)
def test_get_total_rss_matches_toolkit_formula(rssi, agc, expected):
    # get_total_rss.m: db(dbinv(a) + dbinv(b) + dbinv(c), 'pow') - 44 - agc
    assert IWLBeamformReader.get_total_rss(*rssi, agc) == pytest.approx(expected)


@known_bug(INFO_INTEL_RSSI_NOT_DBM)
def test_metadata_average_rssi_is_in_dbm():
    data = read_fresh("CSIKit/data/intel/log.all_csi.6.7.6.dat")
    expected = np.mean([
        IWLBeamformReader.get_total_rss(f.rssi_a, f.rssi_b, f.rssi_c, f.agc) for f in data.frames
    ])
    assert data.get_metadata().average_rssi == pytest.approx(expected, abs=0.1)
