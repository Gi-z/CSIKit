# CSIKit - Intel Sanity Tests

- [Introduction](#introduction)
- [Running Tests](#running-tests) 
- [Generating MATs](#generating-mats)
- [Example File Listing](#example-file-listing)
    * [log.all.csi.6.7.6.dat](#logallcsi676dat)
    * [example.dat](#exampledat)

## Introduction

These tests serve to check the output of CSIKit's parsing and processing functions are identical (to at least 8 decimal places) to that of the MATLAB example scripts supplied with [linux-80211n-csi-tool-supplementary](https://github.com/dhalperi/linux-80211n-csitool-supplementary/matlab).

The tests work by iterating through each file in `./CSIKit/data/intel`, first parsing them with an `IWLBeamformReader`, and then extracting the CSI matrices from each CSIFrame. The output from these functions can then be compared directly to the cells produced by the MATLAB scripts, loaded from the accompanying .mat file in `./CSIKit/tests/matlab/intel/mats`.

These should be run before any deployment occurs to ensure the output of CSIKit is correct, and the core functionality of CSIKit does not contain any critical errors. If you notice an error within one of these tests, please create an Issue with [this link](https://github.com/Gi-z/CSIKit/issues/new) and mark it as URGENT.

## Running Tests

In order to run the tests in `test_intel.py` with PyTest, the following environment variables must be set.
- `INTEL_TEST_EXAMPLE_DIR`: Directory containing dat files to be used for tests.
- `INTEL_TEST_MAT_DIR`: Directory containing mat files generated for files in the `EXAMPLE_DIR` using the method below.

Once these environment variables are set, these tests can be run either by directly running `pytest test_intel.py`, or (once the Nexmon environment variables from `tests/nexmon/README.md` have been created) all tests can be run from the root directory by just running `pytest`.

## Generating MATs

1. Download the contents of the matlab folder linked here: [linux-80211n-csi-tool-supplementary](https://github.com/dhalperi/linux-80211n-csitool-supplementary/matlab).
2. Put them in the working directory in MATLAB.
3. Generate an MEX for `read_bfee.c` by typing `mex read_bfee.c` in the MATLAB console. `read_bfee.mex` should then exist.
4. Run `csi = read_bf_file("your_dat_filename.dat");`
5. Run `csi_scaled = cellfun(@get_scaled_csi, csi, 'UniformOutput', false);`
6. Right click in the Workspace column and click Save.
7. Label your completed file with the same filename (but not extension) as your `.dat`.

This process will generate a `.mat` file which can be used with `run_intel_tests`.

## Example File Listing

### log.all.csi.6.7.6.dat
Hardware: Intel IWL5300\
Bandwidth: 20MHz\
Subcarriers: 30\
Frames: 29\
Skipped Frames: 0\
CSI Shape: 29x30x3x(variable Tx)

### example.dat
Hardware: Intel IWL5300 (Lenovo T410)\
Bandwidth: 20MHz\
Subcarriers: 30\
Frames: 26\
Skipped Frames: 0\
CSI Shape: 26x30x3x(variable Tx)
