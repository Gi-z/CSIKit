"""Catalogue of the sample captures bundled in ``CSIKit/data``.

Every capture-driven test (reader selection, golden snapshots, CLI) is
parametrised from this list, so adding a sample here adds coverage everywhere.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from csikit_testing import NUMPY2, NUMPY_STRICT_SCALAR_ASSIGNMENT
from csikit_testing.known_issues import (
    ESP32_ODD_LENGTH_ROW,
    NUMPY2_SUPPORT,
    known_bug,
)


@dataclass(frozen=True)
class Sample:
    path: str
    """Path relative to the repository root."""

    reader: str
    """Name of the reader class ``get_reader`` should pick."""

    slow: bool = False
    """Parsing takes long enough that the test only runs with ``--runslow``."""

    numpy2_read_broken: bool = False
    """``read_file`` itself raises under NumPy 2 (see NUMPY2_SUPPORT)."""

    numpy2_get_csi_broken: bool = False
    """``read_file`` works but ``csitools.get_CSI`` raises on NumPy >= 2.4."""

    unreadable: object = None
    """Known issue that stops this file being parsed on any NumPy version."""

    @property
    def id(self) -> str:
        return self.path.split("/", 2)[-1] if self.path.startswith("CSIKit/data/") else self.path

    def marks(self, *, needs_get_csi: bool = False):
        marks = []
        if self.slow:
            marks.append(pytest.mark.slow)
        if self.unreadable is not None:
            marks.append(known_bug(self.unreadable))
        elif self.numpy2_read_broken:
            marks.append(known_bug(NUMPY2_SUPPORT, condition=NUMPY2, raises=OverflowError))
        elif needs_get_csi and self.numpy2_get_csi_broken:
            marks.append(known_bug(NUMPY2_SUPPORT, condition=NUMPY_STRICT_SCALAR_ASSIGNMENT, raises=TypeError))
        return marks

    def param(self, *, needs_get_csi: bool = False):
        return pytest.param(self, id=self.id, marks=self.marks(needs_get_csi=needs_get_csi))


IWL = "IWLBeamformReader"
NEX = "NEXBeamformReader"
CSV = "CSVBeamformReader"
PICO = "PicoScenesBeamformReader"
FEIT = "FeitCSIBeamformReader"

SAMPLES = [
    # Linux 802.11n CSI Tool (Intel IWL5300)
    Sample("CSIKit/data/intel/example.dat", IWL),
    Sample("CSIKit/data/intel/log.all_csi.6.7.6.dat", IWL),
    Sample("CSIKit/visualization/example_dat/los_5.dat", IWL),
    Sample("CSIKit/visualization/example_dat/los_40.dat", IWL),
    Sample("CSIKit/visualization/example_dat/los_100.dat", IWL),
    # Nexmon CSI (Broadcom)
    Sample("CSIKit/data/nexmon/example_4339.pcap", NEX),
    Sample("CSIKit/data/nexmon/example_43455c0.pcap", NEX, numpy2_get_csi_broken=True),
    Sample("CSIKit/data/nexmon/test.pcap", NEX, numpy2_get_csi_broken=True),
    Sample("CSIKit/data/nexmon/example_4358.pcap", NEX, numpy2_read_broken=True),
    Sample("tests/reader/example.pcap", NEX, numpy2_read_broken=True),
    Sample("CSIKit/data/nexmon/example_4366c0.pcap", NEX, numpy2_read_broken=True),
    Sample("CSIKit/data/nexmon/example_4366c0_4x4mimo.pcap", NEX, slow=True, numpy2_read_broken=True),
    # ESP32 CSI Tool (CSV)
    Sample("CSIKit/data/esp32/example_data.csv", CSV, numpy2_get_csi_broken=True),
    Sample("CSIKit/data/esp32/example_fast_100hz_pitraffic.csv", CSV, numpy2_get_csi_broken=True),
    Sample("CSIKit/data/esp32/example_fast2_100hz_pitraffic.csv", CSV, numpy2_get_csi_broken=True),
    Sample("CSIKit/data/esp32/example_100hz_pitraffic.csv", CSV, unreadable=ESP32_ODD_LENGTH_ROW),
    # PicoScenes (Intel AX200/AX210, IWL5300, USRP)
    Sample("CSIKit/data/pico/picoscenes_ax200_example.csi", PICO),
    Sample("CSIKit/data/pico/picoscenes_ax200_agcdemo.csi", PICO),
    Sample("CSIKit/data/intel/ax200_demo.csi", PICO),
    Sample("CSIKit/data/intel/ax200_agc_demo.csi", PICO),
    Sample("CSIKit/data/intel/rx_7_211206_160817.csi", PICO),
    Sample("CSIKit/data/intel/rx_7_211206_160935.csi", PICO),
    Sample("CSIKit/data/intel/rx_8_211119_171706.csi", PICO),
    Sample("CSIKit/data/intel/rx_8_211206_152319.csi", PICO),
    Sample("CSIKit/data/intel/rx_8_211206_161457.csi", PICO),
    Sample("CSIKit/data/intel/rx_8_211217_191036.csi", PICO),
    Sample("CSIKit/data/pico/picoscenes_iwl5300_example.csi", PICO, numpy2_read_broken=True),
    Sample("CSIKit/data/pico/picoscenes_iwl5300_example2.csi", PICO, numpy2_read_broken=True),
    Sample("CSIKit/data/pico/picoscenes_usrpb210_example.csi", PICO, slow=True, numpy2_read_broken=True),
    # FeitCSI (Intel AX200/AX210)
    *[
        Sample(f"CSIKit/data/feitcsi/{name}.csi", FEIT)
        for name in (
            "HT20_2452", "HT40_2452",
            "VHT20_5500", "VHT40_5500", "VHT80_5500", "VHT160_5500",
            "HESU20_5500", "HESU40_5500", "HESU80_5500", "HESU160_5500",
        )
    ],
]

# Files in CSIKit/data that are deliberately not catalogued:
#   esp32/output.csv  - CSIKit's own --csv export, not a capture.
#   nexmon/test*.py   - scratch scripts.


def by_reader(reader: str):
    return [s for s in SAMPLES if s.reader == reader]


def get(path: str) -> Sample:
    for s in SAMPLES:
        if s.path == path:
            return s
    raise KeyError(path)


def params(samples=None, *, needs_get_csi: bool = False):
    return [s.param(needs_get_csi=needs_get_csi) for s in (SAMPLES if samples is None else samples)]
