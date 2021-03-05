import collections
import os
import struct
from math import floor

from CSIKit.csi import CSIData
from CSIKit.csi.frames import ATHCSIFrame
from CSIKit.reader import Reader
from CSIKit.util import byteops

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
    def can_read(path: str) -> bool: 
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
    def read_bfee(csi_buf: bytes, nr: int, nc: int, num_tones: int, scaled: bool=False) -> np.array:

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
                    imag = byteops.signbit_convert(imag, BITS_PER_SYMBOL)
                    imag += 1

                    bits_left -= BITS_PER_SYMBOL
                    current_data = current_data >> BITS_PER_SYMBOL

                    if ((bits_left - BITS_PER_SYMBOL) < 0):
                        current_data, idx, bits_left = ATHBeamformReader.get_next_bits(csi_buf, current_data, idx, bits_left)

                    real = current_data & bitmask
                    real = byteops.signbit_convert(real, BITS_PER_SYMBOL)
                    real += 1

                    bits_left -= BITS_PER_SYMBOL
                    current_data = current_data >> BITS_PER_SYMBOL

                    csi[k, nc_idx, nr_idx] = np.complex(real, imag)

        return csi

    def read_file(self, path: str, scaled: bool=False) -> CSIData:

        if scaled:
            print("Scaling not yet supported in Atheros format.")

        self.filename = os.path.basename(path)
        if not os.path.exists(path):
            raise Exception("File not found: {}".format(path))

        data = open(path, "rb").read()
        length = len(data)

        ret_data = CSIData(self.filename, "Atheros 802.11n-compatible")
        ret_data.bandwidth = 20

        cursor = 0
        expected_count = 0

        initial_timestamp = 0

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
                    
                    timestamp_low = header_block.timestamp*1e-6

                    if initial_timestamp == 0:
                        initial_timestamp = timestamp_low

                    ret_data.timestamps.append(timestamp_low - initial_timestamp)

                expected_count += 1
                cursor += header_block.csi_length

            if header_block.payload_length > 0:
                cursor += header_block.payload_length

            if (cursor + 420 > length):
                break

        return ret_data