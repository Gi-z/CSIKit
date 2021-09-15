from CSIKit.util import stringops, byteops

from math import floor

import numpy as np

import struct

BITS_PER_SYMBOL = 10
BITS_PER_COMPLEX_SYMBOL = 2 * BITS_PER_SYMBOL

class CSISegment:

    SignalMatrixStorageMajority = {
        "R": "RowMajority",
        "C": "ColumnMajority",
        "U": "UndefinedMajority"
    }

    def __init__(self, data: bytes, version: int):
        VERSION_MAP = {
            1: self.parseV1or2,
            2: self.parseV1or2,
            3: self.parseV3,
        }

        self.version = version

        if version in VERSION_MAP:
            # Parse data with relevant parser.
            VERSION_MAP[version](data)

    def parseQCA9300CSIData(self, data: bytes, pos: int):

        num_tones = self.numTone
        nc = self.numSTS
        nr = self.numRx
        csi_buf = data[pos:]

        csi = np.empty((num_tones, nc, nr), dtype=complex)

        bitmask = (1 << BITS_PER_SYMBOL) - 1
        idx = 0
        bits_left = 16

        h_data = csi_buf[idx]
        idx += 1
        h_data += (csi_buf[idx] << 8)
        idx += 1
        current_data = h_data & ((1 << 16) - 1)

        for k in range(num_tones):
            for nc_idx in range(nc):
                for nr_idx in range(nr):
                    if (bits_left - BITS_PER_SYMBOL) < 0:
                        current_data, idx, bits_left = byteops.get_next_bits(csi_buf, current_data, idx, bits_left)

                    imag = current_data & bitmask
                    imag = byteops.signbit_convert(imag, BITS_PER_SYMBOL)
                    imag += 1

                    bits_left -= BITS_PER_SYMBOL
                    current_data = current_data >> BITS_PER_SYMBOL

                    if (bits_left - BITS_PER_SYMBOL) < 0:
                        current_data, idx, bits_left = byteops.get_next_bits(csi_buf, current_data, idx, bits_left)

                    real = current_data & bitmask
                    real = byteops.signbit_convert(real, BITS_PER_SYMBOL)
                    real += 1

                    bits_left -= BITS_PER_SYMBOL
                    current_data = current_data >> BITS_PER_SYMBOL

                    csi[k, nc_idx, nr_idx] = complex(real, imag)

        self.parsed_csi = csi

    def parseIWL5300CSIData(self, data: bytes, pos: int):
        self.actualNumSTSPerChain = (self.CSIBufferLength - 12) / 60 / self.numRx

        payload = data[pos:pos + self.CSIBufferLength]

        ntx = int(self.actualNumSTSPerChain)
        nrx = int(self.numRx)
        ant_sel = int(self.antSelByte)

        csi = np.zeros((30, nrx, ntx), dtype=np.complex)

        perm = np.array([0, 1, 2])
        if sum(perm) == nrx:
            perm[0] = ((ant_sel) & 0x3)
            perm[1] = ((ant_sel >> 2) & 0x3)
            perm[2] = ((ant_sel >> 4) & 0x3)

        index = 0
        for i in range(30):
            index += 3
            remainder = index % 8
            for j in range(nrx):
                for k in range(ntx):
                    ind8 = floor(index / 8)

                    if ind8 + 2 >= len(payload):
                        break

                    real = (payload[ind8] >> remainder) | (payload[1 + ind8] << (8 - remainder))
                    imag = (payload[1 + ind8] >> remainder) | (payload[2 + ind8] << (8 - remainder))

                    real = np.int8(real)
                    imag = np.int8(imag)

                    complex_no = real + imag * 1j

                    csi[i][perm[j]][k] = complex_no

                    index += 16

        self.parsed_csi = csi

    def parseIWLMVMCSIData(self, data: bytes, pos: int):
        # total_tones = self.numRx * self.numSTS * self.numTone
        csi_matrix = np.zeros((self.numTone, self.numRx, self.numSTS), dtype=complex)

        for j in range(self.numRx):
            for k in range(self.numSTS):
                for n in range(self.numTone):
                    real = struct.unpack("h", data[pos:pos + 2])
                    imag = struct.unpack("h", data[pos + 2:pos + 4])
                    pos += 4

                    csi_matrix[j, k, n] = complex(real, imag)

        self.parsed_csi = csi_matrix

    def parseUSRPCSIData(self, data: bytes, pos: int):
        csi_array_length = self.CSIBufferLength - 2 * self.numTone

        subcarrier_indices = np.zeros(self.numTone, dtype=np.int16)

        for i in range(self.numTone):
            subcarrier_indices[i] = struct.unpack("H", data[pos:pos + 2])[0]
            pos += 2

        self.subcarrierIndices = subcarrier_indices

        file_header = data[pos:pos + 2].decode("ascii")
        file_version = data[pos + 2:pos + 4].decode("ascii")

        # if file_header != "BB":
        #     print("Invalid CSI beamforming header.")
        # if file_version != "v1" and file_version != "v2":
        #     print("Unsupported CSI beamforming version.")

        matrix_version = struct.unpack("B", data[pos + 3:pos + 4])[0]
        matrix_version -= 48

        pos += 4

        dimensions = []
        # signalType seems to always be a double in this case?
        SIGNALTYPE_DOUBLE_SIZE = 16

        num_dimensions = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1
        for i in range(num_dimensions):
            if matrix_version == 1:
                v = struct.unpack("I", data[pos:pos + 4])[0]
                dimensions.append(v)
                pos += 4
            elif matrix_version == 2:
                v = struct.unpack("Q", data[pos:pos + 8])[0]
                dimensions.append(v)
                pos += 8

        complex_char = data[pos:pos + 1].decode("ascii")
        pos += 1
        # Hardcoded for now. Not seen a non-complex example.
        input_complexity_char = "C"
        if complex_char != input_complexity_char:
            print("Incompatible SignalMatrix complexity")

        type_char = struct.unpack("c", data[pos:pos + 1])[0]
        pos += 1
        # Need to check against SignalElementType

        num_type_bits = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1
        # Need to check against SignalElementType

        majority_char = data[pos:pos + 1].decode("ascii")
        pos += 1

        input_majority = CSISegment.SignalMatrixStorageMajority[majority_char]
        storage_majority = "ColumnMajority"

        numel = np.prod(dimensions)
        distance = csi_array_length - pos
        # if (distance != numel * SIGNALTYPE_DOUBLE_SIZE):
        #     print("Inconsistent SignalMatrix data buffer")

        signal_array = None

        if storage_majority == input_majority:
            buff = data[pos:pos + (numel * SIGNALTYPE_DOUBLE_SIZE)]
            signal_array = np.frombuffer(buff, dtype=np.cdouble)

        # else:

        signal_array = signal_array.reshape(tuple(dimensions))

        self.parsed_csi = signal_array

    def parseV1or2(self, data: bytes):
        self.deviceType = struct.unpack("H", data[:2])[0]
        pos = 2

        self.packetFormat = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.channelBandwidth = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.carrierFreq = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.samplingRate = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.subcarrierBandwidth = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.numTone = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.numSTS = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numRx = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numESS = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numCSI = 1

        self.antSelByte = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        if self.version == 2:
            self.subcarrierIndexOffset = struct.unpack("H", data[pos:pos + 2])[0]
            pos += 2
        else:
            self.subcarrierIndexOffset = 0

        self.CSIBufferLength = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        if self.deviceType == 0x1234:
            self.parseUSRPCSIData(data, pos)
        elif self.deviceType == 0x5300:
            self.parseIWL5300CSIData(data, pos)
        elif self.deviceType == 0x9300:
            self.parseQCA9300CSIData(data, pos)

    def parseV3(self, data: bytes):
        self.deviceType = struct.unpack("H", data[:2])[0]
        pos = 2

        self.packetFormat = struct.unpack("b", data[pos:pos + 1])[0]
        pos += 1

        self.channelBandwidth = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.carrierFreq = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.samplingRate = struct.unpack("Q", data[pos:pos + 8])[0]
        pos += 8

        self.subcarrierBandwidth = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        self.numTone = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.numSTS = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numRx = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numESS = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.numCSI = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.antSelByte = struct.unpack("B", data[pos:pos + 1])[0]
        pos += 1

        self.subcarrierIndexOffset = struct.unpack("H", data[pos:pos + 2])[0]
        pos += 2

        self.CSIBufferLength = struct.unpack("I", data[pos:pos + 4])[0]
        pos += 4

        if self.deviceType == 0x1234:
            self.parseUSRPCSIData(data, pos)
        elif self.deviceType == 0x2000:
            self.parseIWLMVMCSIData(data, pos)
        elif self.deviceType == 0x5300:
            self.parseIWL5300CSIData(data, pos)
        elif self.deviceType == 0x9300:
            self.parseQCA9300CSIData(data, pos)
