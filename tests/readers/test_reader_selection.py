"""get_reader / can_read: every bundled capture is routed to the right parser."""
import contextlib
import io

import pytest

from CSIKit.reader import (
    ATHBeamformReader,
    CSVBeamformReader,
    FeitCSIBeamformReader,
    IWLBeamformReader,
    NEXBeamformReader,
    PicoScenesBeamformReader,
    get_reader,
)
from CSIKit.util.errors import UnsupportedFormatError
from csikit_testing import repo_path
from csikit_testing.samples import SAMPLES

ALL_READERS = [
    ATHBeamformReader,
    CSVBeamformReader,
    FeitCSIBeamformReader,
    IWLBeamformReader,
    NEXBeamformReader,
    PicoScenesBeamformReader,
]


@pytest.mark.parametrize("sample", [pytest.param(s, id=s.id) for s in SAMPLES])
def test_get_reader_selects_expected_reader(sample):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        reader = get_reader(str(repo_path(sample.path)))
    assert type(reader).__name__ == sample.reader
    assert "Unable to automatically select" not in out.getvalue()


@pytest.mark.parametrize("sample", [pytest.param(s, id=s.id) for s in SAMPLES])
def test_only_one_reader_claims_each_sample(sample):
    path = str(repo_path(sample.path))
    claimed = [r.__name__ for r in ALL_READERS if r.can_read(path)]
    assert claimed == [sample.reader]


@pytest.mark.parametrize("reader", ALL_READERS, ids=lambda r: r.__name__)
def test_can_read_missing_file_returns_false(reader, tmp_path):
    assert reader.can_read(str(tmp_path / "does-not-exist.dat")) is False


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"x", id="1-byte"),
        pytest.param(b"hello, this is not CSI\n" * 50, id="text"),
        pytest.param(bytes(range(256)) * 8, id="binary"),
    ],
)
def test_can_read_never_raises_on_foreign_files(content, tmp_path):
    for suffix in (".dat", ".pcap", ".csv", ".csi", ".bin"):
        path = tmp_path / f"foreign{suffix}"
        path.write_bytes(content)
        for reader in ALL_READERS:
            reader.can_read(str(path))  # must not raise


@pytest.mark.parametrize("content", [b"", b"\x01\x02"], ids=["empty", "2-bytes"])
def test_feitcsi_does_not_claim_tiny_files(tmp_path, content):
    path = tmp_path / "tiny.csi"
    path.write_bytes(content)
    assert FeitCSIBeamformReader.can_read(str(path)) is False


def test_get_reader_rejects_unrecognised_file(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not a CSI capture\n" * 20)
    with pytest.raises(UnsupportedFormatError, match="Could not detect the CSI format"):
        get_reader(str(path))


def test_get_reader_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        get_reader(str(tmp_path / "missing.pcap"))
