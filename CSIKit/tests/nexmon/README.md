# CSIKit - Nexmon Sanity Tests

## Introduction

These tests serve to check the output of CSIKit's parsing and processing functions are identical (to at least 8 decimal places) to that of the MATLAB example scripts supplied with [nexmon_csi](https://github.com/seemoo-lab/nexmon_csi/tree/master/utils/matlab).

The tests work by iterating through each file in `./CSIKit/data/nexmon`, first parsing them with a `NEXBeamformReader`, and then extracting CSI amplitude using `csitools.get_CSI`. The output from these functions can then be compared directly to the matrices produced by the MATLAB scripts, loaded from the accompanying .mat file in `./CSIKit/tests/nexmon/mats`.

These should be run before any deployment occurs to ensure the output of CSIKit is correct, and the core functionality of CSIKit does not contain any critical errors. If you notice an error within one of these tests, please create an Issue with [this link](https://github.com/Gi-z/CSIKit/issues/new) and mark it as URGENT.

## File Listing

### example_4358.pcap
Hardware: Broadcom BCM4358\
Bandwidth: 80MHz\
Subcarriers: 256\
Frames: 4\
Skipped Frames: 0\
CSI Shape: 4x256x1

### example_4366c0.pcap
Hardware: Broadcom BCM4366c0\
Bandwidth: 80MHz\
Subcarriers: 256\
Frames: 293\
Skipped Frames: 0\
CSI Shape: 293x256x1

### example_43455c0.pcap
Hardware: Broadcom BCM43455c0\
Bandwidth: 80MHz\
Subcarriers: 256\
Frames: 566\
Skipped Frames: 18\
CSI Shape: 566x256x1
