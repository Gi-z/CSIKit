from CSIKit.csi import CSIFrame


class USRPCSIFrame(CSIFrame):
    """CSIFrame subclass for USRP hardware.

        Format produced by PicoScenes, developed by Zhiping Jiang and contributors.

        ...

        Attributes
        ----------
        timestamp : int
            Epoch timestamp for the frame.
        device_type : int
            Numeric identifier for the PicoScenes device type.
        user_index : int
            Lorem ipsum dolor sit amet. (Maybe the Phy index?)
        channel_freq : int
            Central frequency (MHz) of the 802.11 channel used for frame transmission.
            2.4GHz: https://en.wikipedia.org/wiki/List_of_WLAN_channels#2.4_GHz_(802.11b/g/n/ax)
            5GHz: https://en.wikipedia.org/wiki/List_of_WLAN_channels#5_GHz_(802.11a/h/j/n/ac/ax)
        guard_interval : int
            Guard interval (spacing between IQ symbols) used for frame transmission (in ns).
        noise_floor : int
            Measured noise floor.
        mcs : int
            Bitmask containing the rate options used for frame transmission.
        cbw : int
            Bandwidth used for frame transmission (in MHz).
        num_tones : int
            Number of active subcarriers present.
        num_rx : int
            Number of receiving antennas present.
        num_STS : int
            Number of transmitting antennas present.
        num_ESS : int
            Lorem ipsum dolor sit amet.
        rssi : int
            Total observed RSSI (signal strength in dB).
        rssi_1 : int
            RSSI observed on the first receiving antenna.
        rssi_2 : int
            RSSI observed on the second receiving antenna (if present).
        rssi_3 : int
            RSSI observed on the third receiving antenna (if present).
        csi_matrix : np.array
            Matrix of CSI values.

    """

    __slots__ = [
        "timestamp",
        "csi_length",
        "tx_channel",
        "mac",
        "err_info",
        "noise_floor",
        "rate",
        "bandwidth",
        "num_tones",
        "num_rx",
        "num_STS",
        "rssi",
        "rssi_1",
        "rssi_2",
        "rssi_3",
        "csi_matrix"
    ]

    def __init__(self, frame_container: "FrameContainer"):
        self.timestamp = frame_container.RxSBasic.timestamp
        if hasattr(frame_container.RxSBasic, "channelFreq"):
            self.channel_freq = frame_container.RxSBasic.channelFreq
        else:
            self.channel_freq = frame_container.RxSBasic.centerFreq
        self.mac = frame_container.RxSBasic.source_mac
        self.noise_floor = frame_container.RxSBasic.noiseFloor
        self.bandwidth = frame_container.RxSBasic.cbw
        self.num_tones = frame_container.CSI.numTone
        self.num_rx = frame_container.RxSBasic.numRx
        self.num_STS = frame_container.RxSBasic.numSTS
        self.rssi = frame_container.RxSBasic.rssi
        self.rssi_1 = frame_container.RxSBasic.rssi_ctl0
        self.rssi_2 = frame_container.RxSBasic.rssi_ctl1
        self.rssi_3 = frame_container.RxSBasic.rssi_ctl2
        self.csi_matrix = frame_container.CSI.parsed_csi

    @classmethod
    def from_picoscenes(cls, frame_container: "FrameContainer"):
        return cls(frame_container)