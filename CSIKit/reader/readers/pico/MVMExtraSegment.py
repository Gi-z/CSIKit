from CSIKit.reader.readers.pico.utils import parse_with_relevant_parser
from CSIKit.util import stringops

import struct

class MVMExtraSegment:

    def __init__(self, data: bytes, version: int):
        VERSION_MAP = {
            1: self.parseV1,
        }

        parse_with_relevant_parser(VERSION_MAP, version, data, self.__class__.__name__)

    def parseV1(self, data: bytes):
        pos = 0

        length = struct.unpack("H", data[:pos+2])[0]
        pos += 2

        self.iqDataSize = struct.unpack("I", data[pos:pos+4])[0]
        pos += 4

        # reserved 4 bytes
        pos += 4

        self.ftmClock = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        # self.samplingTick2 = struct.unpack("I", data[pos:pos + 4])[0]
        # pos += 4

        # reserved12_52[40]
        pos += 40

        self.numTones = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.reserved56 = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.rssi1 = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.rssi2 = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.sourceAddress = struct.unpack(">BBBBBB", data[pos:pos + 6])
        pos += 6

        self.addressPadding = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.csiSequence = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        # reserved77[11]
        pos += 11

        self.muClock = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        #
        # uint32_t
        # rate_n_flags; // 92
        # union
        # {
        #     uint8_t
        # blockedSection[176]
        # __attribute__((__packed__));
        # struct
        # {
        #     uint8_t
        # chain0Info96[20];
        # uint8_t
        # chain1Info96[20];
        # uint8_t
        # chain2Info96[20];
        # uint8_t
        # chain3Info96[20];
        # uint32_t
        # value176;
        # uint32_t
        # value180;
        # uint32_t
        # value184;
        # uint8_t
        # reserved188_198[10];
        # uint16_t
        # value198;
        # uint64_t
        # timeValue200;
        # uint8_t
        # reserved208_240[32];
        # uint8_t
        # chainInfo240[4];
        # uint8_t
        # chainInfo244[4];
        # uint8_t
        # chainInfo248[4];
        # uint8_t
        # chainInfo252[4];
        # uint16_t
        # value256;
        # uint16_t
        # value258;
        # uint16_t
        # value260;
        # uint16_t
        # value262;
        # uint16_t
        # value264;
        # uint16_t
        # value266;
        # uint16_t
        # value268;
        # uint16_t
        # value270;
        # } __attribute__((__packed__));
