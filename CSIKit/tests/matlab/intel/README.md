# CSIKit - Intel Sanity Tests

## Introduction

These tests serve to check the output of CSIKit's parsing and processing functions are identical (to at least 8 decimal places) to that of the MATLAB example scripts supplied with [linux-80211n-csi-tool-supplementary](https://github.com/dhalperi/linux-80211n-csitool-supplementary/matlab).

The tests work by iterating through each file in `./CSIKit/data/intel`, first parsing them with an `IWLBeamformReader`, and then extracting the CSI matrices from each CSIFrame. The output from these functions can then be compared directly to the cells produced by the MATLAB scripts, loaded from the accompanying .mat file in `./CSIKit/tests/matlab/intel/mats`.

These should be run before any deployment occurs to ensure the output of CSIKit is correct, and the core functionality of CSIKit does not contain any critical errors. If you notice an error within one of these tests, please create an Issue with [this link](https://github.com/Gi-z/CSIKit/issues/new) and mark it as URGENT.

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
