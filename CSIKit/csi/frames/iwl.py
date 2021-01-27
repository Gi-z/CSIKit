from ..csiframe import CSIFrame

class IWLCSIFrame(CSIFrame):

    __slots__ = ["timestamp_low", "bfee_count", "n_rx", "n_tx", "rssi_a", "rssi_b", "rssi_c", "noise", "agc", "antenna_sel", "length", "rate", "csi_matrix"]
    def __init__(self, header_block, csi_matrix):
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
        self.csi_matrix = csi_matrix