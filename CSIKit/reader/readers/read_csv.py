import os

from CSIKit.csi import CSIData
from CSIKit.csi.frames import ESP32CSIFrame
from CSIKit.reader import Reader
from CSIKit.util import csitools, constants

ESP32_HEADER = ["type", "role", "mac", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding",
                "aggregation", "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel",
                "local_timestamp", "ant", "sig_len", "rx_state", "real_time_set", "real_timestamp", "len", "CSI_DATA"]

THROWIE_HEADER = ["time", "movement_detected", "csi"]
THROWIE_HEADER2 = ["time", "pcc", "movement_detected", "csi"]

FITHOMES_HEADER = ["time", "src_mac", "rssi", "noise_floor", "csi"]
FITHOMES_HEADER2 = ["sensor_id", "timestamp", "sequence_identifier", "antenna", "rssi", "noise_floor", "interval", "imag", "real"]

HEADER_NAME_MAPPINGS = {
    "ESP32": ESP32_HEADER,
    "THROWIE": THROWIE_HEADER,
    "THROWIE2": THROWIE_HEADER2,
    "FITHOMES": FITHOMES_HEADER,
    "FITHOMES2": FITHOMES_HEADER2
}

HEADER_FRAMES = {
    "ESP32": ESP32CSIFrame,
    "THROWIE": ESP32CSIFrame,
    "THROWIE2": ESP32CSIFrame,
    "FITHOMES": ESP32CSIFrame,
    "FITHOMES2": ESP32CSIFrame,
}

BACKEND_MAPPING = {
    "ESP32": "ESP32 CSI Tool",
    "THROWIE": "prototype thing",
    "THROWIE2": "prototype thing",
    "FITHOMES": "FitHomes CSI Platform (Alpha)",
    "FITHOMES2": "FitHomes CSI Platform (Alpha2)"
}

# Divisor converting the other layouts' timestamp column to seconds (treated as milliseconds,
# as before). The ESP32 layout is timed from local_timestamp instead; see esp32_seconds().
TIMESTAMP_DIVISOR = {
    "THROWIE": 1000,
    "THROWIE2": 1000,
    "FITHOMES": 1000,
    "FITHOMES2": 1000,
}

# ESP32 rx_ctrl.timestamp (local_timestamp) is a 32-bit microsecond counter: it wraps every ~71.6 min.
ESP32_LOCAL_TIMESTAMP_RANGE = 2 ** 32


def esp32_seconds(local_timestamps):
    """Seconds since the first frame from ESP32 local_timestamp values, undoing 32-bit wraps.

    local_timestamp is the radio's own receive time in microseconds (precise because
    ESP32-CSI-Tool disables power saving). real_timestamp is not used: older ESP32-CSI-Tool
    versions print it as "<seconds>.<microseconds>" without zero-padding the microseconds
    ("1.87258" is 1.087258 s), newer ones print a steady-clock double with 6 significant
    digits, and the two can't be told apart from the values alone.
    """
    seconds = []
    wrap_offset = 0
    previous = None
    for local in local_timestamps:
        # Only a drop of more than half the range is a wrap.
        if previous is not None and previous - local > ESP32_LOCAL_TIMESTAMP_RANGE // 2:
            wrap_offset += ESP32_LOCAL_TIMESTAMP_RANGE
        previous = local
        seconds.append((local + wrap_offset) / 1e6)
    return [t - seconds[0] for t in seconds] if seconds else seconds

LAST_CHAR_MAPPING = {
    "ESP32": "]",
    "THROWIE": "]",
    "THROWIE2": "]",
    "FITHOMES": "]",
    "FITHOMES2": "]",
}

class CSVBeamformReader(Reader):

    def __init__(self):
        pass

    @staticmethod
    def can_read(path: str) -> bool:
        if os.path.exists(path):
            try:
                data = open(path)

                first_line = data.readline()[:-1]
                second_line = data.readline()[:-1]

                first_split = first_line.split(",")
                second_split = second_line.split(",")

                # If they are not the same length then the
                # CSV is malformed or contains a separate header line.
                if len(first_split) == len(second_split):
                    # If we have observe a supported header format.
                    # TODO: Add functionality to add your own headers.
                    return first_split in HEADER_NAME_MAPPINGS.values()
            except UnicodeDecodeError as _:
                return False

        return False

    def read_file(self, path: str, scaled: bool = False, remove_unusable_subcarriers: bool = True, filter_mac: str = None) -> CSIData:

        # if scaled:
        #     print("Scaling not yet supported in CSV formats.")

        self.filename = os.path.basename(path)
        if not os.path.exists(path):
            raise Exception("File not found: {}".format(path))

        data = open(path, "r")

        ret_data = CSIData(self.filename, "", "CSV Format", filter_mac=filter_mac)

        header_line = data.readline()[:-1].split(",")

        # TODO: Add support for adding custom headers.
        if header_line not in HEADER_NAME_MAPPINGS.values():
            print("Unsupported CSV format.")
            exit(1)

        header_name = None
        for key, val in HEADER_NAME_MAPPINGS.items():
            if val == header_line:
                header_name = key
                break

        if not header_name:
            print("Unable to find hardware name for format.")
            exit(1)

        ret_data.set_chipset(header_name)
        ret_data.set_backend(BACKEND_MAPPING[header_name])

        header_frame = HEADER_FRAMES[header_name]
        last_char = LAST_CHAR_MAPPING[header_name]

        first_timestamp = -1
        timestamp_divisor = TIMESTAMP_DIVISOR.get(header_name)
        frames = []

        while True:
            data_line = data.readline().split(",")
            if not data_line or len(data_line) != len(header_line):
                break

            if last_char and last_char not in data_line[-1]:
                break

            new_frame = header_frame(data_line)
            if new_frame.csi_matrix is None:
                # Malformed CSI buffer (values lost in transit): skip the row, but count it.
                ret_data.skipped_frames += 1
                continue

            if ret_data.bandwidth == 0:
                ret_data.bandwidth = new_frame.bandwidth

            if scaled:
                new_frame.csi_matrix = csitools.scale_csi_frame(new_frame.csi_matrix, new_frame.rssi, new_frame.noise_floor)

            if header_name == "ESP32":
                # Timed from local_timestamp once all rows are read (see esp32_seconds).
                frames.append(new_frame)
                continue

            if first_timestamp == -1:
                first_timestamp = float(new_frame.real_timestamp) / timestamp_divisor
                new_frame.real_timestamp = 0
            else:
                new_frame.real_timestamp = (float(new_frame.real_timestamp) / timestamp_divisor) - first_timestamp

            # no_subcarriers = new_frame.csi_matrix.shape[0]

            # if remove_unusable_subcarriers and header_name == "ESP32":
            #     new_frame.csi_matrix = new_frame.csi_matrix[[x for x in range(no_subcarriers) if x not in constants.ESP32_20MHZ_UNUSABLE]]
            # elif remove_unusable_subcarriers:
            #     print("Unsupported header format for null/pilot/guard subcarrier removal.")

            ret_data.push_frame(new_frame, float(new_frame.real_timestamp))

        # frame.real_timestamp holds seconds since the first frame, as for the other layouts.
        for frame, timestamp in zip(frames, esp32_seconds([f.local_timestamp for f in frames])):
            frame.real_timestamp = timestamp
            ret_data.push_frame(frame, timestamp)

        return ret_data