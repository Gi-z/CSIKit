---
layout: default
---

# Overview [![PyPi version](https://pypip.in/v/CSIKit/badge.png)](https://crate.io/packages/CSIKit/) [![Downloads](https://pepy.tech/badge/csikit/month)](https://pepy.tech/project/csikit)

Tools for extracting Channel State Information from formats produced by a range of WiFi hardware/drivers, written in Python with numpy.

Python 3.6+ required.

- **CSI parsing** from Atheros, Intel and Broadcom (nexmon) formats.
- **Processing** and **Visualisation** using numpy and matplotlib.
- **CSV/JSON generators** for dataset serialisation.
- **Library** and **Tools** for parsing CSI for your own Python applications.

Don't have your own CSI data? Check out [CSI-Data](https://github.com/Gi-z/CSI-Data) for a collection of public CSI datasets.

<p align="center">
  <img src="./img/example_new.png" alt="CSIKit Command Line Example"/>
</p>

- [CSIKit](#csikit-)
  - [Description](#description)
  - [Installation](#installation)
  - [Examples](#example)
  - [Supported Hardware](#supported-hardware)
  - [Mistakes and Tests](#mistakes-and-tests)
  - [Reference Links](#reference-links)
  - [License](#license)

## Description

**CSIKit** is a framework aimed at assisting data scientists, researchers, and programmers with performing experiments and tests using CSI-capable WiFi hardware.

While the various public extraction toolkits do include scripts for parsing CSI data from their specific formats, these are largely written for MATLAB. Given the increasing focus on using deep learning in CSI experimentation, Python tools for parsing and processing CSI data may be more desirable for some. This is aimed at improving the accessibility of CSI research for those who may be interested in the area but have little experience with network engineering.

As is usually the case with research-oriented software, documentation is in-progress.

CSIKit provides a command line tool for parsing, processing, converting, and visualisation of CSI data, as well as libraries for use in other Python applications such as those working with Tensorflow, PyTorch, etc.

```console
csikit [OPTIONS] file[.pcap/.dat]
```

## Installation

CSIKit can be installed via pip or used directly from source.

```console
pip install csikit
```

## Example

### Command Line

```console
csikit log.all_csi.6.7.6.dat
csikit --graph --graph-type all_subcarriers log.all_csi.6.7.6.dat
csikit --csv log.all_csi.6.7.6.dat
```

### CSIKit library

Generic example:

```python
from CSIKit.reader import get_reader

my_reader = get_reader("path/to/csi_file.dat/pcap")
csi_data = my_reader.read_file("path/to/my_csi_file.dat/pcap")
```

<!-- Raspberry Pi 4 example:

```python
from CSIKit.reader import NEXBeamformReader

my_reader = NEXBeamformReader()
csi_data = my_reader.read_file("path/to/test.pcap")
``` -->

Hardware-specific (Intel IWL5300) example:

```python
from CSIKit.reader import IWLBeamformReader

my_reader = IWLBeamformReader()
csi_data = my_reader.read_file("path/to/log.all_csi.6.7.6.dat")
```

## Supported Hardware

- Qualcomm Atheros 802.11n Chipsets
- Intel IWL5300
- Broadcom BCM4358, BCM43455c0, BCM4366c0
- ESP32 via [ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool)

## Coming Soon

### Realtime Retrieval

- Utilities for retrieving CSI directly from supported drivers for realtime preprocessing and collection.

## Mistakes and Tests

If anything is wrong, [let me know](mailto:g.r.forbes@rgu.ac.uk). I want to know why, and fix it!

I'm a PhD student working on several sensor data-focussed experiments, a few of which involve using CSI. I'm am by no means an RF engineer or particularly experienced this area. I have done and are doing as much as I can to make sure that anything produced with this is accurate. To that end, there are MATLAB .mat files included in the `tests` folder which have been generated using IWLBeamformReader, NEXBeamformReader, and scipy's `savemat` method. There are also MATLAB scripts in the `scripts` folder which can be used to check the validity of the output from this tool. In my experience I have found these tools to produce identical output to the MATLAB scripts offered by the following developers. If this is not the case, let me know.

Further to that, if there are any assertions I have made within code comments or otherwise which are factually incorrect, again let me know. I want to learn as much about this area as I reasonably can.

## Reference Links

- **[Atheros CSI Tool](https://wands.sg/research/wifi/AtherosCSI/)**: CSI extraction suite for Atheros 802.11n WiFi hardware.
  - This project was released by [Mo Li](https://personal.ntu.edu.sg/limo/) and [Yaxiong Xie](https://www.cs.princeton.edu/~yaxiongx/).
- **[Linux 802.11n CSI Tool](https://dhalperi.github.io/linux-80211n-csitool/)**: CSI extraction suite for Intel IWL5300 hardware.
  - This project was released by [Daniel Halperin](http://github.com/dhalperi).
- **[nexmon_csi](https://github.com/seemoo-lab/nexmon_csi)**: CSI extraction suite for a range of Broadcom WiFi hardware.
  - This project was released by the [Secure Mobile Networking Lab](https://github.com/seemoo-lab).
- **[ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool)**: CSI extraction utilities for ESP32 hardware.
  - This project was released by [Steven Hernandez](https://github.com/StevenMHernandez).

## License

The code in this project is licensed under MIT license. If you are using this codebase for any research or other projects, I would greatly appreciate if you could cite this repository or one of my papers.

a) "G. Forbes. CSIKit: Python CSI processing and visualisation tools for commercial off-the-shelf hardware. (2021). https://github.com/Gi-z/CSIKit."

b) "Forbes, G., Massie, S. and Craw, S., 2020, November. 
      WiFi-based Human Activity Recognition using Raspberry Pi. 
      In 2020 IEEE 32nd International Conference on Tools with Artificial Intelligence (ICTAI) (pp. 722-730). IEEE."

  ```
  @electronic{csikit:gforbes,
      author = {Forbes, Glenn},
      title = {CSIKit: Python CSI processing and visualisation tools for commercial off-the-shelf hardware.},
      url = {https://github.com/Gi-z/CSIKit},
      year = {2021}
  }

  @inproceedings{forbes2020wifi,
    title={WiFi-based Human Activity Recognition using Raspberry Pi},
    author={Forbes, Glenn and Massie, Stewart and Craw, Susan},
    booktitle={2020 IEEE 32nd International Conference on Tools with Artificial Intelligence (ICTAI)},
    pages={722--730},
    year={2020},
    organization={IEEE}
  }
  ```