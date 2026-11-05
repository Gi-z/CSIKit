"""FeitCSI .csi reader (Intel AX200/AX210)."""
import re

import numpy as np
import pytest

from CSIKit.reader import FeitCSIBeamformReader
from csikit_testing import read_cached, read_quietly, repo_path
from csikit_testing.known_issues import FEITCSI_MULTI_TX_INTERPOLATION, FILTER_MAC_BROKEN, known_bug
from csikit_testing.samples import FEIT, by_reader

FEIT_PARAMS = [pytest.param(s.path, id=s.id) for s in by_reader(FEIT)]

# Standard 802.11 tone counts per (format, channel width).
TONES = {
    ("HT", "20"): 56, ("HT", "40"): 114,
    ("VHT", "20"): 56, ("VHT", "40"): 114, ("VHT", "80"): 242, ("VHT", "160"): 484,
    ("HE", "20"): 242, ("HE", "40"): 484, ("HE", "80"): 996, ("HE", "160"): 1992,
}
HT20_PILOTS = [7, 21, 34, 48]


def format_from_filename(path):
    fmt, width = re.match(r"(HESU|VHT|HT)(\d+)_", path.rsplit("/", 1)[-1]).groups()
    return ("HE" if fmt == "HESU" else fmt), width


@pytest.mark.parametrize("path", FEIT_PARAMS)
def test_rate_format_and_width_decoded(path):
    fmt, width = format_from_filename(path)
    data = read_cached(path)
    assert data.backend == "FeitCSI"
    assert str(data.bandwidth) == width
    for frame in data.frames:
        assert (frame.rate_format, frame.channel_width) == (fmt, width)


@pytest.mark.parametrize("path", FEIT_PARAMS)
def test_subcarrier_count_matches_standard(path):
    expected = TONES[format_from_filename(path)]
    for frame in read_cached(path).frames:
        assert frame.num_subcarriers == expected
        assert frame.csi_matrix.shape == (expected, frame.num_rx, frame.num_tx)


@pytest.mark.parametrize("path", FEIT_PARAMS)
def test_timestamps_start_at_zero_and_increase(path):
    ts = np.asarray(read_cached(path).timestamps)
    assert ts[0] == 0
    assert np.all(np.diff(ts) > 0)


def _pilot_csi(n_rx, n_tx):
    csi = np.ones((56, n_rx, n_tx), dtype=complex)
    csi[HT20_PILOTS] = 100  # outliers the interpolation should smooth away
    return {"header": {"rate_format": "HT", "channel_width": "20"}, "csi_matrix": csi}


def test_pilot_interpolation_single_tx():
    out = FeitCSIBeamformReader().interpolate(_pilot_csi(2, 1))["csi_matrix"]
    np.testing.assert_allclose(np.abs(out), 1, atol=1e-9)


@known_bug(FEITCSI_MULTI_TX_INTERPOLATION, raises=ValueError)
def test_pilot_interpolation_multiple_tx():
    out = FeitCSIBeamformReader().interpolate(_pilot_csi(2, 2))["csi_matrix"]
    np.testing.assert_allclose(np.abs(out), 1, atol=1e-9)


@known_bug(FILTER_MAC_BROKEN, raises=AttributeError)
def test_filter_mac():
    path = repo_path("CSIKit/data/feitcsi/HT20_2452.csi")
    everything = read_cached("CSIKit/data/feitcsi/HT20_2452.csi")
    assert len(read_quietly(FeitCSIBeamformReader(), path, filter_mac="00:16:EA:12:34:56").frames) == len(everything.frames)
    assert len(read_quietly(FeitCSIBeamformReader(), path, filter_mac="02:00:00:00:00:01").frames) == 0
