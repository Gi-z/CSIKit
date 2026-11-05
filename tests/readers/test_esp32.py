"""ESP32-CSI-Tool CSV reader (CSVBeamformReader, ESP32 layout)."""
import csv

import numpy as np
import pytest

from CSIKit.reader import CSVBeamformReader, get_reader
from CSIKit.util.matlab import dbinv
from csikit_testing import read_cached, read_quietly, repo_path
from csikit_testing.known_issues import (
    CSV_DROPS_ANTENNA_1,
    ESP32_IMAG_REAL_ORDER,
    ESP32_ODD_LENGTH_ROW,
    ESP32_TIMESTAMPS,
    known_bug,
)
from csikit_testing.samples import CSV, by_reader
from csikit_testing.synthetic import ESP32_FIELDS, esp32_row, write_esp32_csv

READABLE = [pytest.param(s.path, id=s.id) for s in by_reader(CSV) if s.unreadable is None]
COL = {name: i for i, name in enumerate(ESP32_FIELDS)}


def csv_rows(path):
    with open(repo_path(path), newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ESP32_FIELDS
    return rows[1:]


def raw_csi(row):
    return [int(v) for v in row[COL["CSI_DATA"]].strip("[] \n").split()]


@pytest.mark.parametrize("path", READABLE)
def test_one_frame_per_row(path):
    assert len(read_cached(path).frames) == len(csv_rows(path))


@pytest.mark.parametrize("path", READABLE)
def test_metadata_columns_are_parsed(path):
    data = read_cached(path)
    assert data.chipset == "ESP32" and data.backend == "ESP32 CSI Tool"
    assert data.bandwidth == 20
    for frame, row in zip(data.frames, csv_rows(path)):
        assert frame.mac == row[COL["mac"]]
        assert frame.rssi == int(row[COL["rssi"]])
        assert frame.noise_floor == int(row[COL["noise_floor"]])
        assert frame.channel == int(row[COL["channel"]])
        assert frame.local_timestamp == int(row[COL["local_timestamp"]])


@pytest.mark.parametrize("path", READABLE)
def test_csi_amplitudes_match_raw_buffer(path):
    # Amplitude is independent of the (imag, real) vs (real, imag) question.
    for frame, row in zip(read_cached(path).frames, csv_rows(path)):
        values = np.array(raw_csi(row), dtype=float).reshape(-1, 2)
        assert frame.csi_matrix.shape == (len(values), 1)
        np.testing.assert_allclose(np.abs(frame.csi_matrix[:, 0]), np.hypot(values[:, 0], values[:, 1]), rtol=1e-6)


@known_bug(ESP32_TIMESTAMPS)
@pytest.mark.parametrize("path", READABLE)
def test_timestamps_are_seconds_since_first_frame(path):
    real_ts = np.array([float(r[COL["real_timestamp"]]) for r in csv_rows(path)])
    np.testing.assert_allclose(read_cached(path).timestamps, real_ts - real_ts[0], atol=1e-6)


@known_bug(ESP32_IMAG_REAL_ORDER)
def test_each_subcarrier_is_stored_imaginary_part_first(tmp_path):
    # ESP-IDF: each subcarrier is two int8s, imaginary part then real part.
    # csiread's ESP32 parser agrees: csi = buf[1::2] + 1j * buf[::2].
    buf = [v for k in range(64) for v in (k % 7 - 3, k % 5 - 2)]
    path = write_esp32_csv(tmp_path / "order.csv", [esp32_row(buf)])
    frame = read_quietly(CSVBeamformReader(), path).frames[0]
    expected = np.array(buf[1::2]) + 1j * np.array(buf[::2])
    np.testing.assert_array_equal(frame.csi_matrix[:, 0], expected)


def test_synthetic_file_is_detected(tmp_path):
    path = write_esp32_csv(tmp_path / "esp.csv", [esp32_row([1, 2] * 64)] * 3)
    assert isinstance(get_reader(str(path)), CSVBeamformReader)


@known_bug(ESP32_ODD_LENGTH_ROW, raises=ValueError)
def test_odd_length_row_does_not_abort_the_read(tmp_path):
    good = esp32_row([1, 2] * 64)
    bad = esp32_row([1, 2] * 63 + [1])  # 127 values: one byte missing
    path = write_esp32_csv(tmp_path / "odd.csv", [good, bad, good, good])
    data = read_quietly(CSVBeamformReader(), path)
    assert len(data.frames) >= 3


@known_bug(CSV_DROPS_ANTENNA_1)
def test_rows_from_antenna_1_are_kept(tmp_path):
    rows = [esp32_row([1, 2] * 64, ant=ant, local_timestamp=i) for i, ant in enumerate([0, 1, 0, 1])]
    data = read_quietly(CSVBeamformReader(), write_esp32_csv(tmp_path / "ant.csv", rows))
    assert [f.ant for f in data.frames] == [0, 1, 0, 1]


@pytest.mark.parametrize("path", READABLE)
def test_scaling_matches_mean_subcarrier_power_to_rssi(path):
    data = read_cached(path, scaled=True)
    for frame in data.frames[:200]:
        power = np.mean(np.abs(frame.csi_matrix) ** 2)
        assert power == pytest.approx(dbinv(frame.rssi), rel=1e-4)
