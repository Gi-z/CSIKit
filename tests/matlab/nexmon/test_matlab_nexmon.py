"""Parity with nexmon_csi's MATLAB reader (utils/matlab/csireader.m).

csireader.m preallocates one row per pcap record and skips records whose
length doesn't match the expected CSI size, leaving zero rows at the end.
NEXBeamformReader's default ``fill_skipped_frames=True`` reproduces exactly
that, which is why these comparisons include the trailing zero frames (see
NEXMON_SKIPPED_FRAMES_APPENDED in tests/csikit_testing/known_issues.py).

BCM4339 is excluded: its format matches BCM43455c0, and csireader.m does not
merge spatial streams the way CSIKit does.
"""
import numpy as np
import pytest

from CSIKit.reader import NEXBeamformReader
from csikit_testing import read_quietly, repo_path
from csikit_testing.samples import get

scipy_io = pytest.importorskip("scipy.io")

CASES = [
    ("CSIKit/data/nexmon/example_43455c0.pcap", "tests/matlab/nexmon/mats/example_43455c0.mat"),
    ("CSIKit/data/nexmon/example_4358.pcap", "tests/matlab/nexmon/mats/example_4358.mat"),
    ("CSIKit/data/nexmon/example_4366c0.pcap", "tests/matlab/nexmon/mats/example_4366c0.mat"),
]


@pytest.mark.parametrize(
    "pcap_path, mat_path",
    [pytest.param(p, m, id=p.rsplit("/", 1)[-1], marks=get(p).marks()) for p, m in CASES],
)
def test_matches_matlab_reference(pcap_path, mat_path):
    expected = scipy_io.loadmat(str(repo_path(mat_path)))["csi_buff"]
    data = read_quietly(NEXBeamformReader(), repo_path(pcap_path))
    actual = np.squeeze(np.array([f.csi_matrix for f in data.frames], dtype=np.complex64))
    assert actual.shape == expected.shape
    np.testing.assert_allclose(actual, expected.astype(np.complex64), rtol=1e-5, atol=1e-8)
