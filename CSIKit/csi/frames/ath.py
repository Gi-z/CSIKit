import collections

from CSIKit.csi import CSIFrame

from collections import namedtuple

import numpy as np

class ATHCSIFrame(CSIFrame):
    """CSIFrame subclass for Atheros hardware.

        Format produced by Atheros CSI Tool, developed by Mo Li and Yaxiong Xie.

        ...

        Attributes
        ----------
        timestamp : int
            Epoch timestamp for the frame.
        csi_length : int
            Length of the binary CSI payload.
        tx_channel : int
            Central frequency (MHz) of the 802.11 channel used for frame transmission.
            2.4GHz: https://en.wikipedia.org/wiki/List_of_WLAN_channels#2.4_GHz_(802.11b/g/n/ax)
            5GHz: https://en.wikipedia.org/wiki/List_of_WLAN_channels#5_GHz_(802.11a/h/j/n/ac/ax)
        err_info : int
            PHY error code. 0 when valid.
        noise_floor : int
            Measured noise floor.
        rate : int
            Bitmask containing the rate options used for frame transmission.
        bandwidth : int
            Binary value indicating the bandwidth used for frame transmission.
            0 = 20MHz.
            1 = 40MHz.
        num_tones : int
            Number of active subcarriers present.
        nr : int
            Number of receiving antennas present.
        nc : int
            Number of transmitting antennas present.
        rssi : int
            Total observed RSSI (signal strength in dB).
        rssi_1 : int
            RSSI observed on the first receiving antenna.
        rssi_2 : int
            RSSI observed on the second receiving antenna (if present).
        rssi_3 : int
            RSSI observed on the third receiving antenna (if present).
        payload_length : int
            Expected length for the CSI payload.
        csi_matrix : np.array
            Matrix of CSI values.

    """

    __slots__ = [
        "timestamp",
        "csi_length",
        "tx_channel",
        "err_info",
        "noise_floor",
        "rate",
        "bandwidth",
        "num_tones",
        "nr",
        "nc",
        "rssi",
        "rssi_1",
        "rssi_2",
        "rssi_3",
        "payload_length",
        "csi_matrix"
    ]

    HEADER_DATA = collections.namedtuple("header_data", __slots__[:-1])

    def __init__(self, header_data: namedtuple, csi_matrix: np.array):
        self.timestamp = header_data.timestamp
        self.csi_length = header_data.csi_length
        self.tx_channel = header_data.tx_channel
        self.err_info = header_data.err_info
        self.noise_floor = header_data.noise_floor
        self.rate = header_data.rate
        self.bandwidth = header_data.bandwidth
        self.num_tones = header_data.num_tones
        self.nr = header_data.nr
        self.nc = header_data.nc
        self.rssi = header_data.rssi
        self.rssi_1 = header_data.rssi_1
        self.rssi_2 = header_data.rssi_2
        self.rssi_3 = header_data.rssi_3
        self.payload_length = header_data.payload_length
        self.csi_matrix = csi_matrix

    @classmethod
    def from_picoscenes(cls, frame_container: "FrameContainer"):
        header_data = cls.HEADER_DATA._make([
            frame_container.RxSBasic.timestamp,
            0,
            frame_container.RxSBasic.channelFreq,
            0,
            frame_container.RxSBasic.noiseFloor,
            0,
            frame_container.RxSBasic.cbw,
            frame_container.CSI.numTone,
            frame_container.CSI.numRx,
            frame_container.CSI.numSTS,
            frame_container.RxSBasic.rssi,
            frame_container.RxSBasic.rssi_ctl0,
            frame_container.RxSBasic.rssi_ctl1,
            frame_container.RxSBasic.rssi_ctl2,
            0
        ])
        return cls(header_data, frame_container.CSI.parsed_csi)
