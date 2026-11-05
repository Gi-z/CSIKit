"""ESP32-CSI-Tool CSV reader (CSVBeamformReader, ESP32 layout)."""
import csv

import numpy as np
import pytest

from CSIKit.reader import CSVBeamformReader, get_reader
from CSIKit.util.matlab import dbinv
from csikit_testing import read_cached, read_quietly, repo_path
from csikit_testing.samples import CSV, by_reader
from csikit_testing.synthetic import ESP32_FIELDS, esp32_row, write_esp32_csv

ESP32_SAMPLES = [pytest.param(s.path, id=s.id) for s in by_reader(CSV)]
COL = {name: i for i, name in enumerate(ESP32_FIELDS)}


def csv_rows(path):
    with open(repo_path(path), newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ESP32_FIELDS
    return rows[1:]


def raw_csi(row):
    return [int(v) for v in row[COL["CSI_DATA"]].strip("[] \n").split()]


def is_complete(row):
    # (imag, real) pairs, as many values as the `len` column says; ESP32-CSI-Tool's
    # LLTF-only build prints the first 128 values of a longer buffer.
    n, expected = len(raw_csi(row)), int(row[COL["len"]])
    return n % 2 == 0 and (n == expected or (n == 128 and expected > 128))


def valid_rows(path):
    return [r for r in csv_rows(path) if is_complete(r)]


@pytest.mark.parametrize("path", ESP32_SAMPLES)
def test_one_frame_per_complete_row(path):
    data = read_cached(path)
    assert len(data.frames) == len(valid_rows(path))
    assert data.skipped_frames == len(csv_rows(path)) - len(valid_rows(path))


@pytest.mark.parametrize("path", ESP32_SAMPLES)
def test_metadata_columns_are_parsed(path):
    data = read_cached(path)
    assert data.chipset == "ESP32" and data.backend == "ESP32 CSI Tool"
    assert data.bandwidth == 20
    for frame, row in zip(data.frames, valid_rows(path)):
        assert frame.mac == row[COL["mac"]]
        assert frame.rssi == int(row[COL["rssi"]])
        assert frame.noise_floor == int(row[COL["noise_floor"]])
        assert frame.channel == int(row[COL["channel"]])
        assert frame.local_timestamp == int(row[COL["local_timestamp"]])


@pytest.mark.parametrize("path", ESP32_SAMPLES)
def test_csi_amplitudes_match_raw_buffer(path):
    for frame, row in zip(read_cached(path).frames, valid_rows(path)):
        values = np.array(raw_csi(row), dtype=float).reshape(-1, 2)
        assert frame.csi_matrix.shape == (len(values), 1)
        np.testing.assert_allclose(np.abs(frame.csi_matrix[:, 0]), np.hypot(values[:, 0], values[:, 1]), rtol=1e-6)


@pytest.mark.parametrize("path", ESP32_SAMPLES)
def test_timestamps_are_seconds_since_first_frame(path):
    # ESP32-CSI-Tool writes real_timestamp in seconds (steady clock).
    rows = valid_rows(path)
    real_ts = np.array([float(r[COL["real_timestamp"]]) for r in rows])
    np.testing.assert_allclose(read_cached(path).timestamps, real_ts - real_ts[0], atol=1e-6)
    # Cross-check against the radio's own microsecond counter (local_timestamp).
    local_us = np.array([int(r[COL["local_timestamp"]]) for r in rows])
    duration = read_cached(path).timestamps[-1]
    assert duration == pytest.approx((local_us[-1] - local_us[0]) / 1e6, rel=0.02)


def test_each_subcarrier_is_stored_imaginary_part_first(tmp_path):
    # ESP-IDF (wifi-vendor-features.rst): "imaginary part followed by real part". ESP32-CSI-Tool's
    # parse_csi.py and firmware (atan2(buf[2i], buf[2i+1])) and csiread all read it this way.
    buf = [v for k in range(64) for v in (k % 7 - 3, k % 5 - 2)]
    path = write_esp32_csv(tmp_path / "order.csv", [esp32_row(buf)])
    frame = read_quietly(CSVBeamformReader(), path).frames[0]
    expected = np.array(buf[1::2]) + 1j * np.array(buf[::2])
    np.testing.assert_array_equal(frame.csi_matrix[:, 0], expected)


def test_synthetic_file_is_detected(tmp_path):
    path = write_esp32_csv(tmp_path / "esp.csv", [esp32_row([1, 2] * 64)] * 3)
    assert isinstance(get_reader(str(path)), CSVBeamformReader)


@pytest.mark.parametrize(
    "bad_values, len_column",
    [
        pytest.param([1, 2] * 63 + [1], 128, id="odd-count"),       # one value lost
        pytest.param([1, 2] * 63, 128, id="even-but-short"),         # a whole pair lost
    ],
)
def test_incomplete_rows_are_skipped_not_padded(tmp_path, bad_values, len_column):
    # Once a value is lost every later pair is misaligned and the row can't be
    # repaired, so it's dropped and counted rather than padded.
    good = esp32_row([1, 2] * 64, local_timestamp=0)
    bad = esp32_row(bad_values, len=len_column, local_timestamp=1)
    path = write_esp32_csv(tmp_path / "bad.csv", [good, bad, good, good])
    data = read_quietly(CSVBeamformReader(), path)
    assert len(data.frames) == 3
    assert data.skipped_frames == 1
    assert [f.local_timestamp for f in data.frames] == [0, 0, 0]


def test_lltf_only_rows_are_kept(tmp_path):
    # ESP32-CSI-Tool's CONFIG_SHOULD_COLLECT_ONLY_LLTF prints `len` (e.g. 384) but only 128 values.
    path = write_esp32_csv(tmp_path / "lltf.csv", [esp32_row([1, 2] * 64, len=384)] * 2)
    data = read_quietly(CSVBeamformReader(), path)
    assert len(data.frames) == 2 and data.skipped_frames == 0


def test_rows_from_antenna_1_are_kept(tmp_path):
    rows = [esp32_row([1, 2] * 64, ant=ant, local_timestamp=i) for i, ant in enumerate([0, 1, 0, 1])]
    data = read_quietly(CSVBeamformReader(), write_esp32_csv(tmp_path / "ant.csv", rows))
    assert [f.ant for f in data.frames] == [0, 1, 0, 1]


@pytest.mark.parametrize("path", ESP32_SAMPLES)
def test_scaling_matches_mean_subcarrier_power_to_rssi(path):
    data = read_cached(path, scaled=True)
    for frame in data.frames[:200]:
        power = np.mean(np.abs(frame.csi_matrix) ** 2)
        assert power == pytest.approx(dbinv(frame.rssi), rel=1e-4)
