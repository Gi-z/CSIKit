from CSIKit.reader.readers.read_pcap import Pcap
from CSIKit.reader import get_reader
from CSIKit.util import csitools

def test_pcap_extraction():
    path = "example.pcap"
    r = get_reader(path)
    for frame in r.read_stream(path):
        csi_matrix, no_frames, no_subcarriers = csitools.get_CSI(frame,metric="",squeeze_output=True)
        print(csi_matrix)
        print(no_frames)
        print(no_subcarriers)

if __name__ == '__main__':
    test_pcap_extraction()
