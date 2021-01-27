from ..csiframe import CSIFrame

class NEXCSIFrame(CSIFrame):

    __slots__ = ["timestamp", "rssi", "frame_control", "source_mac", "sequence_no", "core", "spatial_stream", "channel_spec", "chip", "csi_matrix"]
    def __init__(self, header_block, csi_matrix):
        self.timestamp = header_block["timestamp"]
        self.rssi = header_block["rssi"]
        self.frame_control = header_block["frame_control"]
        self.source_mac = header_block["source_mac"]
        self.sequence_no = header_block["sequence_no"]
        self.core = header_block["core"]
        self.spatial_stream = header_block["spatial_stream"]
        self.channel_spec = header_block["channel_spec"]
        self.chip = header_block["chip"]
        self.csi_matrix = csi_matrix