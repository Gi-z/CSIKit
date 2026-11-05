"""Atheros CSI Tool reader.

There is no Atheros capture in the repository, so these tests build files
with tests/csikit_testing/synthetic.py. They pin CSIKit's current decoding
convention; whether that convention matches the original tool is tracked in
NEEDS_GROUND_TRUTH (csiread disagrees on element order and the +1 offset).
"""
import numpy as np
import pytest

from CSIKit.reader import ATHBeamformReader, get_reader
from csikit_testing import read_quietly
from csikit_testing.known_issues import ATHEROS_DROPS_TRAILING_FRAMES, known_bug
from csikit_testing.synthetic import atheros_record


def random_csi(rng, tones=56, nr=3, nc=2):
    shape = (tones, nr, nc)
    return rng.integers(-500, 500, shape) + 1j * rng.integers(-500, 500, shape)


@pytest.fixture
def capture(tmp_path):
    rng = np.random.default_rng(1234)
    truth = [random_csi(rng) for _ in range(5)]
    data = b"".join(
        atheros_record(1_000_000 + i * 10_000, csi, rssi=(40 + i, 38, 36, 0), payload_len=60)
        for i, csi in enumerate(truth)
    )
    path = tmp_path / "atheros.dat"
    path.write_bytes(data)
    return path, truth


def test_detected_by_get_reader(capture):
    path, _ = capture
    assert isinstance(get_reader(str(path)), ATHBeamformReader)


def test_header_fields(capture):
    path, truth = capture
    data = read_quietly(ATHBeamformReader(), path)
    assert len(data.frames) == len(truth)
    assert data.bandwidth == 20 and data.chipset == "QCA93XX"
    for i, frame in enumerate(data.frames):
        assert (frame.num_tones, frame.nr, frame.nc) == (56, 3, 2)
        assert frame.tx_channel == 2437
        assert frame.rssi == 40 + i
        assert frame.payload_length == 60
    np.testing.assert_allclose(data.timestamps, np.arange(5) * 0.01, atol=1e-9)


def test_csi_decoding_convention(capture):
    # Current convention: matrix is (tones, nc, nr) and every component is
    # offset by +1 relative to the packed 10-bit value.
    path, truth = capture
    data = read_quietly(ATHBeamformReader(), path)
    for frame, expected in zip(data.frames, truth):
        np.testing.assert_array_equal(frame.csi_matrix, expected.transpose(0, 2, 1) + (1 + 1j))


def test_40mhz_flag(tmp_path):
    rng = np.random.default_rng(0)
    path = tmp_path / "ht40.dat"
    path.write_bytes(b"".join(atheros_record(i, random_csi(rng, tones=114), bandwidth=1) for i in range(3)))
    assert read_quietly(ATHBeamformReader(), path).bandwidth == 40


def test_truncated_final_record_is_ignored(capture, tmp_path):
    path, truth = capture
    truncated = tmp_path / "truncated.dat"
    truncated.write_bytes(path.read_bytes()[:-100])
    assert len(read_quietly(ATHBeamformReader(), truncated).frames) == len(truth) - 1


@known_bug(ATHEROS_DROPS_TRAILING_FRAMES)
def test_small_records_are_all_read(tmp_path):
    # 1x1, 56 tones: ~170-byte records, below the reader's 420-byte end-of-file guard.
    zeros = np.zeros((56, 1, 1))
    path = tmp_path / "small.dat"
    path.write_bytes(b"".join(atheros_record(i, zeros + i + 1j * i) for i in range(10)))
    assert len(read_quietly(ATHBeamformReader(), path).frames) == 10
