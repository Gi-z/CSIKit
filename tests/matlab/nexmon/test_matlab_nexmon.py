"""Parity with nexmon_csi's MATLAB reader (utils/matlab/csireader.m).

csireader.m preallocates one row per pcap record and skips any record whose
captured length isn't exactly the expected CSI size, leaving zero rows at the
end of ``csi_buff``. CSIKit now also reads records that carry padding after
the UDP datagram (18 such records in example_43455c0.pcap), which csireader.m
skips. So each test compares every frame csireader.m produced with CSIKit's
frame for the same pcap record, and checks csireader.m's unused rows are zero.
The extra frames CSIKit recovers are cross-checked against csiread in
tests/test_crosscheck_csiread.py.

BCM4339 is excluded: its format matches BCM43455c0, and csireader.m does not
merge spatial streams the way CSIKit does.
"""
import numpy as np
import pytest

from CSIKit.reader import NEXBeamformReader
from csikit_testing import read_quietly, repo_path
from csikit_testing.samples import get
from csikit_testing.synthetic import pcap_records

scipy_io = pytest.importorskip("scipy.io")

CASES = [
    ("CSIKit/data/nexmon/example_43455c0.pcap", "tests/matlab/nexmon/mats/example_43455c0.mat"),
    ("CSIKit/data/nexmon/example_4358.pcap", "tests/matlab/nexmon/mats/example_4358.mat"),
    ("CSIKit/data/nexmon/example_4366c0.pcap", "tests/matlab/nexmon/mats/example_4366c0.mat"),
]
NFFT = 256  # all reference captures are 80 MHz
HOFFSET = 16  # csireader.m: record length - (HOFFSET - 1) * 4 must equal NFFT * 4


@pytest.mark.parametrize(
    "pcap_path, mat_path",
    [pytest.param(p, m, id=p.rsplit("/", 1)[-1], marks=get(p).marks()) for p, m in CASES],
)
def test_matches_matlab_reference(pcap_path, mat_path):
    expected = scipy_io.loadmat(str(repo_path(mat_path)))["csi_buff"]
    records = list(pcap_records(repo_path(pcap_path)))
    matlab_reads = [r.orig_len - (HOFFSET - 1) * 4 == NFFT * 4 for r in records]
    n_matlab = sum(matlab_reads)

    assert expected.shape == (len(records), NFFT)
    assert not np.any(expected[n_matlab:]), "csireader.m's rows for skipped records should be zero"

    data = read_quietly(NEXBeamformReader(), repo_path(pcap_path))
    assert len(data.frames) == len(records)
    actual = np.array([f.csi_matrix.reshape(-1) for f, read in zip(data.frames, matlab_reads) if read],
                      dtype=np.complex64)
    np.testing.assert_allclose(actual, expected[:n_matlab].astype(np.complex64), rtol=1e-5, atol=1e-8)
