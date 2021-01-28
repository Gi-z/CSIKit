import os
import struct
import time

import numpy as np

from CSIKit.csi import CSIData
from CSIKit.csi.frames import NEXCSIFrame
from CSIKit.reader import Reader

from CSIKit.util.matlab import dbinv

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

        self.header = self.read_header()
        self.payload = self.read_payload()
            
    def read_header(self):
        header = np.frombuffer(self.data[self.offset:self.offset+self.FRAME_HEADER_DTYPE.itemsize], dtype=self.FRAME_HEADER_DTYPE)
        self.offset += self.FRAME_HEADER_DTYPE.itemsize
        return header
    
    @staticmethod
    def read_payloadHeader(payload):
        payloadHeader = {}

        #TODO: Add handling for packets that don't include RSSI.

        payloadHeader["magic_bytes"] = payload[:2]
        payloadHeader["rssi"] = struct.unpack("b", payload[2:3])[0]
        payloadHeader["frame_control"] = struct.unpack("B", payload[3:4])[0]
        payloadHeader["source_mac"] = payload[4:10].hex()
        payloadHeader["sequence_no"] = payload[10:12]

        coreSpatialBytes = int.from_bytes(payload[12:14], byteorder="little")
        payloadHeader["core"] = [int(coreSpatialBytes&x != 0) for x in range(3)]
        payloadHeader["spatial_stream"] = [int(coreSpatialBytes&x != 0) for x in range(3, 6)]

        payloadHeader["channel_spec"] = payload[14:16]
        payloadHeader["chip"] = payload[18:20]

        return payloadHeader
        
    def read_payload(self):
        incl_len = self.header["incl_len"][0]
        if incl_len <= 0:
            return False

        if (incl_len % 4) == 0:
            ints_size = int(incl_len / 4)
            payload = np.array(struct.unpack(ints_size*"I", self.data[self.offset:self.offset+incl_len]), dtype=np.uint32)
        else:
            ints_size = incl_len
            payload = np.array(struct.unpack(ints_size*"B", self.data[self.offset:self.offset+incl_len]), dtype=np.uint8)

        self.payloadHeader = Frame.read_payloadHeader(self.data[self.offset+42:self.offset+62])
        self.offset += incl_len

        return payload

class Pcap:
    BW = 80
    # BW = 40
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
        self.skipped_frames = 0

        offset = self.PCAP_HEADER_DTYPE.itemsize
        while offset < len(self.data):
            nextFrame = Frame(self.data, offset)
            offset = nextFrame.offset

            if nextFrame.header["orig_len"][0]-(self.HOFFSET-1)*4 != self.NFFT*4:
                # print("Skipped frame with incorrect size.")
                self.skipped_frames += 1
            else:
                self.frames.append(nextFrame)

    def readHeader(self):
        return np.frombuffer(self.data[:self.PCAP_HEADER_DTYPE.itemsize], dtype=self.PCAP_HEADER_DTYPE)

class NEXBeamformReader(Reader):
    def __init__(self):
        pass

    @staticmethod
    def can_read(path):
        if os.path.exists(path):
            _, extension = os.path.splitext(path)
            if extension == ".pcap":
                return True
            else:
                return False
        else:
            raise Exception("File not found: {}".format(path))

    def read_file(self, path, scaled=False, chip="43455c0"):

        #TODO: Automatic chip detection.

        self.chip = chip
        
        self.filename = os.path.basename(path)
        if not os.path.exists(path):
            raise Exception("File not found: {}".format(path))

        self.pcap = Pcap(path)

        ret_data = CSIData(self.filename)
        ret_data.skipped_frames = self.pcap.skipped_frames
        ret_data.expected_frames = len(self.pcap.frames)+self.pcap.skipped_frames

        data_frames = self.read_frames(self.pcap.frames, scaled)
        for frame in data_frames:
            ret_data.push_frame(frame)
            ret_data.timestamps.append(frame.timestamp)

        return ret_data

    def read_bfee(self, pcap_frame, scaled):

        #ts_usec contains microseconds as an offset to the main seconds timestamp.
        usecs = pcap_frame.header["ts_usec"][0]/1e+6
        timestamp = pcap_frame.header["ts_sec"][0]+usecs

        data = pcap_frame.payload

        if self.chip in ["4339", "43455c0"]:
            data.dtype = np.int16
        # elif self.chip == "4358":
        # elif self.chip == "4366c0":
        else:
            print("Invalid chip: " + self.chip)
            print("Current supported chipsets: 4339,43455c0")
            exit(1)

        sourceData = data[30:]
        csiData = sourceData.reshape(-1, 2)

        csi = np.zeros((csiData.shape[0],), dtype=np.complex)

        i = 0
        for x in csiData:
            csi[i] = np.complex(x[0], x[1])
            i += 1

        if scaled:
            csi = NEXBeamformReader.scale_csi_frame(csi, pcap_frame.payloadHeader)

        #Manually adding timestamp to the payloadHeader.
        #TODO: Merge differently.

        pcap_frame.payloadHeader["timestamp"] = timestamp

        return NEXCSIFrame(pcap_frame.payloadHeader, csi)

    def read_frames(self, frames, scaled):
        #Split the file into individual frames.
        #Send payloads to read_bfee so they can be extracted.
        return [self.read_bfee(x, scaled) for x in frames]

    @staticmethod
    def scale_csi_frame(csi, header):
        #This is not a true SNR ratio as is the case for the Intel scaling.
        #We do not have agc or noise values so it's just about establishing a scale against RSSI.

        rssi = np.abs(header["rssi"])

        #Calculate the scale factor between normalized CSI and RSSI (mW).
        csi_sq = np.multiply(csi, np.conj(csi))
        csi_pwr = np.sum(csi_sq)
        csi_pwr = np.real(csi_pwr)
        
        rssi_pwr = dbinv(rssi)
        
        #Scale CSI -> Signal power : rssi_pwr / (mean of csi_pwr)
        scale = rssi_pwr / (csi_pwr / 256)

        return csi * np.sqrt(scale)