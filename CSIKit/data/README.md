# CSIKit Data Repo

## Introduction

This repo also aims to provide examples of CSI data with specific labelling data to facilitate experimentation

Many CSI data files can be found online, however they are typically produced by variable hardware configurations and this is not always effectively labelled. experimentation typically relies on a understanding of the methods by which the data was produced, so this also aims to cover that gap.

## Hardware Configuration

### CSI Collector

Intel: Lenovo Thinkpad T420

Pi: Raspberry Pi 4

### WiFi access point

Sky Q Router ER115.

Using separate SSIDs for 2.4GHz and 5GHz.s

# Data

## Intel

### Activity

To be completed.

### Respiration

#### 3breaths.dat
3 breaths captured over an x second period.

### Heart Rate

To be completed.

### Miscallaneous

#### log.all_csi.6.7.6
Example CSI data file included with the Linux 802.11n CSI Tool supplementary files. This sample contains 29 frames of CSI for a 1x3 antenna configuration. This file's headers do not include a valid "timestamp_low" for each frame, which means it cannot effectively be plotted against time. This is a good example of how CSI data, while capturing continuous signals, can be difficult to retrieve with a consistent sampling rate on consumer hardware. Unknown hardware configuration (specifics).

#### csi.dat
Example CSI file captured for a short period, for the demonstration of full functionality (as compared to log.all_csi.6.7.6).

#### csi2.dat
Example CSI file captured for a short period, for the demonstration of full functionality (as compared to log.all_csi.6.7.6).