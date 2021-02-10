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

    CHIPS = {
        "": "4339",
        "6500": "43455c0",
        "adde": "4358",
        "": "4366c0"
    }

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
        if chipIdentifier in Frame.CHIPS:
            payloadHeader["chip"] = Frame.CHIPS[chipIdentifier]

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
    BW_80 = 80
    BW_40 = 40
    BW_20 = 20

    HOFFSET = 16

    NFFT_80 = int(BW_80*3.2)
    NFFT_40 = int(BW_40*3.2)
    NFFT_20 = int(BW_20*3.2)

    BW_SIZES = {
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

    def __init__(self, filename):
        self.data = open(filename, "rb").read()
        self.header = self.readHeader()
        self.frames = []
        self.skipped_frames = 0
        self.bandwidth = 0

        offset = self.PCAP_HEADER_DTYPE.itemsize
        while offset < len(self.data):
            nextFrame = Frame(self.data, offset)
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

    @staticmethod
    def unpack_float_acphy(nbits: int, autoscale: int, shft: int, fmt: int, nman: int, nexp: int, nfft: int, H: np.array) -> np.array:
        k_tof_unpack_sgn_mask = (1<<31)

        e_p, maxbit, e, i, e_zero, sgn = 0, 0, 0, 0, 0, 0
        n_out, e_shift = 0, 0

        He = [0] * nfft

        vi, vq, = 0, 0
        x, iq_mask, e_mask, sgnr_mask, sgni_mask = 0, 0, 0, 0, 0

        iq_mask = (1 << (nman - 1)) - 1
        e_mask = (1 << nexp) - 1
        e_p = (1 << (nexp - 1))
        sgnr_mask = (1 << (nexp + 2*nman - 1))
        sgni_mask = (sgnr_mask >> nman)
        e_zero = -nman

        out = np.zeros((nfft*2, 1), dtype=np.int32)
        n_out = (nfft << 1)
        e_shift = 1
        maxbit = -e_p

        for i in range(len(H)):
            vi = ((H[i] >> (nexp + nman)) & iq_mask)
            vq = ((H[i] >> nexp) & iq_mask)
            e = (H[i] & e_mask)
        
            if e >= e_p:
                e -= (e_p << 1)
            
            He[i] = e

            x = vi | vq
            
            if autoscale and x:
                m = 0xffff0000
                b = 0xffff
                s = 16

                while s > 0:
                    if x & m:
                        e += s
                        x >>= s
                    
                    s >>= 1
                    m = (m >> s) & b
                    b >>= s
            
                if e > maxbit:
                    maxbit = e
                
            if H[i] & sgnr_mask:
                vi |= k_tof_unpack_sgn_mask
            
            if H[i] & sgni_mask:
                vq |= k_tof_unpack_sgn_mask

            out[i<<1] = vi
            out[(i<<1)+1] = vq

        shft = nbits - maxbit
        for i in range(n_out):
            e = He[(i >> e_shift)] + shft
            vi = out[i]

            sgn = 1

            if vi & k_tof_unpack_sgn_mask:
                sgn = -1

                vi &= ~k_tof_unpack_sgn_mask
            
            if e < e_zero:
                vi = 0
            elif e < 0:
                e = -e
                vi = (vi >> e)
            else:
                vi = (vi << e)

            out[i] = sgn * vi

        return out
            

    @staticmethod
    def unpack_float(format: int, nfft: int, nfftx1: np.array):
        if format == 0:
            return NEXBeamformReader.unpack_float_acphy(10, 1, 0, 1, 9, 5, nfft, nfftx1)
        elif format == 1:
            return NEXBeamformReader.unpack_float_acphy(10, 1, 0, 1, 12, 6, nfft, nfftx1)

    def read_file(self, path, scaled=False):

        #TODO: Automatic chip detection.
        
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
            ret_data.push_frame(frame)
            ret_data.timestamps.append(frame.timestamp)

        ret_data.set_chipset("Broadcom BCM{}".format(self.chip))

        return ret_data

    def read_bfee(self, pcap_frame, scaled, bandwidth):

        #ts_usec contains microseconds as an offset to the main seconds timestamp.
        usecs = pcap_frame.header["ts_usec"][0]/1e+6
        timestamp = pcap_frame.header["ts_sec"][0]+usecs

        data = pcap_frame.payload

        self.chip = pcap_frame.payloadHeader["chip"]

        if self.chip in ["4339", "43455c0"]:
            data.dtype = np.int16
            data = data[30:]
        elif self.chip == "4358":
            data = data[15:15+int(bandwidth*3.2)]
            data = self.unpack_float(0, int(bandwidth*3.2), data)
        elif self.chip == "4366c0":
            data = data[15:15+int(bandwidth*3.2)]
            data = self.unpack_float(1, int(bandwidth*3.2), data)
        else:
            print("Invalid chip: " + self.chip)
            print("Current supported chipsets: 4339,43455c0,4358,4366c0")
            exit(1)

        csiData = data.reshape(-1, 2)

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

    def read_frames(self, frames, scaled, bandwidth):
        #Split the file into individual frames.
        #Send payloads to read_bfee so they can be extracted.
        return [self.read_bfee(x, scaled, bandwidth) for x in frames]

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