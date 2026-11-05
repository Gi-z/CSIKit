"""CSIKit.util.csitools: get_CSI matrix assembly and RSS-based scaling."""
import numpy as np
import pytest

from CSIKit.csi import CSIData
from CSIKit.util import csitools
from CSIKit.util.matlab import dbinv


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
    return make_data([three_rx[0], three_rx[1], two_rx[0], three_rx[2]]), [0, 1, 3]


def test_frame_count_matches_matrix_when_frames_are_left_out():
    data, kept = _mixed_antenna_data()
    with pytest.warns(UserWarning, match="3 of 4 frames"):
        csi, n_frames, _, indices = csitools.get_CSI(data, metric="complex", return_indices=True)
    assert csi.shape[0] == n_frames == 3  # the 2-Rx frame can't fit a 3-Rx matrix
    assert indices == kept
    np.testing.assert_array_equal(csi, np.stack([data.frames[i].csi_matrix for i in kept]))


def test_get_csi_does_not_modify_its_input():
    data, _ = _mixed_antenna_data()
    before = list(data.timestamps)
    with pytest.warns(UserWarning):
        csitools.get_CSI(data, metric="complex")
    assert data.timestamps == before


def test_mixed_tone_counts_use_the_most_common_shape_without_padding():
    # e.g. PicoScenes captures mixing 52-tone legacy and 56-tone HT frames,
    # with a legacy frame first.
    legacy = random_csi((52, 2, 1), n=1, seed=3)
    ht = random_csi((56, 2, 1), n=3, seed=4)
    data = make_data([legacy[0], *ht])
    with pytest.warns(UserWarning, match="3 of 4 frames"):
        csi, n_frames, n_subcarriers, indices = csitools.get_CSI(data, metric="complex", return_indices=True)
    assert (csi.shape, n_frames, n_subcarriers, indices) == ((3, 56, 2, 1), 3, 56, [1, 2, 3])
    np.testing.assert_array_equal(csi, np.stack(ht))


def test_return_indices_for_uniform_frames():
    data = make_data(random_csi((30, 3, 1)))
    _, n_frames, _, indices = csitools.get_CSI(data, return_indices=True)
    assert indices == list(range(n_frames)) == list(range(5))


def test_no_frames_raises_a_clear_error():
    with pytest.raises(ValueError, match="No CSI frames"):
        csitools.get_CSI(CSIData("empty.dat"))


@pytest.mark.parametrize("rss", [-30, -60, -85])
def test_scale_csi_frame_sets_mean_subcarrier_power_to_rss(rss):
    csi = random_csi((64, 1), n=1)[0]
    scaled = csitools.scale_csi_frame(csi, rss)
    assert np.mean(np.abs(scaled) ** 2) == pytest.approx(dbinv(rss))
    # Scaling is a single real factor: phase is untouched.
    np.testing.assert_allclose(np.angle(scaled), np.angle(csi))
