"""Nexmon CSI (Broadcom) pcap reader.

Value-level agreement is covered by tests/matlab/nexmon (MATLAB) and
tests/test_crosscheck_csiread.py (csiread); these tests cover framing.
"""
import collections

import numpy as np
import pytest

from CSIKit.reader import NEXBeamformReader
from CSIKit.util import csitools
from csikit_testing import read_cached, read_quietly, repo_path
from csikit_testing.known_issues import FILTER_MAC_BROKEN, known_bug
from csikit_testing.samples import NEX, by_reader, get
from csikit_testing.synthetic import pcap_records, shorten_nexmon_record, write_pcap

PADDED = "CSIKit/data/nexmon/example_43455c0.pcap"  # 18 of 566 records carry 4 bytes of padding after the UDP datagram
FOUR_BY_FOUR = "CSIKit/data/nexmon/example_4366c0_4x4mimo.pcap"
BATCHED_4339 = "CSIKit/data/nexmon/example_4339.pcap"  # 3 spatial streams per sequence number
# Files where every pcap record becomes its own CSIKit frame.
UNBATCHED = [
    PADDED,
    "CSIKit/data/nexmon/example_4358.pcap",
    "CSIKit/data/nexmon/example_4366c0.pcap",
    "CSIKit/data/nexmon/test.pcap",
    "tests/reader/example.pcap",
]

CHIPS = {
    "example_4339.pcap": "4339",
    "example_43455c0.pcap": "43455c0",
    "example_4358.pcap": "4358",
    "example_4366c0.pcap": "4366c0",
    "example_4366c0_4x4mimo.pcap": "4366c0",
    "test.pcap": "43455c0",
    "example.pcap": "4358",
}


def nexmon_reader(**kwargs):
    return NEXBeamformReader(**kwargs)


@pytest.mark.parametrize("sample", [s.param() for s in by_reader(NEX)])
def test_chip_and_bandwidth_identified(sample):
    data = read_cached(sample.path)
    chip = CHIPS[sample.path.rsplit("/", 1)[-1]]
    assert data.chipset == f"Broadcom BCM{chip}"
    assert data.backend == "Nexmon CSI"
    assert data.bandwidth == 80
    assert data.skipped_frames == 0
    for frame in data.frames:
        assert frame.chip == chip


@pytest.mark.parametrize("sample", [get(p).param() for p in UNBATCHED])
def test_one_frame_per_pcap_record(sample):
    path = repo_path(sample.path)
    records = list(pcap_records(path))
    data = read_quietly(nexmon_reader(), path)
    assert len(data.frames) == len(records)
    assert [f.sequence_no for f in data.frames] == [r.nexmon["sequence_no"] for r in records]
    assert [f.source_mac for f in data.frames] == [r.nexmon["source_mac"] for r in records]
    for frame in data.frames:
        # (256, 1) or (256, 1, 1) depending on whether the file went through
        # the multi-stream batching path; either way, one 80 MHz measurement.
        assert frame.csi_matrix.shape[0] == 256 and frame.csi_matrix.size == 256


@pytest.mark.parametrize("sample", [get(p).param() for p in UNBATCHED])
def test_timestamps_are_pcap_capture_times(sample):
    path = repo_path(sample.path)
    expected = [r.ts_sec + r.ts_usec / 1e6 for r in pcap_records(path)]
    data = read_quietly(nexmon_reader(), path)
    np.testing.assert_allclose(data.timestamps, expected, rtol=0, atol=1e-6)


def test_streams_sharing_a_sequence_number_are_merged():
    records = list(pcap_records(repo_path(BATCHED_4339)))
    streams = collections.Counter(r.nexmon["sequence_no"] for r in records)
    assert set(streams.values()) == {3}
    data = read_cached(BATCHED_4339)
    assert len(data.frames) == len(streams)
    for frame in data.frames:
        # Current layout is (subcarriers, spatial_stream, core); whether those
        # axes are the right way round is part of NEEDS_GROUND_TRUTH.
        assert frame.csi_matrix.shape == (256, 3, 1)


@pytest.mark.slow
@pytest.mark.parametrize("sample", [get(FOUR_BY_FOUR).param()])
def test_4x4_mimo_capture(sample):
    data = read_cached(sample.path)
    assert len(data.frames) == 941
    assert {f.csi_matrix.shape for f in data.frames} == {(256, 4, 4)}


