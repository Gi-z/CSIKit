from .csitools import get_CSI, get_timestamps
from .reader import get_reader, get_hardware

def display_info(path):
    reader = get_reader(path)
    hardware_info_string = get_hardware(reader)

    unmodified_csi_matrix = reader.csi_trace[0]["csi"]
    _, no_frames, no_subcarriers = get_CSI(reader.csi_trace)

    if len(unmodified_csi_matrix.shape) <= 2:
        rx_count, tx_count = (1, 1)
    elif len(unmodified_csi_matrix.shape) == 3:
        rx_count, tx_count = unmodified_csi_matrix.shape[1:]

    antenna_config_string = "{} Rx, {} Tx".format(rx_count, tx_count)

    timestamps = get_timestamps(reader.csi_trace)
    final_timestamp = timestamps[-1]

    average_sample_rate = no_frames/final_timestamp

    print("Hardware: {}".format(hardware_info_string))
    print("Antenna Configuration: {}".format(antenna_config_string))
    print("Frame Count: {}".format(no_frames))
    print("Subcarrier Count: {}".format(no_subcarriers))
    print("Length: {0:.2f}s".format(final_timestamp))
    print("Average Sample Rate: {0:.2f}Hz".format(average_sample_rate))
    print("CSI Shape: {}".format((no_frames, *unmodified_csi_matrix.shape)))