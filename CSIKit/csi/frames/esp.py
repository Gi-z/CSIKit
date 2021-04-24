from CSIKit.csi import CSIFrame

import ast
import numpy as np

class ESP32CSIFrame(CSIFrame):

    # https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_wifi.html#_CPPv418wifi_pkt_rx_ctrl_t

    __slots__ = ["type", "role", "mac", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding",
                "aggregation", "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel",
                "local_timestamp", "ant", "sig_len", "rx_state", "real_time_set", "real_timestamp", "len", "CSI_DATA"]
    def __init__(self, csv_line: list):
        self.type = csv_line[0]
        self.role = csv_line[1]
        self.mac = csv_line[2]
        self.rssi = csv_line[3]
        self.rate = csv_line[4]
        self.sig_mode = csv_line[5]
        self.mcs = csv_line[6]
        self.bandwidth = 20 if csv_line[7] == "0" else 40
        self.smoothing = csv_line[8]
        self.not_sounding = csv_line[9]
        self.aggregation = csv_line[10]
        self.stbc = csv_line[11]
        self.fec_coding = csv_line[12]
        self.sgi = csv_line[13]
        self.noise_floor = csv_line[14]
        self.ampdu_cnt = csv_line[15]
        self.channel = csv_line[16]
        self.secondary_channel = csv_line[17]
        self.local_timestamp = csv_line[18]
        self.ant = csv_line[19]
        self.sig_len = csv_line[20]
        self.rx_state = csv_line[21]
        self.real_time_set = csv_line[22]
        self.real_timestamp = csv_line[23]
        self.len = csv_line[24]

        string_data = csv_line[25]
        self.csi_matrix = ESP32CSIFrame.parse_matrix(string_data)

    @staticmethod
    def parse_matrix(string_data):
        array_string = string_data.replace(" ", ", ")
        array_string_asarray = ast.literal_eval(array_string)

        int8_matrix = np.array(array_string_asarray)
        int8_matrix = int8_matrix.reshape(-1, 2)

        complex_matrix = int8_matrix.astype(np.float32).view(np.complex64)
        return complex_matrix
