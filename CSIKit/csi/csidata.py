
class CSIData:

    def __init__(self, filename=""):
        
        self.frames = []

        self.expected_frames = 0
        self.skipped_frames = 0

        self.filename = filename

    def push_frame(self, frame):
        self.frames.append(frame)

    def get_metadata(self):
        pass
        # reader = get_reader(path)
        # hardware_info_string = get_hardware(reader)

        # unmodified_csi_matrix = reader.csi_trace[0]["csi"]
        # _, no_frames, no_subcarriers = get_CSI(reader.csi_trace)

        # if len(unmodified_csi_matrix.shape) <= 2:
        #     rx_count, tx_count = (1, 1)
        # elif len(unmodified_csi_matrix.shape) == 3:
        #     rx_count, tx_count = unmodified_csi_matrix.shape[1:]

        # antenna_config_string = "{} Rx, {} Tx".format(rx_count, tx_count)

        # timestamps = get_timestamps(reader.csi_trace)
        # final_timestamp = timestamps[-1]

        # if final_timestamp == 0:
        #     average_sample_rate = 0
        # else:
        #     average_sample_rate = no_frames/final_timestamp

        # print("Hardware: {}".format(hardware_info_string))
        # print("Antenna Configuration: {}".format(antenna_config_string))
        # print("Frame Count: {}".format(no_frames))
        # print("Subcarrier Count: {}".format(no_subcarriers))
        # print("Length: {0:.2f}s".format(final_timestamp))
        # print("Average Sample Rate: {0:.2f}Hz".format(average_sample_rate))
        # print("CSI Shape: {}".format((no_frames, *unmodified_csi_matrix.shape)))