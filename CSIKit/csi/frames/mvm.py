from CSIKit.csi import CSIFrame

import numpy as np

class IWLMVMCSIFrame(CSIFrame):
    """CSIFrame subclass for Intel AX2xx hardware.

        Format produced by Linux 802.11n CSI Tool, developed by Daniel Halperin.

        ...

        Attributes
        ----------
        timestamp_low : int
            Timestamp indicating the current state of the IWL5300's built in 32bit clock.
        bfee_count : int
            Sequential index of the given frame.
        n_rx : int
            Number of receiving antennas present.
        n_tx : int
            Number of transmitting antennas present.
        rssi_a : int
            RSSI observed on the first receiving antenna.
        rssi_b : int
            RSSI observed on the second receiving antenna (if present).
        rssi_c : int
            RSSI observed on the third receiving antenna (if present).
        noise : int
            Measured noise floor.
        agc : int
            Gain applied by the Automatic Gain Control system.
            Used for rescaling CSI values.
        antenna_sel : int
            Bitmask indicating the permutation setting used by the antenna selection system.
        length : int
            Expected length for the CSI payload.
        rate : int
            Bitmask containing the rate options used for frame transmission.
        csi_matrix : np.array
            Matrix of CSI values.

    """

    __slots__ = [
        "timestamp_low",
        "bfee_count",
        "n_rx",
        "n_tx",
        "rssi_a",
        "rssi_b",
        "rssi_c",
        "noise",
        "agc",
        "antenna_sel",
        "length",
        "rate",
        "csi_matrix",

        "frame_container"
    ]
    def __init__(self, header_block: list, csi_matrix: np.array, frame_container=None):
        self.timestamp_low = header_block[0]
        self.bfee_count = header_block[1]
        self.n_rx = header_block[3]
        self.n_tx = header_block[4]
        self.rssi_a = header_block[5]
        self.rssi_b = header_block[6]
        self.rssi_c = header_block[7]
        self.noise = header_block[8]
        self.agc = header_block[9]
        self.antenna_sel = header_block[10]
        self.length = header_block[11]
        self.rate = header_block[12]
        # self.perm = header_block[13]
        self.source_mac = header_block[13]
        self.csi_matrix = csi_matrix

        if frame_container:
            self.frame_container = frame_container

    @classmethod
    def from_picoscenes(cls, frame_container: "FrameContainer"):
        header_block = [
            frame_container.RxSBasic.timestamp,
            0,
            0,
            frame_container.CSI.numRx,
            frame_container.CSI.numSTS,
            frame_container.RxSBasic.rssi_ctl0,
            frame_container.RxSBasic.rssi_ctl1,
            frame_container.RxSBasic.rssi_ctl2,
            frame_container.RxSBasic.noiseFloor,
            0,
            frame_container.CSI.antSelByte,
            0,
            0,
            frame_container.RxSBasic.source_mac
        ]
        return cls(header_block, frame_container.CSI.parsed_csi, frame_container)