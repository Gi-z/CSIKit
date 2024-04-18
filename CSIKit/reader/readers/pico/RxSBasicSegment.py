import struct

from CSIKit.reader.readers.pico.utils import parse_with_relevant_parser

class RxSBasicSegment:

    def __init__(self, data: bytes, version: int):
        VERSION_MAP = {
            1: self.parseV1,
            2: self.parseV2,
            3: self.parseV3,
            4: self.parseV4
        }

        parse_with_relevant_parser(VERSION_MAP, version, data, self.__class__.__name__)

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

        self.noiseFloor = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl0 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl1 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl2 = struct.unpack("b", data[pos:pos + 1])[0]
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

        self.noiseFloor = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl0 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl1 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl2 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

    def parseV3(self, data: bytes):
        pos = 0

        self.deviceType = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.timestamp = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.centerFreq = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.controlFreq = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.cbw = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.packetFormat = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.pkt_cbw = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.guardInterval = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.mcs = struct.unpack("B", data[pos:pos + 1])[0]
        if self.mcs != 4:
            x = 0
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

        self.noiseFloor = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl0 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl1 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl2 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

    def parseV4(self, data: bytes):
        pos = 0

        self.deviceType = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.timestamp = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.systemtime = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.centerFreq = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.controlFreq = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.cbw = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.packetFormat = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.pkt_cbw = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.guardInterval = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.mcs = struct.unpack("B", data[pos:pos + 1])[0]
        if self.mcs != 4:
            x = 0
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

        self.noiseFloor = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl0 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl1 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.rssi_ctl2 = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1