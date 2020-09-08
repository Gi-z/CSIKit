# CSIKit ![PyPI version](https://badge.fury.io/py/placeholder.svg)

CSI interaction tools for a range of compatible WiFi hardware, written in Python with numpy. 

Python 3.5+ required.

- **CSI parsing** from .pcap and .dat files.
- **Processing** and **Visualisation** using numpy and matplotlib.
- **CSV generator** for dataset serialisation.
- **Libraries** for parsing CSI for your own Python applications.

<p align="center">
  <img src="./img/example.png" alt="CSIKit Command Line Example">
</p>

- [Description](#Description)
- [Installation](#Installation)
- [Options](#Options)
- [Example](#Example)
- [Library](#Library)
- [Supported Hardware](#Supported-Hardware)
- [Mistakes](#Mistakes)
- [Links](#Links)
- [License](#License)

## Description

**CSIKit** is a framework aimed at assisting data scientists, researchers and other programmers with performing experiments and tests using CSI-capable WiFi hardware. 

While the various public extraction toolkits do include scripts for parsing CSI data from their specific formats, these are largely written for MATLAB. Given the increasing focus on using deep learning in CSI experimentation, Python tools for parsing and processing CSI data may be more desirable for some.

command line tool for parsing, processing, converting, and visualisation. 

```
csikit [OPTIONS] file[.pcap/.dat]
```

## Installation

CSIKit can be used directly from source, or installed via pip.

```
pip install csikit
```

## Options

```
--info, -i              Print information about the CSI contained in a given file (hardware, configuration, shape, etc).


--graph, -g             Visualise CSI data using matplotlib.

    --graph-type TYPE   Select a graph type for visualisation: ["heatmap" (default), "all_subcarriers", "subcarrier_filter"]

--csv, -c               Write CSI data to CSV file.
                        # Currently this writes all (scaled, where applicable) subcarrier amplitudes from the first antenna stream to each row.
    --csv-dest FILE     Provide a destination for the output CSV file. (Default: output.csv)
                        
```

Additional options for each mode are to be added in the near future.

## Example

### CSIKit CLI

```
csikit example_file.pcap
csikit --graph --graph-type all_subcarriers example_file.pcap
csikit --csv example_file.pcap
```

### CSIKit library

Intel IWL5300 example:

```
from CSIKit import csitools
from CSIKit import IWLBeamformReader

reader = IWLBeamformReader("log.all_csi.6.7.6.dat")
csi_matrix = get_CSI(reader, scaled=True/False, antenna_stream=0)
```

Raspberry Pi 4 example:

```
from CSIKit import csitools
from CSIKit import NEXBeamformReader

reader = NEXBeamformReader("walk_1597159475.pcap")
csi_matrix = get_CSI(reader)
```

## Library

csitools, iwl, nex

Descriptions of things.

## Supported Hardware

 - Intel IWL5300

 - Broadcom BCMs43455c0

## Known Issues

 - CSVs and Visualisations always assume you want to view the first antenna stream.
    - If this affects you, reach out to me.
    - I am interested as to how you would want to make use of multiple streams.
 - nexmon_csi pcaps generated with non-43455c0 hardware will be parsed incorrectly. 
    - I only have 43455c0 hardware to generate data with, so I have been unable to spend time with others.
    - BCM hardware will have to be detected from file headers.
    - Once additional hardware support is completed, this will be resolved.


### Coming Soon

Additional **[nexmon_csi](https://github.com/seemoo-lab/nexmon_csi)** compatible hardware.

Atheros.

ESP32.

## Mistakes

If anything is wrong, [let me know](mailto:gizmoloon@gmail.com). I want to know why.

## Links

- **[Linux 802.11n CSI Tool](https://dhalperi.github.io/linux-80211n-csitool/)**: CSI extraction suite for Intel IWL5300 hardware.
- **[nexmon_csi](https://github.com/seemoo-lab/nexmon_csi)**: CSI extraction suite for a range of Broadcom hardware.

## License

The code in this project is licensed under MIT license.