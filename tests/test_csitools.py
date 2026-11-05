"""CSIKit.util.csitools: get_CSI matrix assembly and RSS-based scaling."""
import numpy as np
import pytest

from CSIKit.csi import CSIData
from CSIKit.util import csitools
from CSIKit.util.matlab import dbinv
from csikit_testing.known_issues import GET_CSI_DROPPED_FRAMES, known_bug


class Frame:
    def __init__(self, csi_matrix, **attrs):
        self.csi_matrix = csi_matrix
        self.__dict__.update(attrs)


def make_data(matrices, timestamps=None):
    data = CSIData("synthetic.dat", "test backend", "test chipset")
    for i, matrix in enumerate(matrices):
        data.push_frame(Frame(matrix), timestamps[i] if timestamps is not None else i * 0.01)
    return data


def random_csi(shape, n=5, seed=0):
    rng = np.random.default_rng(seed)
    return [rng.normal(size=shape) + 1j * rng.normal(size=shape) for _ in range(n)]


@pytest.mark.parametrize("shape", [(30, 3, 2), (56, 2, 1), (256, 4, 4)])
def test_multi_antenna_layout_is_frames_subcarriers_rx_tx(shape):
    mats = random_csi(shape)
    csi, n_frames, n_subcarriers = csitools.get_CSI(make_data(mats), metric="complex")
    assert (n_frames, n_subcarriers) == (5, shape[0])
    assert csi.shape == (5, *shape)
    np.testing.assert_array_equal(csi, np.stack(mats))


def test_single_antenna_1d_frames():
    mats = random_csi((64,))
    csi, n_frames, n_subcarriers = csitools.get_CSI(make_data(mats), metric="complex")
    assert csi.shape == (5, 64, 1, 1)
    np.testing.assert_array_equal(csi[:, :, 0, 0], np.stack(mats))


def test_single_antenna_column_frames():
    # (subcarriers, 1) is what the ESP32 and single-stream Nexmon readers produce.
    mats = random_csi((64, 1))
    csi, _, _ = csitools.get_CSI(make_data(mats), metric="complex")
    assert csi.shape == (5, 64, 1, 1)
    np.testing.assert_array_equal(csi[:, :, :, 0], np.stack(mats))


def test_metrics():
    mats = random_csi((30, 3, 1))
    data = make_data(mats)
    stacked = np.stack(mats)
    amp_db, _, _ = csitools.get_CSI(data)  # default: amplitude in dB
    np.testing.assert_allclose(amp_db, 20 * np.log10(np.abs(stacked)))
    amp, _, _ = csitools.get_CSI(data, metric="amplitude", extract_as_dBm=False)
    np.testing.assert_allclose(amp, np.abs(stacked))
    phase, _, _ = csitools.get_CSI(data, metric="phase")
    np.testing.assert_allclose(phase, np.angle(stacked))


def test_squeeze_output():
    csi, _, _ = csitools.get_CSI(make_data(random_csi((30, 3, 1))), metric="complex", squeeze_output=True)
    assert csi.shape == (5, 30, 3)


def _mixed_antenna_data():
    three_rx = random_csi((30, 3, 1), n=3, seed=1)
    two_rx = random_csi((30, 2, 1), n=1, seed=2)
    return make_data([three_rx[0], three_rx[1], two_rx[0], three_rx[2]])


@known_bug(GET_CSI_DROPPED_FRAMES)
def test_frame_count_matches_matrix_when_frames_are_dropped():
    csi, n_frames, _ = csitools.get_CSI(_mixed_antenna_data(), metric="complex")
    assert csi.shape[0] == 3  # the 2-Rx frame can't fit a 3-Rx matrix
    assert n_frames == csi.shape[0]


@known_bug(GET_CSI_DROPPED_FRAMES)
def test_get_csi_does_not_modify_its_input():
    data = _mixed_antenna_data()
    before = list(data.timestamps)
    csitools.get_CSI(data, metric="complex")
    assert data.timestamps == before


@pytest.mark.parametrize("rss", [-30, -60, -85])
def test_scale_csi_frame_sets_mean_subcarrier_power_to_rss(rss):
    csi = random_csi((64, 1), n=1)[0]
    scaled = csitools.scale_csi_frame(csi, rss)
    assert np.mean(np.abs(scaled) ** 2) == pytest.approx(dbinv(rss))
    # Scaling is a single real factor: phase is untouched.
    np.testing.assert_allclose(np.angle(scaled), np.angle(csi))
