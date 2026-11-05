"""CSIKit.csi.CSIData: frame collection, MAC filtering and metadata."""
import numpy as np
import pytest

from CSIKit.csi import CSIData


class Frame:
    def __init__(self, csi_matrix, **attrs):
        self.csi_matrix = csi_matrix
        self.__dict__.update(attrs)


def test_push_frame_keeps_frames_and_timestamps_aligned():
    data = CSIData("f.dat", "backend", "chip")
    frames = [Frame(np.zeros((30, 1, 1))) for _ in range(3)]
    for i, frame in enumerate(frames):
        data.push_frame(frame, i * 0.5)
    assert data.frames == frames
    assert data.timestamps == [0.0, 0.5, 1.0]


@pytest.mark.parametrize("attr", ["source_mac", "mac"])
def test_filter_mac_is_case_insensitive(attr):
    data = CSIData(filter_mac="aa:bb:cc:dd:ee:ff")
    data.push_frame(Frame(np.zeros(4), **{attr: "AA:BB:CC:DD:EE:FF"}), 0.0)
    data.push_frame(Frame(np.zeros(4), **{attr: "11:22:33:44:55:66"}), 1.0)
    assert len(data.frames) == 1 and data.timestamps == [0.0]


def _with_frames(shape, n=101, duration=1.0, **attrs):
    data = CSIData("f.dat", "backend", "chip")
    data.bandwidth = 20
    for t in np.linspace(0, duration, n):
        data.push_frame(Frame(np.ones(shape, dtype=complex), **attrs), float(t))
    return data


def test_metadata_summary():
    meta = _with_frames((30, 3, 2), rssi=-40).get_metadata()
    assert (meta.chipset, meta.backend, meta.bandwidth) == ("chip", "backend", 20)
    assert meta.antenna_config == "3 Rx, 2 Tx"
    assert (meta.frames, meta.subcarriers, meta.csi_shape) == (101, 30, (30, 3, 2))
    assert meta.time_length == pytest.approx(1.0)
    assert meta.average_sample_rate == pytest.approx(101.0)
    assert meta.average_rssi == -40


def test_metadata_single_antenna():
    assert _with_frames((64, 1), rssi=-60).get_metadata().antenna_config == "1 Rx, 1 Tx"


def test_metadata_of_empty_data_raises_a_clear_error():
    with pytest.raises(ValueError, match="No CSI frames were read from empty.dat"):
        CSIData("empty.dat").get_metadata()
