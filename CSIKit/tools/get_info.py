
from CSIKit.reader import get_reader

def display_info(path: str, scaled: bool=False, filter_mac: str=None):
    reader = get_reader(path)

    csi_data = reader.read_file(path, scaled=scaled, filter_mac=filter_mac)
    metadata = csi_data.get_metadata()

    print("Hardware: {}".format(metadata.chipset))
    print("Backend: {}".format(metadata.backend))
    print("Bandwidth: {}MHz".format(metadata.bandwidth))
    print("Antenna Configuration: {}".format(metadata.antenna_config))
    print("Frame Count: {}".format(metadata.frames))
    print("Subcarrier Count: {}".format(metadata.subcarriers))
    print("Length: {0:.2f}s".format(metadata.time_length))
    print("Average Sample Rate: {0:.2f}Hz".format(metadata.average_sample_rate))

    if metadata.average_rssi != -1:
        print("Average RSSI: {}dBm".format(metadata.average_rssi))

    print("CSI Shape: {}".format((metadata.frames, *metadata.csi_shape)))