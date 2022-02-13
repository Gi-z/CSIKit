import csiread

csidata = csiread.Nexmon("example_4366c0_4x4mimo.pcap", chip="4366c0", bw=80)
csidata.read()
