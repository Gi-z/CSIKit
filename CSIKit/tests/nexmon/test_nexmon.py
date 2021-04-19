from CSIKit.reader import NEXBeamformReader

import numpy as np

import glob
import os
import scipy.io


def run_nexmon_tests(example_dir, mat_dir):

    if example_dir == "" or mat_dir == "":
        print("Example and MAT directories must be set with launch parameters.")
        print("See tests/nexmon/README.md for examples.")
        print("Exiting.")
        exit(1)

    # Instantiate reader.
    reader = NEXBeamformReader()

    # Load all files from data/nexmon.

    example_files = glob.glob(os.path.join(example_dir, "*.pcap"))
    matlab_files = glob.glob(os.path.join(mat_dir, "*.mat"))

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

        if np.allclose(mat_csibuff, pcap_csibuff, atol=1e-8):
            print("Test Successful: {}".format(pcap_filename))
            success_count += 1
        else:
            print("Test Failed: {}".format(pcap_filename))

        test_count += 1

    print("Nexmon Tests complete: {}/{} successful.".format(success_count, test_count))
