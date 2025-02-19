from CSIKit.csi import CSIFrame

import ast
import numpy as np


class ESP32CSIFrame(CSIFrame):
    """CSIFrame subclass for ESP32 hardware.

        Format produced by ESP32-CSI-Tool, developed by Steven Hernandez.

        ...

        Attributes
        ----------
        type : str
            "CSI_DATA" string to indicate the beginning of a CSV payload.
        role : str
            Field indicating the role of the ESP capturing the frame.
            Possible values:
                 - AP
                 - STA
                 - PASSIVE
        mac : str
            Source MAC address for the frame.
        rssi : int
            Observed signal strength in dB.
        rate : int
            Bitmask containing the rate options used for frame transmission.
        sig_mode : str
            Field indicating the 802.11 specification used for frame transmission.
            Possible values:
                - 11abg
                - 11n
                - 11ac (Should not occur with ESP32)
        mcs : int
            Modulation Coding Scheme index (only valid for 11n frames).
            Ranges from 0-76.
        bandwidth : int
            Bandwidth used for frame transmission, in MHz.
        smoothing : int
            Field indicating whether channel estimate smoothing is recommended.
            May not be functional as ESP-IDF states it is "reserve".
        not_sounding : int
            Field indicating whether the Physical layer Protocol Data Unit is not sounding.
            May not be functional as ESP-IDF states it is "reserve".
        aggregation : str
            Field indicating whether the frame used MPDU or AMPDU.
        stbc : bool
            Field indicating whether Space-time Block Coding was used for frame transmission.
        fec_coding : bool
            Field indicating 11n frames which use LDPC/FEC.
        sgi : str
            Field indicating the guide interval used.
            Possible values:
                - long
                - short
        noise_floor : int
            Measured noise floor at the receiver, with units of 0.25dBm.
        ampdu_cnt : int
            Number of AMPDUs.
        channel : int
            802.11 channel number used for transmission.
        secondary_channel : str
            Field indicating whether the frame was received on a secondary channel, and if so which.
            Possible values:
                - none
                - above
                - below
        local_timestamp : int
            Device local timestamp (in microseconds), starting from 0 at the device boot.
        ant : int
            Antenna number from which the frame was received.
        sig_len : int
            Full length of the received 802.11 packet.
        rx_state : int
            Private ESP-IDF error code for packet transmission. 0 indicates no error.
        real_time_set : bool
            Additional field added by ESP32-CSI-Tool.
            Indicates whether an initial time value was set via serial.
        real_timestamp: float
            Additional field added by ESP32-CSI-Tool.
            Real timestamp (in seconds) factoring in the local time and a base timestamp provided by the user.
            If real_time_set=False, real_timestamp acts as a mirror of local_timestamp, instead measured in seconds.
        len : int
            Length of the 802.11 packet.
        csi_matrix : np.array
            Matrix of CSI values.

    """

    # https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_wifi.html#_CPPv418wifi_pkt_rx_ctrl_t
    # https://github.com/espressif/esp-idf/blob/9d0ca60398481a44861542638cfdc1949bb6f312/components/esp_wifi/include/esp_wifi_types.h#L314

    SUBS = {
        20: 64,
        40: 128
    }

    SIGS = {
        0: "11abg",
        1: "11n",
        3: "11ac"  # Not possible with this hardware?
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
        if len(csv_line) == 3 or len(csv_line) == 4:
            self.type = 0
            self.role = 0
            self.mac = "00:16:EA:12:34:56"
            self.rssi = 0
            self.rate = 0
            self.sig_mode = 0
            self.mcs = 0
            self.bandwidth = 0
            self.smoothing = 0
            self.not_sounding = 0
            self.aggregation = 0
            self.stbc = 0
            self.fec_coding = 0
            self.sgi = 0
            self.noise_floor = 0
            self.ampdu_cnt = 0
            self.channel = 0
            self.secondary_channel = 0
            self.local_timestamp = csv_line[0]
            self.ant = 0
            self.sig_len = 0
            self.rx_state = 0
            self.real_time_set = 0
            self.real_timestamp = csv_line[0]
            self.len = 0
            self.csi_matrix = ESP32CSIFrame.parse_matrix(csv_line[len(csv_line)-1])
            return

        if len(csv_line) == 5:
            self.type = 0
            self.role = 0
            self.mac = csv_line[1]
            self.rssi = int(csv_line[2])
            self.rate = 0
            self.sig_mode = 0
            self.mcs = 0
            self.bandwidth = 20
            self.smoothing = 0
            self.not_sounding = 0
            self.aggregation = 0
            self.stbc = 0
            self.fec_coding = 0
            self.sgi = 0
            self.noise_floor = int(csv_line[3])
            self.ampdu_cnt = 0
            self.channel = 0
            self.secondary_channel = 0
            self.local_timestamp = int(csv_line[0])
            self.ant = 0
            self.sig_len = 0
            self.rx_state = 0
            self.real_time_set = 0
            self.real_timestamp = int(csv_line[0])
            self.len = 0
            self.csi_matrix = ESP32CSIFrame.parse_matrix(csv_line[len(csv_line)-1])
            return
        elif len(csv_line) == 9:
            self.mac = f"00:16:ea:{":".join(csv_line[0].split())}"
            self.rssi = int(csv_line[4])
            self.bandwidth = 20
            self.rate = 0
            self.sig_mode = 0
            self.mcs = 0
            self.bandwidth = 20
            self.smoothing = 0
            self.not_sounding = 0
            self.aggregation = 0
            self.stbc = 0
            self.fec_coding = 0
            self.sgi = 0
            self.noise_floor = int(csv_line[5])
            self.ampdu_cnt = 0
            self.channel = 0
            self.secondary_channel = 0
            self.local_timestamp = int(csv_line[1][:-3])
            self.ant = int(csv_line[3])
            self.sig_len = 0
            self.rx_state = 0
            self.real_time_set = 0
            self.real_timestamp = int(csv_line[1][:-3])
            self.len = 0
            self.csi_matrix = ESP32CSIFrame.parse_separate_matrices(csv_line[7], csv_line[8])
            return

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

        # if len(array_string_asarray) != ESP32CSIFrame.SUBS[bandwidth]*2:
        #     return None

        int8_matrix = np.array(array_string_asarray)
        int8_matrix = int8_matrix.reshape(-1, 2)

        complex_matrix = int8_matrix.astype(np.float32).view(np.complex64)
        return complex_matrix

    @staticmethod
    def parse_separate_matrices(imag_data, real_data, bandwidth=20):
        imag_string = imag_data.replace("\"", "")
        imag_string_py = imag_string.replace(" ", ", ")
        imag_string_asarray = ast.literal_eval(imag_string_py)
        imag_int8_matrix = np.array(imag_string_asarray)

        real_string = real_data.replace("\"", "")
        real_string_py = real_string.replace(" ", ", ")
        real_string_asarray = ast.literal_eval(real_string_py)
        real_int8_matrix = np.array(real_string_asarray)

        complex_matrix = np.zeros((len(imag_int8_matrix), 1), dtype=complex)
        for n in range(len(imag_int8_matrix)):
            complex_matrix[n] = complex(real_int8_matrix[n], imag_int8_matrix[n])

        return complex_matrix

    # Seems some CSI lines are missing a value.
    # Very rare, I assume weird dropped behaviour.
    # Probably not the best way to fill the gap.
    @staticmethod
    def fill_missing(array, expected_length):
        remainder = expected_length - len(array)
        for _ in range(remainder):
            array.append(0)
