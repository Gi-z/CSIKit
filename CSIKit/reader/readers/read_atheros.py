import collections
import os
import struct
from math import floor

from CSIKit.csi import CSIData
from CSIKit.csi.frames import ATHCSIFrame
from CSIKit.reader import Reader
from CSIKit.util import byteops, csitools

import numpy as np

SIZE_STRUCT = struct.Struct("<H").unpack

HEADER_STRUCT_BE = struct.Struct(">QHHBBBBBBBBBBBH").unpack
HEADER_STRUCT_LE = struct.Struct("<QHHBBBBBBBBBBBH").unpack
HEADER_FORMAT = collections.namedtuple("frame_header", ["timestamp", "csi_length", "tx_channel", "err_info", "noise_floor", "rate", "bandwidth", "num_tones", "nr", "nc", "rssi", "rssi_1", "rssi_2", "rssi_3", "payload_length"])

BITS_PER_SYMBOL = 10
BITS_PER_COMPLEX_SYMBOL = 2 * BITS_PER_SYMBOL

class ATHBeamformReader(Reader):

    def __init__(self):
        pass

    @staticmethod
    def can_read(path: str) -> bool: 
        if os.path.exists(path) and os.path.splitext(path)[1] == ".dat":
            data = open(path, "rb").read()
            if len(data) < 30:
                return False

            header_block = HEADER_FORMAT._make(HEADER_STRUCT_LE(data[2:27]))
            if header_block is None:
                return False

            tx_antenna_count = header_block.nc
            rx_antenna_count = header_block.nr

            # Looking for a quick heuristic for identifying if the first frame is valid.
            # Here we're interpreting the first frame's header as we regularly would.
            # https://wands.sg/research/wifi/AtherosCSI/document/Atheros-CSI-Tool-User-Guide.pdf
            # ^ This document says at most 3 tx and 3 rx antennas can be used.
            # So we want to check both antenna counts are between 1 and 3.
            tx_valid = tx_antenna_count >= 1 and tx_antenna_count <= 3
            rx_valid = rx_antenna_count >= 1 and rx_antenna_count <= 3

            return tx_valid and rx_valid

        return False

    @staticmethod
    def read_bfee(csi_buf: bytes, nr: int, nc: int, num_tones: int, scaled: bool=False) -> np.array:

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

        return csi

    def read_file(self, path: str, scaled: bool = False) -> CSIData:

        self.filename = os.path.basename(path)
        if not os.path.exists(path):
            raise Exception("File not found: {}".format(path))

        data = open(path, "rb").read()
        length = len(data)

        ret_data = CSIData(self.filename, "Atheros CSI Tool", "QCA93XX")

        cursor = 0
        expected_count = 0

        initial_timestamp = 0

        # first_byte = data[cursor:cursor+1]

        # if first_byte == b'\xff': # This is a holdout from a weird version of the format I found. Likely not used now.
        #     struct_type = HEADER_STRUCT_BE
        #     cursor += 1
        # else:
        #     #¯\_(ツ)_/¯
        #     #print("File contains no endianness header. Assuming little.")
        #     struct_type = HEADER_STRUCT_LE

        struct_type = HEADER_STRUCT_LE

        while cursor < (length - 4):
            field_length = SIZE_STRUCT(data[cursor:cursor+2])[0]
            
            if (cursor + field_length) > length:
                break

            cursor += 2

            header_block = HEADER_FORMAT._make(struct_type(data[cursor:cursor+25]))
            cursor += 25

            # Grabbing the bandwidth for the CSIData object using the boolean in the first Atheros frame.
            if ret_data.bandwidth == 0:
                ret_data.bandwidth = 20 if header_block.bandwidth == 0 else 40

            # if header_block.csi_length > 0:
            data_block = data[cursor:cursor+header_block.csi_length]
            if len(data_block) <= 0:
                continue

            try:
                csi_matrix = ATHBeamformReader.read_bfee(data_block, header_block.nr, header_block.nc, header_block.num_tones)
                if csi_matrix is not None:

                    # if scaled:
                    #     csi_matrix = csitools.scale_csi_frame(csi_matrix, rssi_dbm)

                    frame = ATHCSIFrame(header_block, csi_matrix)
                    ret_data.push_frame(frame)

                    timestamp_low = header_block.timestamp*1e-6

                    if initial_timestamp == 0:
                        initial_timestamp = timestamp_low

                    ret_data.timestamps.append(timestamp_low - initial_timestamp)
            except IndexError as e:
                print(e)

            expected_count += 1
            cursor += header_block.csi_length

            if header_block.payload_length > 0:
                cursor += header_block.payload_length

            if cursor + 420 > length:
                break

        return ret_data