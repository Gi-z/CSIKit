
from CSIKit.reader import get_reader

def display_info(path):
    reader = get_reader(path)
    csi_data = reader.read_file(path)
    metadata = csi_data.get_metadata()

    print("Hardware: {}".format(metadata.chipset))
    print("Bandwidth: {}MHz".format(metadata.bandwidth))
    print("Antenna Configuration: {}".format(metadata.antenna_config))
    print("Frame Count: {}".format(metadata.frames))
    print("Subcarrier Count: {}".format(metadata.subcarriers))
    print("Length: {0:.2f}s".format(metadata.time_length))
    print("Average Sample Rate: {0:.2f}Hz".format(metadata.average_sample_rate))
    print("CSI Shape: {}".format((metadata.frames, *metadata.csi_shape)))