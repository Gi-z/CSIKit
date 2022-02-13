from CSIKit.reader import NEXBeamformReader
from CSIKit.util import csitools

reader = NEXBeamformReader()
csidata = reader.read_file("example_4366c0_4x4mimo.pcap")
#_, _, _, = csitools.get_CSI(csidata)