def test_records_with_padding_after_the_datagram_are_kept():
    records = list(pcap_records(repo_path(PADDED)))
    assert collections.Counter(r.orig_len for r in records) == {1084: 548, 1088: 18}
    padded = [i for i, r in enumerate(records) if r.orig_len == 1088]
    assert all(records[i].data[-4:] == bytes(4) for i in padded)
    data = read_quietly(nexmon_reader(), repo_path(PADDED))
    assert len(data.frames) == len(records) and data.skipped_frames == 0
    for i in padded:  # the padding is not part of the CSI
        assert data.frames[i].csi_matrix.shape == data.frames[0].csi_matrix.shape
        np.testing.assert_array_equal(
            data.frames[i].csi_matrix[:, 0],
            np.frombuffer(records[i].data[60:60 + 1024], dtype=np.int16).astype(np.float32).view(np.complex64))


@pytest.fixture
def capture_with_a_skipped_record(tmp_path):
    # Real 43455c0 records, with the third shortened to a 40 MHz-sized payload:
    # a bandwidth change, which the reader skips.
    records = list(pcap_records(repo_path(PADDED)))[:5]
    records[2] = shorten_nexmon_record(records[2], 512)
    path = write_pcap(tmp_path / "skip.pcap", repo_path(PADDED), records)
    return path, records


def test_skipped_records_are_dropped_and_counted(capture_with_a_skipped_record):
    path, records = capture_with_a_skipped_record
    data = read_quietly(nexmon_reader(), path)
    assert len(data.frames) == 4 and data.skipped_frames == 1
    assert [f.sequence_no for f in data.frames] == [records[i].nexmon["sequence_no"] for i in (0, 1, 3, 4)]
    assert np.all(np.diff(data.timestamps) >= 0)


def test_fill_skipped_frames_inserts_placeholders_in_place(capture_with_a_skipped_record):
    path, records = capture_with_a_skipped_record
    data = read_quietly(nexmon_reader(fill_skipped_frames=True), path)
    assert len(data.frames) == 5 and data.skipped_frames == 1
    placeholder = data.frames[2]
    assert not np.any(placeholder.csi_matrix)
    assert placeholder.csi_matrix.shape == data.frames[0].csi_matrix.shape
    assert data.timestamps[2] == pytest.approx(records[2].ts_sec + records[2].ts_usec / 1e6)
    assert np.all(np.diff(data.timestamps) >= 0)


def test_filter_mac_keeps_matching_frames():
    path = repo_path("CSIKit/data/nexmon/example_4339.pcap")
    unfiltered = read_cached(BATCHED_4339)
    mac = unfiltered.frames[0].source_mac
    data = read_quietly(nexmon_reader(), path, filter_mac=mac.lower())
    assert len(data.frames) == len(unfiltered.frames)


@known_bug(FILTER_MAC_BROKEN)
def test_filter_mac_drops_other_transmitters():
    data = read_quietly(nexmon_reader(), repo_path(BATCHED_4339), filter_mac="02:00:00:00:00:01")
    assert len(data.frames) == 0


@pytest.mark.parametrize("sample", [get("tests/reader/example.pcap").param()])
def test_read_stream_matches_read_file(sample):
    path = str(repo_path(sample.path))
    reader = nexmon_reader()
    streamed = list(reader.read_stream(path))
    assert len(streamed) == len(read_cached(sample.path).frames) == 4
    for chunk, frame in zip(streamed, read_cached(sample.path).frames):
        assert len(chunk.frames) == 1
        np.testing.assert_array_equal(chunk.frames[0].csi_matrix, frame.csi_matrix)


@pytest.mark.parametrize("sample", [get("tests/reader/example.pcap").param()])
def test_get_csi_complex_output(sample):
    data = read_quietly(nexmon_reader(), repo_path(sample.path))
    csi, n_frames, n_subcarriers = csitools.get_CSI(data, metric="complex", squeeze_output=True)
    assert (n_frames, n_subcarriers) == (4, 256)
    assert csi.shape == (4, 256) and np.iscomplexobj(csi)
