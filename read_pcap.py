from math import floor
from matlab import db, dbinv
from pathlib import Path

import pcapkit
import binascii
import scipy.io

import numpy as np
import os
import struct
import sys

import time
start = time.time()

class BeamformReader:

    def __init__(self, filename=""):
        self.filename = filename
        if os.path.exists(filename):
            self.csi_trace = self.read_bf_file(filename)
            self.scale_timestamps()

    def scale_timestamps(self):
        csi_trace = self.csi_trace
        sourceTimestamps = [x["timestamp"] for x in csi_trace]

        timediff = np.diff(sourceTimestamps)
        relativeTimestamps = list(np.cumsum(timediff))
        relativeTimestamps.insert(0, 0)
    
        for i, x in enumerate(csi_trace):
            x["timestamp"] = relativeTimestamps[i]

    def read_bfee(self, frame):

        n = 0

        timestamp = frame.info.time_epoch

        data = binascii.hexlify(frame.info.packet).decode("utf-8")

        #First we need to find the 0x11111111 to indicate the start.
        n = data.find("11111111")
        if n == -1:
            #Invalid frame found.
            print("Found invalid frame with no CSI data.")
            return None
        n += 8

        #Next is the 6 byte source MAC address.
        srcMac = data[n:n+12]
        #Optionally: tidy this up for viewing.
        srcMac = ":".join([srcMac[x:x+2] for x in range(0, len(srcMac), 2)]).upper()
        n += 12

        #Bitmask containing Core and Spatial stream numbers.
        coreSpatialByte = data[n:n+4]
        n += 4
        # print(coreSpatialByte)

        #Empty 2 bytes here for some reason.
        #These are future use bytes, but they
        #should be after the channel spec.

        n += 4

        #Channel specification, in (big??) endian.
        #Reading two bytes in backwards order.
        chanspec = data[n+2:n+4]+data[n:n+2]
        n += 4

        #More future use bytes???
        #2 here.
        n += 4

        csi = []
        csiData = np.frombuffer(binascii.unhexlify(data[n:]), dtype="int16")
        it = iter(csiData)
        for x in it:
            csi.append(np.complex(x, next(it)))

        csi = np.array(csi, dtype="complex")
        scipy.io.savemat("test.mat", {"csi": csi})

        return {
            "timestamp": timestamp,
            "source_mac": srcMac,
            "core_spatial": coreSpatialByte,
            "csi": csi,
        }

    def read_bf_file(self, filename):
        #Split the file into individual frames.
        #Send payloads to read_bfee so they can be extracted.
        extraction = pcapkit.extract(fin=str(filename), nofile=True)
        return [self.read_bfee(x) for x in extraction.frame]

if __name__ == "__main__":

    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        basePath = Path(__file__).parent
        path = (basePath / "../sample_data/out.pcap").resolve()

    reader = BeamformReader(path)
    print("Have CSI for {} packets.".format(len(reader.csi_trace)))
    end = time.time()
    print(end-start)