from CSIKit.reader import IWLBeamformReader
from CSIKit.util import csitools

import numpy as np

import errno
import glob
import os
import scipy.io


class InconsistentOutputError(RuntimeError):
    def __init__(self, arg):
        self.args = arg

def test_intel_matlab_consistency():

    example_dir = os.environ["INTEL_TEST_EXAMPLE_DIR"]
    mat_dir = os.environ["INTEL_TEST_MAT_DIR"]

    if not os.path.isdir(example_dir):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), example_dir)

    if not os.path.isdir(mat_dir):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), mat_dir)

    # Instantiate reader.
    reader = IWLBeamformReader()

    # Load all files from data/intel.
    example_files = sorted(glob.glob(os.path.join(example_dir, "*.dat")))
    matlab_files = sorted(glob.glob(os.path.join(mat_dir, "*.mat")))

    test_count, success_count = 0, 0

    for dat_path, mat_path in zip(example_files, matlab_files):

        # Check if the accompanying .mat file exists.
        #   dat_file/mat_file are absolute paths.
        #   os.path.basename returns the last part of the path including the file extension.
        #   We need the filename without extension, so we use the first element in os.path.splitext.
        dat_filename = os.path.splitext(os.path.basename(dat_path))[0]
        mat_filename = os.path.splitext(os.path.basename(mat_path))[0]

        if dat_filename != mat_filename:
            print("Unknown dat file found in examples: {}".format(dat_path))
            print("Accompanied by mat: {}".format(mat_path))
            print("No accompanying MAT file found. Ensure one has been generated for sanity testing.")
            print("Exiting.")
            exit(1)

        mat_dict = scipy.io.loadmat(mat_path)
        mat_csibuff_data = mat_dict["csi"]
        mat_csibuff_scaled_data = mat_dict["csi_scaled"]

        # The "csi" cells returned by read_bf_file are not raw CSI matrices, but the parsed frames.
        # We need to manually extract the complex matrix ourselves.
        # For this, we'll be assuming consistent antenna configuration across the packet trace.
        # (Time will tell if that actually causes any problems.)
        # mat_csibuff_data is a dense set of labelled tuples.
        # We just need the csi matrix inside.
        no_frames = mat_csibuff_data.shape[0]
        mat_csibuff_matrices = []
        for i in range(no_frames):
            frame = mat_csibuff_data[i]
            matrix = frame[0][0][0][-1] # Who decided load_mat would use nested tuples?!!? I JUST WANNA TALK
            mat_csibuff_matrices.append(np.transpose(matrix))

        mat_csibuff_scaled_matrices = []
        for i in range(no_frames):
            frame = mat_csibuff_scaled_data[i]
            matrix = frame[0]
            mat_csibuff_scaled_matrices.append(np.transpose(matrix))

        dat_csidata = reader.read_file(dat_path)
        dat_csiframe_matrices = [x.csi_matrix for x in dat_csidata.frames]

        dat_csidata_scaled = reader.read_file(dat_path, scaled=True)
        dat_csiframes_matrices_scaled = [x.csi_matrix for x in dat_csidata_scaled.frames]

        incorrect_frames = 0
        incorrect_scaled_frames = 0

        for i in range(no_frames):
            mat_frame_matrix = mat_csibuff_matrices[i]
            mat_scaled_frame_matrix = mat_csibuff_scaled_matrices[i]
            
            dat_frame_matrix = dat_csiframe_matrices[i]
            dat_scaled_frame_matrix = dat_csiframes_matrices_scaled[i]
        
            if not np.allclose(mat_frame_matrix, dat_frame_matrix, atol=1e-8):
                incorrect_frames += 1
    
            if not np.allclose(mat_scaled_frame_matrix, dat_scaled_frame_matrix, atol=1e-8):
                incorrect_scaled_frames += 1

        if incorrect_frames > 0:
            # print("Test Failed: {}".format(dat_filename))
            raise InconsistentOutputError("Stored MATLAB output does not match CSIKit's generated matrices.")
        # else:
        #     success_count += 1

        if incorrect_scaled_frames > 0:
            # print("Test (Scaled) Failed: {}".format(dat_filename))
            raise InconsistentOutputError("Stored MATLAB output does not match CSIKit's scaled matrices.")
        # else:
        #     success_count += 1

        # test_count += 2

    # print("Intel Tests complete: {}/{} successful.".format(success_count, test_count))
