# import scipy.io

import os
import struct
import sys
import time

import numpy as np

start = time.time()

class Frame:
    FRAME_HEADER_DTYPE = np.dtype([
        ("ts_sec", np.uint32), 
        ("ts_usec", np.uint32), 
        ("incl_len", np.uint32), 
        ("orig_len", np.uint32), 
    ])

    def __init__(self, data, offset):
        self.data = data
        self.offset = offset

        self.header = self.read_header(data)
        self.payload = self.read_payload(data)
            
    def read_header(self, data):
        header = np.frombuffer(self.data[self.offset:self.offset+self.FRAME_HEADER_DTYPE.itemsize], dtype=self.FRAME_HEADER_DTYPE)
        self.offset += self.FRAME_HEADER_DTYPE.itemsize
        return header
    
    def read_payloadHeader(self, payload):
        payloadHeader = {}

        payloadHeader["magic_bytes"] = payload[:4]
        payloadHeader["source_mac"] = payload[4:10]
        payloadHeader["sequence_no"] = payload[10:12]

        coreSpatialBytes = int.from_bytes(payload[12:14], byteorder="little")
        payloadHeader["core"] = [int(coreSpatialBytes&x != 0) for x in range(3)]
        payloadHeader["spatial_stream"] = [int(coreSpatialBytes&x != 0) for x in range(3, 6)]

        payloadHeader["channel_spec"] = payload[14:16]
        payloadHeader["chip"] = payload[18:20]

        return payloadHeader
        
    def read_payload(self, data):
        incl_len = self.header["incl_len"][0]
        if incl_len <= 0:
            return False

        if (incl_len % 4) == 0:
            ints_size = int(incl_len / 4)
            payload = np.array(struct.unpack(ints_size*"I", data[self.offset:self.offset+incl_len]), dtype=np.uint32)
        else:
            ints_size = incl_len
            payload = np.array(struct.unpack(ints_size*"B", data[self.offset:self.offset+incl_len]), dtype=np.uint8)

        self.payloadHeader = self.read_payloadHeader(data[self.offset+42:self.offset+62])
        self.offset += incl_len

        return payload

class Pcap:
    BW = 80
    HOFFSET = 16
    NFFT = int(BW*3.2)

    #Need to update this so we can extract bandwidth from the first chanspec reading, maybe?

    PCAP_HEADER_DTYPE = np.dtype([
        ("magic_number", np.uint32), 
        ("version_major", np.uint16), 
        ("version_minor", np.uint16), 
        ("thiszone", np.int32), 
        ("sigfigs", np.uint32), 
        ("snaplen", np.uint32), 
        ("network", np.uint32)
    ])

    def __init__(self, filename):
        self.data = open(filename, "rb").read()
        self.header = self.readHeader()
        self.frames = []

        offset = self.PCAP_HEADER_DTYPE.itemsize
        while offset < len(self.data):
            nextFrame = Frame(self.data, offset)
            offset = nextFrame.offset

            if nextFrame.header["orig_len"][0]-(self.HOFFSET-1)*4 != self.NFFT*4:
                print("Skipped frame with incorrect size.")
            else:
                self.frames.append(nextFrame)

    def readHeader(self):
        return np.frombuffer(self.data[:self.PCAP_HEADER_DTYPE.itemsize], dtype=self.PCAP_HEADER_DTYPE)

class NEXBeamformReader:
    def __init__(self, filename="", chip="43455c0"):
        self.filename = filename
        self.chip = chip
        if os.path.exists(filename):
            self.pcap = Pcap(filename)
            self.csi_trace = self.read_frames(self.pcap.frames)

            self.csi_trace = self.scale_timestamps()
        else:
            print("Couldn't load file at {}.".format(filename))

    def scale_timestamps(self):
        csi_trace = self.csi_trace
        sourceTimestamps = [x["timestamp_low"] for x in csi_trace]
        sourceStamp = sourceTimestamps[0]
    
        for i, x in enumerate(csi_trace):
            x["timestamp"] = sourceTimestamps[i]-sourceStamp
        
        return csi_trace

    def read_bfee(self, frame):

        #ts_usec contains microseconds as an offset to the main seconds timestamp.
        usecs = frame.header["ts_usec"][0]/1e+6
        timestamp = frame.header["ts_sec"][0]+usecs

        data = frame.payload

        if self.chip in ["4339", "43455c0"]:
            data.dtype = np.int16
        # elif self.chip == "4358":
        # elif self.chip == "4366c0":
        else:
            print("Invalid chip: " + self.chip)
            print("Current supported chipsets: 4339,43455c0")
            exit(1)

        csi = np.zeros((256,), dtype=np.complex)
        sourceData = data[30:]
        csiData = sourceData.reshape(-1, 2)
        i = 0
        for x in csiData:
            csi[i] = np.complex(x[0], x[1])
            i += 1

        return {
            "timestamp_low": timestamp,
            "header": frame.payloadHeader,
            "csi": csi,
        }

    def read_frames(self, frames):
        #Split the file into individual frames.
        #Send payloads to read_bfee so they can be extracted.
        return [self.read_bfee(x) for x in frames]

if __name__ == "__main__":
    path = ".\\data\\pi\\walk_1597159475.pcap"

    reader = NEXBeamformReader(path, "43455c0")

    # Output for testing.
    # csi = np.zeros((len(reader.csi_trace), 256), dtype="complex")
    # for i, x in enumerate(reader.csi_trace):
    #     csi[i] = x["csi"]
    # scipy.io.savemat("test.mat", {"csi": csi})

    print("Have CSI for {} packets.".format(len(reader.csi_trace)))
    end = time.time()
    print(end-start)