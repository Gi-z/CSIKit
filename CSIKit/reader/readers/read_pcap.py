import os
import struct
import time

import numpy as np

from CSIKit.csi import CSIData
from CSIKit.csi.frames import NEXCSIFrame
from CSIKit.reader import Reader

from CSIKit.util import byteops
from CSIKit.util.matlab import dbinv

start = time.time()

class PcapFrame:
    FRAME_HEADER_DTYPE = np.dtype([
        ("ts_sec", np.uint32), 
        ("ts_usec", np.uint32), 
        ("incl_len", np.uint32), 
        ("orig_len", np.uint32), 
    ])

    CHIPS = {
        "": "4339", #Cannot find an up to date version of this format.
        
        "6500": "43455c0", 
        
        "adde": "4358",

        "34e8": "4366c0", #Seen in data/nexmon/example_4366c0
        "6a00": "4366c0" #Seen on both the RT-AC86U and GT-AC5300
    }

    def __init__(self, data: bytes, offset: int):
        self.data = data
        self.offset = offset

        self.header = self.read_header()
        self.payload = self.read_payload()
            
    def read_header(self):
        header = np.frombuffer(self.data[self.offset:self.offset+self.FRAME_HEADER_DTYPE.itemsize], dtype=self.FRAME_HEADER_DTYPE)
        self.offset += self.FRAME_HEADER_DTYPE.itemsize
        return header
    
    @staticmethod
    def read_payloadHeader(payload: bytes) -> dict:
        payloadHeader = {}

        #Stupid question, why is the header 18 bytes?
        #The Hoffset is 16 everywhere else.

        payloadHeader["magic_bytes"] = payload[:2]
        payloadHeader["rssi"] = struct.unpack("b", payload[2:3])[0]
        payloadHeader["frame_control"] = struct.unpack("B", payload[3:4])[0]
        payloadHeader["source_mac"] = payload[4:10].hex()
        payloadHeader["sequence_no"] = payload[10:12]

        coreSpatialBytes = int.from_bytes(payload[12:14], byteorder="little")
        payloadHeader["core"] = [int(coreSpatialBytes&x != 0) for x in range(3)]
        payloadHeader["spatial_stream"] = [int(coreSpatialBytes&x != 0) for x in range(3, 6)]

        payloadHeader["channel_spec"] = payload[14:16]
       
        chipIdentifier = payload[16:18].hex()
        if chipIdentifier in PcapFrame.CHIPS:
            payloadHeader["chip"] = PcapFrame.CHIPS[chipIdentifier]
        else:
            payloadHeader["chip"] = "UNKNOWN"

        return payloadHeader
        
    def read_payload(self) -> np.array:
        incl_len = self.header["incl_len"][0]
        if incl_len <= 0:
            return False

        if (incl_len % 4) == 0:
            ints_size = int(incl_len / 4)
            payload = np.array(struct.unpack(ints_size*"I", self.data[self.offset:self.offset+incl_len]), dtype=np.uint32)
        else:
            ints_size = incl_len
            payload = np.array(struct.unpack(ints_size*"B", self.data[self.offset:self.offset+incl_len]), dtype=np.uint8)

        self.payloadHeader = PcapFrame.read_payloadHeader(self.data[self.offset+42:self.offset+62])
        self.offset += incl_len

        return payload

class Pcap:
    BW_80 = 80
    BW_40 = 40
    BW_20 = 20

    HOFFSET = 16

    NFFT_80 = int(BW_80*3.2)
    NFFT_40 = int(BW_40*3.2)
    NFFT_20 = int(BW_20*3.2)

    BW_SIZES = {
        #Adding an exception here for an additional file I found.
        #Need to figure out what's causing this 26 byte discrepancy.
        1050: 80,

        NFFT_80*4: 80,
        NFFT_40*4: 40,
        NFFT_20*4: 20
    }

    PCAP_HEADER_DTYPE = np.dtype([
        ("magic_number", np.uint32), 
        ("version_major", np.uint16), 
        ("version_minor", np.uint16), 
        ("thiszone", np.int32), 
        ("sigfigs", np.uint32), 
        ("snaplen", np.uint32), 
        ("network", np.uint32)
    ])

    def __init__(self, filename: str):
        self.data = open(filename, "rb").read()
        self.header = self.readHeader()
        self.frames = []
        self.skipped_frames = 0
        self.bandwidth = 0

        offset = self.PCAP_HEADER_DTYPE.itemsize
        while offset < len(self.data):
            nextFrame = PcapFrame(self.data, offset)
            offset = nextFrame.offset

            givenSize = nextFrame.header["orig_len"][0]-(self.HOFFSET-1)*4

            if givenSize not in self.BW_SIZES:
                # print("Skipped frame with incorrect size.")
                self.skipped_frames += 1
            else:
                bandwidth = self.BW_SIZES[givenSize]
                if self.bandwidth == 0:
                    self.bandwidth = bandwidth
                elif self.bandwidth != bandwidth:
                    # print("Change in observed bandwidth during capture.")
                    pass

                self.frames.append(nextFrame)

    def readHeader(self) -> np.array:
        return np.frombuffer(self.data[:self.PCAP_HEADER_DTYPE.itemsize], dtype=self.PCAP_HEADER_DTYPE)

