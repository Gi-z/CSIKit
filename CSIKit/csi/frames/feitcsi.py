from CSIKit.csi import CSIFrame

import numpy as np

class FeitCSIFrame(CSIFrame):
    """
        CSIFrame subclass for FeiCSI.
        More https://feitcsi.kuskosoft.com/csi_format/    
    """

    def __init__(self, header_data: {}, csi_matrix: np.array):
        self.csi_length = header_data["csi_length"]
        self.ftm_clock = header_data["ftm_clock"]
        self.mu_clock = header_data["mu_clock"]
        self.num_rx = header_data["num_rx"]
        self.num_tx = header_data["num_tx"]
        self.num_subcarriers = header_data["num_subcarriers"]
        self.rssi_1 = header_data["rssi_1"]
        self.rssi_2 = header_data["rssi_2"]
        self.source_mac = header_data["source_mac"]
        self.channel_width = header_data["channel_width"]
        self.rate_format = header_data["rate_format"]
        self.mcs = header_data["mcs"]
        self.antenna_a = header_data["antenna_a"]
        self.antenna_b = header_data["antenna_b"]
        self.ldpc = header_data["ldpc"]
        self.ss = header_data["ss"]
        self.beamforming = header_data["beamforming"]
        self.csi_matrix = csi_matrix