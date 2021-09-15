import struct

class ModularPicoScenesFrame:
    SIZE = 11

    def __init__(self, data: bytes):
        self.parse_header(data)

    def parse_header(self, data: bytes):
        self.frameLength = struct.unpack("I", data[:4])[0]
        pos = 4

        self.magicWord = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.frameVersion = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.numRxSegments = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        # if self.frameLength != len(data):
        #     self.log_exception("Invalid length")
        # if self.magicWord != 0x20150315:
        #     self.log_exception("Invalid magic")
        # if self.frameVersion != 0x1:
        #     self.log_exception("Unsupported frame version")