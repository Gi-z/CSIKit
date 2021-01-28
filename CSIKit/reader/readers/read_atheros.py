import collections
import os
import struct
from math import floor

from CSIKit.csi import CSIData
from CSIKit.csi.frames import ATHCSIFrame
from CSIKit.reader import Reader

import numpy as np

SIZE_STRUCT = struct.Struct(">H").unpack

HEADER_STRUCT_BE = struct.Struct(">QHHBBBBBBBBBBBH").unpack
HEADER_STRUCT_LE = struct.Struct(">QHHBBBBBBBBBBBH").unpack
HEADER_FORMAT = collections.namedtuple("frame_header", ["timestamp", "csi_length", "tx_channel", "err_info", "noise_floor", "rate", "bandwidth", "num_tones", "nr", "nc", "rssi", "rssi_1", "rssi_2", "rssi_3", "payload_length"])

BITS_PER_SYMBOL = 10
BITS_PER_COMPLEX_SYMBOL = 2 * BITS_PER_SYMBOL

class ATHBeamformReader(Reader):

    def __init__(self):
        pass

    @staticmethod
    def can_read(path):
        if os.path.exists(path):
            with open(path, "rb") as file:
                first_byte = file.read(1)
                if first_byte == b"\xff":
                    #Currently using the first byte.
                    #Big Endian format only supported (for auto selection) right now.
                    return True
                else:
                    return False
        else:
            raise Exception("File not found: {}".format(path))

    @staticmethod
    def signbit_convert(data, maxbit):
        if (data & (1 << (maxbit - 1))):
            data -= (1 << maxbit)

        return data

    @staticmethod
    def get_next_bits(buf, current_data, idx, bits_left):
        h_data = buf[idx]
        h_data += (buf[idx+1] << 8)

        current_data += h_data << bits_left

        idx += 2
        bits_left += 16

        return current_data, idx, bits_left

    @staticmethod
    def read_bfee(csi_buf, nr, nc, num_tones, scaled=False):

        csi = np.empty((num_tones, nc, nr), dtype=np.complex)

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
                    if ((bits_left - BITS_PER_SYMBOL) < 0):
                        current_data, idx, bits_left = ATHBeamformReader.get_next_bits(csi_buf, current_data, idx, bits_left)
                    
                    imag = current_data & bitmask
                    imag = ATHBeamformReader.signbit_convert(imag, BITS_PER_SYMBOL)
                    imag += 1

                    bits_left -= BITS_PER_SYMBOL
                    current_data = current_data >> BITS_PER_SYMBOL

                    if ((bits_left - BITS_PER_SYMBOL) < 0):
                        current_data, idx, bits_left = ATHBeamformReader.get_next_bits(csi_buf, current_data, idx, bits_left)

                    real = current_data & bitmask
                    real = ATHBeamformReader.signbit_convert(real, BITS_PER_SYMBOL)
                    real += 1

                    bits_left -= BITS_PER_SYMBOL
                    current_data = current_data >> BITS_PER_SYMBOL

                    csi[k, nc_idx, nr_idx] = np.complex(real, imag)

        return csi

    def read_file(self, path, scaled=False):
        """
            This function parses .dat files containing CSI frame data.

            Returns:
                total_csi (list): All valid CSI blocks, and their associated headers, contained within the given file.
        """

        if scaled:
            print("Scaling not yet supported in Atheros format.")

        self.filename = os.path.basename(path)
        if not os.path.exists(path):
            raise Exception("File not found: {}".format(path))

        data = open(path, "rb").read()
        length = len(data)

        ret_data = CSIData(self.filename)

        total_csi = []
        cursor = 0
        expected_count = 0

        first_byte = data[cursor:cursor+1]

        if first_byte == b'\xff':
            struct_type = HEADER_STRUCT_BE
            cursor += 1
        elif first_byte == b'\x00':
            struct_type = HEADER_STRUCT_LE
            cursor += 1
        else:
            #¯\_(ツ)_/¯
            print("File contains no endianness header. Assuming big.")
            struct_type = HEADER_STRUCT_BE

        while cursor < (length - 4):
            field_length = SIZE_STRUCT(data[cursor:cursor+2])[0]
            
            if (cursor + field_length) > length:
                break

            cursor += 2

            header_block = HEADER_FORMAT._make(struct_type(data[cursor:cursor+25]))
            cursor += 25

            if header_block.csi_length > 0:
                data_block = data[cursor:cursor+header_block.csi_length]

                csi_matrix = ATHBeamformReader.read_bfee(data_block, header_block.nr, header_block.nc, header_block.num_tones)
                if csi_matrix is not None:
                    frame = ATHCSIFrame(header_block, csi_matrix)
                    ret_data.push_frame(frame)
                    ret_data.timestamps.append(header_block.timestamp)

                expected_count += 1
                cursor += header_block.csi_length

            if header_block.payload_length > 0:
                cursor += header_block.payload_length

            if (cursor + 420 > length):
                break

        return ret_data