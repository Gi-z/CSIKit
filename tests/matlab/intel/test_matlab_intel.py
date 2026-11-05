"""Parity with the Linux 802.11n CSI Tool's MATLAB parser.

The .mat references were produced with ``read_bf_file`` and ``get_scaled_csi``
from linux-80211n-csitool-supplementary (see README.md in this directory).
"""
import numpy as np
import pytest

from CSIKit.reader import IWLBeamformReader
from csikit_testing import read_quietly, repo_path

scipy_io = pytest.importorskip("scipy.io")

CASES = [
    pytest.param("CSIKit/data/intel/example.dat", "tests/matlab/intel/mats/example.mat", id="example"),
    pytest.param("CSIKit/data/intel/log.all_csi.6.7.6.dat", "tests/matlab/intel/mats/log.all_csi.6.7.6.mat",
                 id="log.all_csi.6.7.6"),
]


def load_reference(mat_path):
    mat = scipy_io.loadmat(str(repo_path(mat_path)))
    # read_bf_file returns a cell array of structs whose last field is the
    # (Ntx, Nrx, 30) CSI matrix; get_scaled_csi returns the scaled matrices.
    raw = [np.transpose(cell[0][0][0][-1]) for cell in mat["csi"]]
    scaled = [np.transpose(cell[0]) for cell in mat["csi_scaled"]]
    return raw, scaled


@pytest.mark.parametrize("scaled", [False, True], ids=["raw", "scaled"])
@pytest.mark.parametrize("dat_path, mat_path", CASES)
def test_matches_matlab_reference(dat_path, mat_path, scaled):
    raw, ref_scaled = load_reference(mat_path)
    expected = ref_scaled if scaled else raw
    data = read_quietly(IWLBeamformReader(), repo_path(dat_path), scaled=scaled)
    assert len(data.frames) == len(expected)
    for i, (frame, ref) in enumerate(zip(data.frames, expected)):
        np.testing.assert_allclose(frame.csi_matrix, ref, rtol=1e-5, atol=1e-8, err_msg=f"frame {i}")