class NEXBeamformReader(Reader):
    def __init__(self):
        pass

    @staticmethod
    def can_read(path: str) -> bool:
        if os.path.exists(path):
            _, extension = os.path.splitext(path)
            if extension == ".pcap":
                return True
            else:
                return False
        else:
            raise Exception("File not found: {}".format(path))
            
    @staticmethod
    def unpack_float(format: int, nfft: int, nfftx1: np.array) -> np.array:
        if format == 0:
            return byteops.unpack_float_acphy(10, 1, 0, 1, 9, 5, nfft, nfftx1)
        elif format == 1:
            return byteops.unpack_float_acphy(10, 1, 0, 1, 12, 6, nfft, nfftx1)

    def read_file(self, path: str, scaled: bool=False) -> CSIData:

        self.chip = " UNKNOWN"

        self.filename = os.path.basename(path)
        if not os.path.exists(path):
            raise Exception("File not found: {}".format(path))

        self.pcap = Pcap(path)

        ret_data = CSIData(self.filename)
        ret_data.bandwidth = self.pcap.bandwidth
        ret_data.skipped_frames = self.pcap.skipped_frames
        ret_data.expected_frames = len(self.pcap.frames)+self.pcap.skipped_frames

        data_frames = self.read_frames(self.pcap.frames, scaled, ret_data.bandwidth)
        for frame in data_frames:
            if frame is not None:
                ret_data.push_frame(frame)
                ret_data.timestamps.append(frame.timestamp)

        ret_data.set_chipset("Broadcom BCM{}".format(self.chip))

        return ret_data

    def read_bfee(self, pcap_frame: PcapFrame, scaled: bool, bandwidth: int) -> NEXCSIFrame:

        #ts_usec contains microseconds as an offset to the main seconds timestamp.
        usecs = pcap_frame.header["ts_usec"][0]/1e+6
        timestamp = pcap_frame.header["ts_sec"][0]+usecs

        data = pcap_frame.payload

        chipType = pcap_frame.payloadHeader["chip"]

        if chipType in ["4339", "43455c0"]:
            data.dtype = np.int16
            data = data[30:]
        elif chipType == "4358":
            data = data[15:15+int(bandwidth*3.2)]
            data = self.unpack_float(0, int(bandwidth*3.2), data)
        elif chipType == "4366c0":
            data = data[15:15+int(bandwidth*3.2)]
            data = self.unpack_float(1, int(bandwidth*3.2), data)
        else:
            # print("Invalid chip: " + chipType)
            # print("Current supported chipsets: 4339,43455c0,4358,4366c0")
            # exit(1)
            return None

        if chipType != "UNKNOWN":
            self.chip = chipType

        csiData = data.reshape(-1, 2)
        csi = csiData.astype(np.float32).view(np.complex64)
        
        if scaled:
            csi = NEXBeamformReader.scale_csi_frame(csi, pcap_frame.payloadHeader)

        #Manually adding timestamp to the payloadHeader.
        #TODO: Merge differently.
        pcap_frame.payloadHeader["timestamp"] = timestamp

        return NEXCSIFrame(pcap_frame.payloadHeader, csi)

    def read_frames(self, frames: list, scaled: bool, bandwidth: int) -> list:
        #Split the file into individual frames.
        #Send payloads to read_bfee so they can be extracted.
        return [self.read_bfee(x, scaled, bandwidth) for x in frames]

    @staticmethod
    def scale_csi_frame(csi: np.array, header: dict) -> np.array:
        #This is not a true SNR ratio as is the case for the Intel scaling.
        #We do not have agc or noise values so it's just about establishing a scale against RSSI.

        rssi = np.abs(header["rssi"])

        #Calculate the scale factor between normalized CSI and RSSI (mW).
        csi_sq = np.multiply(csi, np.conj(csi))
        csi_pwr = np.sum(csi_sq)
        csi_pwr = np.real(csi_pwr)
        csi_pwr_mean = np.mean(csi_pwr)
        
        rssi_pwr = dbinv(rssi)
        
        #Scale CSI -> Signal power : rssi_pwr / (mean of csi_pwr)
        scale = rssi_pwr / csi_pwr_mean

        return csi * np.sqrt(scale)