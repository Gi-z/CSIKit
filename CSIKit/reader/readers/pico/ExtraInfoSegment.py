from CSIKit.util import stringops

import struct

class ExtraInfoSegment:

    BOOLS = {
        1: [
            "hasLength",
            "hasVersion",
            "hasMacAddr_cur",
            "hasMacAddr_rom",
            "hasChansel",
            "hasBMode",
            "hasEVM",
            "hasTxChainMask",
            "hasRxChainMask",
            "hasTxpower",
            "hasCF",
            "hasTxTSF",
            "hasLastHWTxTSF",
            "hasChannelFlags",
            "hasTxNess",
            "hasTuningPolicy",
            "hasPLLRate",
            "hasPLLRefDiv",
            "hasPLLClkSel",
            "hasAGC",
            "hasAntennaSelection",
            "hasSamplingRate",
            "hasCFO",
            "hasSFO",
            "hasPreciseTxTiming",
        ]
    }

    def __init__(self, data: bytes, version: int):
        VERSION_MAP = {
            1: self.parseV1,
        }

        if version in VERSION_MAP:
            # Parse data with relevant parser.
            VERSION_MAP[version](data)

    def parseV1(self, data: bytes):
        pos = 0

        self.featureCode = struct.unpack("I", data[:4])[0]
        pos += 4

        # bools = self.BOOLS[1]
        # numBools = len(bools)
        # boolVals = struct.unpack(numBools*"?", data[pos:pos+numBools])
        #
        # {setattr(self, boolKey, boolVal) for boolKey, boolVal in zip(bools, boolVals)}
        #
        # pos += numBools

        self.length = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.version = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.macaddr_rom = stringops.hexToMACString(data[pos:pos + 6].hex())
        pos += 6

        self.macaddr_cur = stringops.hexToMACString(data[pos:pos + 6].hex())
        pos += 6

        self.chansel = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.bmode = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.evm = struct.unpack(20*"B", data[pos:pos + 20])
        pos += 20

        self.txChainMask = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.rxChainMask = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.txpower = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.cf = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.txTSF = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.lastHwTxTSF = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.channelFlags = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.tx_ness = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        tuningpolicy = struct.unpack("B", data[pos:pos + 1])[0]
        if tuningpolicy == 30:
            self.tuningPolicy = "Chansel"
        elif tuningpolicy == 31:
            self.tuningPolicy = "FastCC"
        elif tuningpolicy == 32:
            self.tuningPolicy = "Reset"
        elif tuningpolicy == 33:
            self.tuningPolicy = "Default"
        else:
            # clean this up
            print("invalid tuning policy.")

        self.pll_rate = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.pll_refdiv = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.pll_clock_select = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.agc = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.ant_sel = struct.unpack("BBB", data[pos:pos + 3])
        pos += 3

        self.samplingRate = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.cfo = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.sfo = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.preciseTxTiming = struct.unpack("d", data[pos:pos + 8])[0]
        pos += 8
