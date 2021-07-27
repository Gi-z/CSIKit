from CSIKit.reader import NEXBeamformReader

import numpy as np

import errno
import glob
import os
import scipy.io


class InconsistentOutputError(RuntimeError):
    def __init__(self, arg):
        self.args = arg

def test_nexmon_matlab_consistency():

    example_dir = os.environ["NEX_TEST_EXAMPLE_DIR"]
    mat_dir = os.environ["NEX_TEST_MAT_DIR"]

    if not os.path.isdir(example_dir):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), example_dir)

    if not os.path.isdir(mat_dir):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), mat_dir)

    # Instantiate reader.
    reader = NEXBeamformReader()

    # Load all files from data/nexmon.
    example_files = sorted(glob.glob(os.path.join(example_dir, "*.pcap")))
    matlab_files = sorted(glob.glob(os.path.join(mat_dir, "*.mat")))

    # Not including bcm4339 in these tests for now, as the format is almost identical to 43455c0,
    # and the MATLAB script does not merge core/spatial streams as we are doing.
    example_files = [x for x in example_files if "4339" not in x]

    test_count, success_count = 0, 0

    for pcap_path, mat_path in zip(example_files, matlab_files):

        # Check if the accompanying .mat file exists.
        #   pcap_file/mat_file are absolute paths.
        #   os.path.basename returns the last part of the path including the file extension.
        #   We need the filename without extension, so we use the first element in os.path.splitext.
        pcap_filename = os.path.splitext(os.path.basename(pcap_path))[0]
        mat_filename = os.path.splitext(os.path.basename(mat_path))[0]

        if pcap_filename != mat_filename:
            print("Unknown PCAP file found in examples: {}".format(pcap_filename))
            print("No accompanying MAT file found. Ensure one has been generated for sanity testing.")
            print("Exiting.")
            exit(1)

        mat_dict = scipy.io.loadmat(mat_path)
        mat_csibuff = mat_dict["csi_buff"]

        # MATLAB's complex double comes out to an np.complex128.
        # We use complex64.
        if mat_csibuff.dtype == np.complex128:
            mat_csibuff = mat_csibuff.astype(np.complex64)

        pcap_csidata = reader.read_file(pcap_path)
        pcap_csiframes = [x.csi_matrix for x in pcap_csidata.frames]
        pcap_csibuff = np.array(pcap_csiframes, dtype=np.complex64)

        # The matrices produced by the MATLAB code do not include singular dimensions.
        # CSIKit includes these for consistency between different CSI matrices.
        # For comparison, we'll remove this with np.squeeze.

        pcap_csibuff = np.squeeze(pcap_csibuff)

        if not np.allclose(mat_csibuff, pcap_csibuff, atol=1e-8):
            raise InconsistentOutputError("Stored MATLAB output does not match CSIKit's generated matrices.")

        # if np.allclose(mat_csibuff, pcap_csibuff, atol=1e-8):
        #     print("Test Successful: {}".format(pcap_filename))
        #     success_count += 1
        # else:
        #     print("Test Failed: {}".format(pcap_filename))

        test_count += 1

    if test_count == 0:
        raise InconsistentOutputError("No tests performed. Ensure .dat and .mat files are present in their respective directories.")

    # print("Nexmon Tests complete: {}/{} successful.".format(success_count, test_count))
