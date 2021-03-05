from CSIKit.csi import CSIFrame

from collections import namedtuple

import numpy as np

class ATHCSIFrame(CSIFrame):

    __slots__ = ["timestamp", "csi_length", "tx_channel", "err_info", "noise_floor", "rate", "bandwidth", "num_tones", "nr", "nc", "rssi", "rssi_1", "rssi_2", "rssi_3", "payload_length", "csi_matrix"]
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