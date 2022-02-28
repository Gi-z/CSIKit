from CSIKit.util import stringops

import struct

class MVMExtraSegment:

    def __init__(self, data: bytes, version: int):
        VERSION_MAP = {
            1: self.parseV1,
        }

        if version in VERSION_MAP:
            # Parse data with relevant parser.
            VERSION_MAP[version](data)

    def parseV1(self, data: bytes):
        pos = 0

        self.iqDataSize = struct.unpack("I", data[:pos+4])[0]
        pos += 4

        # reserved 4 bytes
        pos += 4

        self.ftmClock = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.samplingTick2 = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4