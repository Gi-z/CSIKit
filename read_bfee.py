from math import floor
from matlab import db, dbinv

import csitools

import scipy.io

import numpy as np
import os
import struct
import sys

SIZE_STRUCT = struct.Struct(">H").unpack
CODE_STRUCT = struct.Struct("B").unpack
HEADER_STRUCT = struct.Struct("<LHHBBBBBbBBHH").unpack

VALID_BEAMFORMING_MEASUREMENT = 187

class BeamformReader:
    """
        This class handles parsing for CSI data from both batched files and realtime CSI packets from IWL5300 hardware.
        It is optimised for speed, with minor sanity checking throughout.

        The testing options allow for mat files to be generated, whose integrity can be verified with the matlab/intelcompare.m script.
    """

    def __init__(self, filename="", scaled=False):
        self.filename = filename
        self.scaled = scaled

        if filename == "":
            print("Realtime BeamformReader initialised.")
        elif os.path.exists(filename):
            with open(filename, "rb") as file:
                self.csi_trace = self.read_bf_file(file)
            csitools.scale_timestamps(self.csi_trace)
        else:
            print("Could not find file: {}".format(filename))

    def print_length_error(self, length, data_length, i):
        """
            Prints an error to highlight a difference between the frame's stated data size and the actual size.
            This usually stems from file termination.

            Args:
                length {int} -- Stated length of the CSI data payload from the frame header.
                data_length {int} -- Actual length as derived from the payload.
        """

        print("Invalid length for CSI frame {} in {}.".format(i, os.path.basename(self.filename)))
        print("\tExpected {} bytes but got {} bytes.".format(length, data_length))
        if data_length < length:
            print("\tLast packet was likely cut off by an improper termination.")
            print("\tWhen killing log_to_file, use SIGTERM and ensure writes have been flushed, and files closed.")

        return False

    def read_bfee(self, header, data, i=0):
        """
            This function parses a CSI payload using its preconstructed header and returns a complete frame object.

            Args:
                header {list} -- A list containing fields for a given CSI frame header.
                data {bytes} -- A bytes object containing the payload for CSI data.
                i {int} -- Index of the given frame.
        """

        timestamp_low = header[0]
        bfee_count = header[1]
        # reserved = header[2]
        n_rx = header[3]
        n_tx = header[4]
        rssi_a = header[5]
        rssi_b = header[6]
        rssi_c = header[7]
        noise = header[8]
        agc = header[9]
        antenna_sel = header[10]
        length = header[11]
        rate = header[12]

        #Flag invalid payloads so we don't error out trying to parse them into matrices.
        data_length = len(data)
        if length != data_length:
            return self.print_length_error(length, data_length, i)

        #If less than 3 Rx antennas are detected, default permutation should be used.
        #Otherwise invalid indices will likely be raised.
        perm = [0, 1, 2]
        if sum(perm) == n_rx:
            perm[0] = ((antenna_sel) & 0x3)
            perm[1] = ((antenna_sel >> 2) & 0x3)
            perm[2] = ((antenna_sel >> 4) & 0x3)

        csi = np.empty((30, n_rx, n_tx), dtype=np.complex)

        index = 0
        for i in range(30):
            index += 3
            remainder = index % 8
            for j in range(n_rx):
                for k in range(n_tx):
                    ind8 = floor(index/8)

                    if (ind8+2 >= len(data)):
                        break

                    real = (data[ind8] >> remainder) | (data[1+ind8] << (8-remainder))
                    imag = (data[1+ind8] >> remainder) | (data[2+ind8] << (8-remainder))

                    real = np.int8(real)
                    imag = np.int8(imag)

                    complex_no = real + imag * 1j

                    try:
                        csi[i][perm[j]][k] = complex_no
                    except IndexError as _:
                        #Minor backup in instances where severely invalid permutation parameters are generated.
                        csi[i][j][k] = complex_no

                    index += 16

        header = {
            "timestamp_low": timestamp_low,
            "bfee_count": bfee_count,
            "n_rx": n_rx,
            "n_tx": n_tx,
            "rssi_a": rssi_a,
            "rssi_b": rssi_b,
            "rssi_c": rssi_c,
            "noise": noise,
            "agc": agc,
            "antenna_sel": antenna_sel,
            "length": length,
            "rate": rate,
            "csi": csi,
            "perm": perm
        }

        if self.scaled:
            scaled_csi = csitools.scale_csi_entry(header)
            header["scaled_csi"] = scaled_csi

        return header

    def read_bf_entry(self, data):
        """
            This function parses a CSI payload not associated with a file (for example: those extracted via netlink).

            Args:
                data {bytes} -- The total bytes returned by the kernel for packet.
        """

        csi_header = struct.unpack("<LHHBBBBBbBBHH", data[4:25])
        all_data = [x[0] for x in struct.Struct(">B").iter_unpack(data[25:])]

        ret = self.read_bfee(csi_header, all_data)

        return ret

    def read_bf_file(self, file):
        """
            This function parses .dat files generated by log_to_file.

            Args:
                file {filereader} -- File reader object returned from open().
        """

        data = file.read()
        length = len(data)

        ret = []
        cur = 0
        count = 0

        while (length - cur) > 100:
            size = SIZE_STRUCT(data[cur:cur+2])[0]
            code = CODE_STRUCT(data[cur+2:cur+3])[0]
            
            cur += 3

            if code == VALID_BEAMFORMING_MEASUREMENT:
                all_block = data[cur:cur+size-1]

                header_block = HEADER_STRUCT(all_block[:20])
                data_block = all_block[20:]

                csi_data = self.read_bfee(header_block, data_block, count)
                if csi_data:
                    ret.append(csi_data)
            else:
                print("Invalid code for beamforming measurement at {}.".format(hex(cur)))

            count += 1
            cur += size-1

        return ret

if __name__ == "__main__":
    test = False

    if test:
        base_path = ".\\data\\intel\\activity"
        tests = ["brushteeth_1590158472.dat", "cook_1590161749.dat", "sleeping_post_1597163585.dat", "walk_1590161182.dat", "log.all_csi.6.7.6.dat"]

        for test in tests:
            path = "{}\\{}".format(base_path, test)
            reader = BeamformReader(path, scaled=True)
            scipy.io.savemat("tests\\{}.mat".format(test[:-4]), {"csi": reader.csi_trace})
    else:
        path = "./data/intel/activity/brushteeth_post_1597163619.dat"

        reader = BeamformReader(path)
        print("Have CSI for {} packets.".format(len(reader.csi_trace)))