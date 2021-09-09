from CSIKit.reader.readers.read_pcap import Pcap
from CSIKit.reader import get_reader
from CSIKit.util import csitools
import json

def test_pcap_extraction():
    path = "example.pcap"
    r = get_reader(path)
    num_frames = 0
    for frame in r.read_stream(path):
        csi_matrix, no_frames, no_subcarriers = csitools.get_CSI(frame,metric="",squeeze_output=True)
        num_frames += no_frames

    assert(num_frames == 4)

def test_pcap_extraction_read():
    path = "example.pcap"
    r = get_reader(path)
    csi_file = r.read_file(path)
    
    csi_matrix, no_frames, no_subcarriers = csitools.get_CSI(csi_file,metric="",squeeze_output=True)
    
    assert(no_frames == 4)

if __name__ == '__main__':
    test_pcap_extraction()
    test_pcap_extraction_read()
