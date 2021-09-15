import struct

class RxSBasicSegment:

    def __init__(self, data: bytes, version: int):
        VERSION_MAP = {
            1: self.parseV1,
            2: self.parseV2
        }

        if version in VERSION_MAP:
            # Parse data with relevant parser.
            VERSION_MAP[version](data)

    def parseV1(self, data: bytes):
        pos = 0

        self.deviceType = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.timestamp = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.channelFreq = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.packetFormat = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.cbw = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.guardInterval = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.mcs = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numSTS = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numESS = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numRx = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numUser = 0
        self.userIndex = 0

        self.noiseFloor = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.rssi = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl0 = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl1 = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl2 = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

    def parseV2(self, data: bytes):
        pos = 0

        self.deviceType = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.timestamp = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.channelFreq = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.packetFormat = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.cbw = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.guardInterval = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.mcs = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numSTS = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numESS = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numRx = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numUser = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.userIndex = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.noiseFloor = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.rssi = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl0 = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl1 = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl2 = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1