"""PicoScenes .csi reader (Intel AX200/AX210, IWL5300 and USRP front-ends)."""
import numpy as np
import pytest

from CSIKit.reader import PicoScenesBeamformReader
from csikit_testing import read_cached, read_quietly, repo_path
from csikit_testing.known_issues import PICOSCENES_LOG_EXCEPTION, known_bug
from csikit_testing.samples import PICO, by_reader

DEVICES = {
    "picoscenes_ax200_example.csi": "Intel WiFi6 AX200",
    "picoscenes_ax200_agcdemo.csi": "Intel WiFi6 AX200",
    "ax200_demo.csi": "Intel WiFi6 AX200",
    "ax200_agc_demo.csi": "Intel WiFi6 AX200",
    "rx_7_211206_160817.csi": "Intel WiFi6E AX210",
    "rx_7_211206_160935.csi": "Intel WiFi6E AX210",
    "rx_8_211119_171706.csi": "Intel WiFi6 AX200",
    "rx_8_211206_152319.csi": "Intel WiFi6 AX200",
    "rx_8_211206_161457.csi": "Intel WiFi6 AX200",
    "rx_8_211217_191036.csi": "Intel WiFi6 AX200",
    "picoscenes_iwl5300_example.csi": "Intel IWL5300",
    "picoscenes_iwl5300_example2.csi": "Intel IWL5300",
    "picoscenes_usrpb210_example.csi": "USRP SDR",
}

PICO_PARAMS = [s.param() for s in by_reader(PICO)]


@pytest.mark.parametrize("sample", PICO_PARAMS)
def test_device_identified(sample):
    data = read_cached(sample.path)
    assert data.backend == "PicoScenes"
    assert data.chipset == DEVICES[sample.path.rsplit("/", 1)[-1]]
    assert data.bandwidth == 20


@pytest.mark.parametrize("sample", PICO_PARAMS)
def test_matrix_shape_matches_frame_header(sample):
    for frame in read_cached(sample.path).frames:
        shape = frame.csi_matrix.shape
        if hasattr(frame, "n_rx"):  # Intel frames
            assert shape[1:] == (frame.n_rx, int(frame.n_tx))
        else:  # USRP
            assert shape[0] == frame.num_tones


@pytest.mark.parametrize("sample", PICO_PARAMS)
def test_timestamps_start_at_zero(sample):
    data = read_cached(sample.path)
    assert len(data.timestamps) == len(data.frames)
    assert data.timestamps[0] == 0
    assert np.all(np.isfinite(data.timestamps))


def _with_frame_version(tmp_path, version: int):
    raw = bytearray(repo_path("CSIKit/data/pico/picoscenes_ax200_example.csi").read_bytes())
    raw[8:10] = version.to_bytes(2, "little")  # ModularPicoScenesFrame.frameVersion of frame 0
    path = tmp_path / "patched.csi"
    path.write_bytes(bytes(raw))
    return path


def test_frame_version_patch_is_a_no_op_for_version_1(tmp_path):
    data = read_quietly(PicoScenesBeamformReader(), _with_frame_version(tmp_path, 1))
    assert len(data.frames) == len(read_cached("CSIKit/data/pico/picoscenes_ax200_example.csi").frames)


@known_bug(PICOSCENES_LOG_EXCEPTION, raises=AttributeError)
def test_unsupported_frame_version_raises_a_clear_error(tmp_path):
    with pytest.raises(ValueError):
        read_quietly(PicoScenesBeamformReader(), _with_frame_version(tmp_path, 2))
