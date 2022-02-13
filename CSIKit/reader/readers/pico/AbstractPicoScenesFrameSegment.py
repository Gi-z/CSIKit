import struct

class AbstractPicoScenesFrameSegment:

    def __init__(self, data: bytes):
        self.read_header(data)

    def read_header(self, data: bytes):
        self.subsegmentLength = struct.unpack("I", data[:4])[0]
        pos = 4

        self.subsegmentNameLength = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.subsegmentName = data[pos:pos + self.subsegmentNameLength].decode("ascii")
        if data[pos + self.subsegmentNameLength - 1:pos + self.subsegmentNameLength] == b'\x00':
            self.subsegmentName = self.subsegmentName[:-1]

        pos += self.subsegmentNameLength

        self.subsegmentVersion = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.pos = pos