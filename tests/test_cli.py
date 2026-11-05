"""End-to-end tests of the ``csikit`` command line (run as ``python -m CSIKit``)."""
import csv
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from csikit_testing import REPO_ROOT, repo_path
from csikit_testing.known_issues import (
    CLI_GRAPH_TYPES_CRASH,
    known_bug,
)
from csikit_testing.synthetic import atheros_record

INTEL = "CSIKit/data/intel/example.dat"  # 26 frames, 30 subcarriers, 3 Rx x 2 Tx


def csikit(*args, cwd=None):
    env = {**os.environ, "MPLBACKEND": "Agg"}
    return subprocess.run(
        [sys.executable, "-m", "CSIKit", *map(str, args)],
        capture_output=True, text=True, env=env, cwd=cwd or REPO_ROOT, timeout=600,
    )


def ok(result):
    assert result.returncode == 0, f"exit {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout


def test_help():
    assert "usage:" in ok(csikit("--help"))


@pytest.mark.parametrize(
    "path, expected",
    [
        pytest.param(INTEL, ["Hardware: Intel IWL5300", "Antenna Configuration: 3 Rx, 2 Tx",
                             "Frame Count: 26", "Subcarrier Count: 30"], id="iwl5300"),
        pytest.param("CSIKit/data/nexmon/example_4339.pcap", ["Hardware: Broadcom BCM4339", "Bandwidth: 80MHz",
                                                              "Frame Count: 950"], id="nexmon"),
        pytest.param("CSIKit/data/pico/picoscenes_ax200_example.csi", ["Hardware: Intel WiFi6 AX200",
                                                                       "Backend: PicoScenes", "Frame Count: 885"],
                     id="picoscenes"),
        pytest.param("CSIKit/data/feitcsi/HT20_2452.csi", ["Backend: FeitCSI", "Frame Count: 48",
                                                           "Subcarrier Count: 56"], id="feitcsi"),
        pytest.param("CSIKit/data/esp32/example_data.csv", ["Hardware: ESP32", "Frame Count: 60"], id="esp32"),
    ],
)
def test_info(path, expected):
    out = ok(csikit(repo_path(path)))
    for line in expected:
        assert line in out


def test_info_atheros(tmp_path):
    rng = np.random.default_rng(0)
    shape = (56, 3, 2)
    path = tmp_path / "atheros.dat"
    path.write_bytes(b"".join(
        atheros_record(i * 10_000, rng.integers(-99, 99, shape) + 1j * rng.integers(-99, 99, shape))
        for i in range(5)))
    out = ok(csikit(path))
    assert "Backend: Atheros CSI Tool" in out and "Frame Count: 5" in out


def test_csv_export(tmp_path):
    dest = tmp_path / "out.csv"
    ok(csikit("--csv", "--csv_dest", dest, repo_path(INTEL)))
    with open(dest, newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 1 + 26
    assert all(len(row) == 30 * 3 * 2 for row in rows)
    assert rows[0][0] == "Sub 0 RXTX 0/0"


def test_json_export(tmp_path):
    dest = tmp_path / "out.json"
    ok(csikit("--json", "--json_dest", dest, repo_path(INTEL)))
    assert np.array(json.loads(dest.read_text())).shape == (26, 30, 3, 2)


@pytest.mark.parametrize("metric", ["amplitude", "phase"])
def test_npz_export(tmp_path, metric):
    dest = tmp_path / "out.npz"
    ok(csikit("--npz", "--npz_dest", dest, "--npz_metric", metric, repo_path(INTEL)))
    with np.load(dest) as npz:
        array = npz["arr_0"]
    assert array.shape == (26, 30, 3, 2)
    if metric == "phase":
        assert np.all(np.abs(array) <= np.pi)


@pytest.mark.parametrize(
    "graph_type, path",
    [
        pytest.param("heatmap", INTEL, id="heatmap"),
        pytest.param("sumsqrssi", "CSIKit/data/nexmon/example_4339.pcap", id="sumsqrssi"),
        pytest.param("all_subcarriers", INTEL, id="all_subcarriers", marks=known_bug(CLI_GRAPH_TYPES_CRASH)),
        pytest.param("subcarrier_filter", INTEL, id="subcarrier_filter", marks=known_bug(CLI_GRAPH_TYPES_CRASH)),
    ],
)
def test_graph(graph_type, path):
    ok(csikit("--graph", "--graph_type", graph_type, repo_path(path)))


def test_unrecognised_file_fails_cleanly(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not a CSI capture\n" * 20)
    result = csikit(path)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "Could not detect the CSI format" in result.stderr


def test_filter_matching_nothing_fails_cleanly():
    result = csikit("--filter_mac", "02:00:00:00:00:01", repo_path("CSIKit/data/nexmon/example_4339.pcap"))
    assert result.returncode == 1
    assert "Traceback" not in result.stderr and "No CSI frames were read" in result.stderr
