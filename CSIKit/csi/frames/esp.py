from CSIKit.csi import CSIFrame

import ast
import numpy as np

class ESP32CSIFrame(CSIFrame):

    # https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_wifi.html#_CPPv418wifi_pkt_rx_ctrl_t
    # https://github.com/espressif/esp-idf/blob/9d0ca60398481a44861542638cfdc1949bb6f312/components/esp_wifi/include/esp_wifi_types.h#L314

    SIGS = {
        0: "nonHT",
        1: "HT",
        3: "VHT"
    }

    SECONDARY_CHANNELS = {
        0: "none",
        1: "above",
        2: "below"
    }

    __slots__ = ["type", "role", "mac", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding",
                "aggregation", "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel",
                "local_timestamp", "ant", "sig_len", "rx_state", "real_time_set", "real_timestamp", "len", "CSI_DATA"]
    def __init__(self, csv_line: list):
        self.type = csv_line[0]
        self.role = csv_line[1]
        self.mac = csv_line[2]

        self.rssi = int(csv_line[3])

        # https://en.wikipedia.org/wiki/IEEE_802.11n-2009#Data_rates
        self.rate = int(csv_line[4])

        self.sig_mode = self.SIGS[int(csv_line[5])]

        # https://en.wikipedia.org/wiki/IEEE_802.11n-2009#Data_rates
        self.mcs = int(csv_line[6])

        # MHz
        self.bandwidth = 20 if csv_line[7] == "0" else 40

        # Supposedly reserved
        self.smoothing = int(csv_line[8])
        self.not_sounding = int(csv_line[9])

        self.aggregation = "MPDU" if csv_line[10] == "0" else "AMPDU"
        self.stbc = bool(int(csv_line[11]))
        self.fec_coding = bool(int(csv_line[12]))

        self.sgi = "long" if csv_line[13] == "0" else "short"

        # Unit: 0.25dBm
        self.noise_floor = int(csv_line[14])
        self.ampdu_cnt = int(csv_line[15])
        self.channel = int(csv_line[16])
        self.secondary_channel = self.SECONDARY_CHANNELS[int(csv_line[17])]
        self.local_timestamp = int(csv_line[18])
        self.ant = int(csv_line[19])

        self.sig_len = int(csv_line[20])
        self.rx_state = int(csv_line[21])
        self.real_time_set = bool(int(csv_line[22]))
        self.real_timestamp = float(csv_line[23])
        self.len = int(csv_line[24])

        string_data = csv_line[25]
        self.csi_matrix = ESP32CSIFrame.parse_matrix(string_data)

    @staticmethod
    def parse_matrix(string_data, bandwidth=20):
        array_string = string_data.replace(" ", ", ")
        array_string_asarray = ast.literal_eval(array_string)

        if bandwidth == 20 and len(array_string_asarray) < 128:
            ESP32CSIFrame.fill_missing(array_string_asarray, 128)
        elif bandwidth == 40 and len(array_string_asarray) < 256:
            ESP32CSIFrame.fill_missing(array_string_asarray, 256)

        int8_matrix = np.array(array_string_asarray)
        int8_matrix = int8_matrix.reshape(-1, 2)

        complex_matrix = int8_matrix.astype(np.float32).view(np.complex64)
        return complex_matrix

    # Seems some CSI lines are missing a value.
    # Very rare, I assume weird dropped behaviour.
    # Probably not the best way to fill the gap.
    @staticmethod
    def fill_missing(array, expected_length):
        remainder = expected_length - len(array)
        for _ in range(remainder):
            array.append(0)