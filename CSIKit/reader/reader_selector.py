import os

from CSIKit.reader import ATHBeamformReader, CSVBeamformReader, IWLBeamformReader, NEXBeamformReader, PicoScenesBeamformReader, FeitCSIBeamformReader
from CSIKit.reader import Reader
from CSIKit.util.errors import UnsupportedFormatError

READERS = [ATHBeamformReader, CSVBeamformReader, IWLBeamformReader, NEXBeamformReader, PicoScenesBeamformReader, FeitCSIBeamformReader]

FORMATS = (
    "Atheros CSI Tool (.dat), Linux 802.11n CSI Tool (.dat), Nexmon CSI (.pcap), "
    "ESP32 CSI Tool (.csv), PicoScenes (.csi), FeitCSI (.csi)"
)

def get_reader(path: str) -> Reader:
    """Pick the reader for a capture file, or raise UnsupportedFormatError (a ValueError)."""
    if not os.path.exists(path):
        raise FileNotFoundError("File not found: {}".format(path))

    for reader in READERS:
        if reader.can_read(path):
            return reader()

    raise UnsupportedFormatError(
        "Could not detect the CSI format of {}. Supported formats: {}. If you know the format, "
        "use its reader directly, e.g. IWLBeamformReader().read_file(path).".format(path, FORMATS))