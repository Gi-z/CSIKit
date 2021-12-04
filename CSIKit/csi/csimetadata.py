class CSIMetadata:

    __slots__ = ["chipset", "backend", "bandwidth", "antenna_config", "frames", "subcarriers", "time_length", "average_sample_rate", "average_rssi", "csi_shape"]
    def __init__(self, data: dict):
        self.chipset = data["chipset"]
        self.backend = data["backend"]
        self.bandwidth = data["bandwidth"]
        self.antenna_config = data["antenna_config"]
        self.frames = data["frames"]
        self.subcarriers = data["subcarriers"]
        self.time_length = data["time_length"]
        self.average_sample_rate = data["average_sample_rate"]
        self.average_rssi = data["average_rssi"]
        self.csi_shape = data["csi_shape"]

    def __str__(self):

        s = ""
        s += "Hardware: {}\n".format(self.chipset)
        s += "Backend: {}\n".format(self.backend)
        s += "Bandwidth: {}MHz\n".format(self.bandwidth)
        s += "Antenna Configuration: {}\n".format(self.antenna_config)
        s += "Frame Count: {}\n".format(self.frames)
        s += "Subcarrier Count: {}\n".format(self.subcarriers)
        s += "Length: {0:.2f}s\n".format(self.time_length)
        s += "Average Sample Rate: {0:.2f}Hz\n".format(self.average_sample_rate)

        if self.average_rssi != -1:
            s += "Average RSSI: {}dBm\n".format(self.average_rssi)

        s += "CSI Shape: {}".format((self.frames, *self.csi_shape))

        return s
