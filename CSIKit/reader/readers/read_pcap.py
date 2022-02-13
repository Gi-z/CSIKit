import os
import struct
import time

import numpy as np

from CSIKit.csi import CSIData
from CSIKit.csi.frames import NEXCSIFrame
from CSIKit.reader import Reader

from CSIKit.util import byteops, constants
from CSIKit.util import csitools, stringops

start = time.time()

class PcapFrame:
    FRAME_HEADER_DTYPE = np.dtype([
        ("ts_sec", np.uint32), 
        ("ts_usec", np.uint32), 
        ("incl_len", np.uint32), 
        ("orig_len", np.uint32), 
    ])

    CHIPS = {
        "0100": "4339", #Cannot find an up to date version of this format.
        
        "6500": "43455c0",
        "dca6": "43455c0",

        "0300": "4358",
        "adde": "4358",

        "34e8": "4366c0", #Seen in data/nexmon/example_4366c0
        "6a00": "4366c0" #Seen on both the RT-AC86U and GT-AC5300
    }

    def __init__(self, data: bytes):
        self.data = data
        self.length = 0

        self.header = None
        self.payload = None
        self.payloadHeader = None

        self.header = self.read_header()
        self.payload = self.read_payload()
            
    def read_header(self):
        headerBytes = self.data.read(self.FRAME_HEADER_DTYPE.itemsize)
        if len(headerBytes) != self.FRAME_HEADER_DTYPE.itemsize:
            raise BufferError("Unable to read data for header")

        header = np.frombuffer(headerBytes, dtype=self.FRAME_HEADER_DTYPE)
        self.length += self.FRAME_HEADER_DTYPE.itemsize

        if header is None:
            raise BufferError("Unable to read data for header")

        return header
    
    @staticmethod
    def read_payloadHeader(payload: bytes) -> dict:
        payloadHeader = {}

        payloadHeader["magic_bytes"] = payload[:2]

        if payload[:4] == b'\x11\x11\x11\x11':
            # Device is running stock nexmon.
            payloadHeader["rssi"] = -1
            payloadHeader["frame_control"] = -1
        else:
            # Device is running mzakharo's PR.
            payloadHeader["rssi"] = struct.unpack("b", payload[2:3])[0]
            payloadHeader["frame_control"] = struct.unpack("B", payload[3:4])[0]

        payloadHeader["source_mac"] = stringops.hexToMACString(payload[4:10].hex())
        payloadHeader["sequence_no"] = int.from_bytes(payload[10:12], byteorder="little")

        coreSpatialBytes = payload[12:14]
        coreSpatialVal = int.from_bytes(coreSpatialBytes, byteorder="little")

        # First, we need to check whether the correct endianness is used here.
        # For some reason it seems to change. I guess Merlin on the RT-AC86U
        # uses big endianness or something?
        # We can check this by checking if the core/spatial bytes exceed the
        # max possible value: 0b111111 = 63
        if coreSpatialVal > 63:
            coreSpatialVal = int.from_bytes(coreSpatialBytes, byteorder="big")

        # Then we'll get the binary mask so we can inspect it ourselves.
        coreSpatialBits = bin(coreSpatialVal)[2:].zfill(6)

        # nexmon_csi defines the mask as follows:
        # "The next two bytes [bytes 12 and 13] contain core and spatial stream
        # number where the lowest three bits indicate the core and the next three
        # bits the spatial stream number,
        # e.g. 0x0019 (0b00011001) means core 0 and spatial stream 3."
        # While I'm not entirely sure whether they mean core 0 or 1 (since 0b001 == 3),
        # we can
        payloadHeader["core"] = int(coreSpatialBits[3:6], 2)
        payloadHeader["spatial_stream"] = int(coreSpatialBits[:3], 2)

        payloadHeader["channel_spec"] = payload[14:16].hex()
       
        chipIdentifier = payload[16:18].hex()
        if chipIdentifier in PcapFrame.CHIPS:
            payloadHeader["chip"] = PcapFrame.CHIPS[chipIdentifier]
        else:
            payloadHeader["chip"] = "UNKNOWN"

        return payloadHeader

    @staticmethod
    def read_payloadHeaderT3rO(payload: bytes) -> dict:
        payloadHeader = {}

        GAIN_RECOVERY_V2_COLUMN_NAME_EXT = ["_1", "_2", "_3", "_4", "_9", "_10"]

        payloadHeader["rssi"] = struct.unpack("b", payload[2:3])[0]

        # T3rO has none of this data but I don't feel like writing a new frame type.
        # Filling with garbage.
        payloadHeader["frame_control"] = -1
        payloadHeader["source_mac"] = ""
        payloadHeader["sequence_no"] = 0
        payloadHeader["core"] = 0
        payloadHeader["spatial_stream"] = 0
        payloadHeader["channel_spec"] = ""

        column_name_extensions = GAIN_RECOVERY_V2_COLUMN_NAME_EXT
        for i in range(0, 6):
            payloadHeader["elna" + column_name_extensions[i]] = struct.unpack("b", payload[18 + i:19 + i])[0]
            payloadHeader["lna1" + column_name_extensions[i]] = struct.unpack("b", payload[18 + i + 6:19 + i + 6])[0]
            payloadHeader["lna2" + column_name_extensions[i]] = struct.unpack(
                "b", payload[18 + i + 12:19 + i + 12])[0]
            payloadHeader["mix" + column_name_extensions[i]] = struct.unpack(
                "b", payload[18 + i + 18:19 + i + 18])[0]
            payloadHeader["lpf0" + column_name_extensions[i]] = struct.unpack(
                "b", payload[18 + i + 24:19 + i + 24])[0]
            payloadHeader["lpf1" + column_name_extensions[i]] = struct.unpack(
                "b", payload[18 + i + 30:19 + i + 30])[0]
            payloadHeader["dvga" + column_name_extensions[i]] = struct.unpack(
                "b", payload[18 + i + 36:19 + i + 36])[0]
            payloadHeader["trLoss" + column_name_extensions[i]] = struct.unpack(
                "b", payload[18 + i + 42:19 + i + 42])[0]

        payloadHeader["agcGain"] = struct.unpack("h", payload[66:68])[0]

        payloadHeader["chip"] = "43455c0"

        return payloadHeader
        
    def read_payload(self) -> np.array:
        if self.header is None or len(self.header["incl_len"]) == 0:
            return None

        incl_len = self.header["incl_len"][0]
        if incl_len <= 0:
            return False

        payload_bytes = self.data.read(incl_len)
        if payload_bytes is None:
            raise BufferError("Could not read payload")

        if (incl_len % 4) == 0:
            ints_size = int(incl_len / 4)
            payload = np.array(struct.unpack(ints_size*"I", payload_bytes), dtype=np.uint32)
        else:
            ints_size = incl_len
            payload = np.array(struct.unpack(ints_size*"B", payload_bytes), dtype=np.uint8)

        if len(payload) == 92:
            # Bad identifier for T3r0 rn.
            self.payloadHeader = PcapFrame.read_payloadHeaderT3rO(payload.tobytes()[42:])
        else:
            self.payloadHeader = PcapFrame.read_payloadHeader(payload.tobytes()[42:64])

        self.length += incl_len

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

        # T3rO 20Mhz
        308: 20,

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

    def stream(self):
        while True:
            try:
                next_frame = PcapFrame(self.data)
                if self.calculate_size(next_frame):
                    yield next_frame
            except BufferError:
                break

    def __init__(self, filename: str):
        self.data = open(filename, "rb")
        self.header = self.data.read(self.PCAP_HEADER_DTYPE.itemsize)
        self.frames = []
        self.skipped_frames = 0
        self.bandwidth = 0
        self.expected_size = None

    def read(self):
        while True:
            try:
                next_frame = PcapFrame(self.data)
                if self.calculate_size(next_frame):
                    self.frames.append(next_frame)
            except BufferError:
                break

    def calculate_size(self, frame):
        if frame is None or frame.header is None or frame.payload is None or frame.payloadHeader is None:
            # print("Incomplete pcap frame header found. Cannot parse any further frames.")
            # self.skipped_frames += 1
            return False

        given_size = frame.header["orig_len"][0]-(self.HOFFSET-1)*4

        # Checking if the frame size is valid for ANY bandwidth.
        if given_size not in self.BW_SIZES or frame.payload is None:
            #print("Skipped frame with incorrect size.")
            self.skipped_frames += 1
            return False

        # Establishing the bandwidth (and so, expected size) using the first frame.
        if self.expected_size is None:
            self.bandwidth = self.BW_SIZES[given_size]
            self.expected_size = given_size

        # Checking if the frame size matches the expected size for the established bandwidth.
        if self.expected_size != given_size:
            print("Change in bandwidth observed in adjacent CSI frames, skipping...")
            self.skipped_frames += 1
            return False

        return True

class NEXBeamformReader(Reader):

    BW_SUBS = {
        80: 256,
        40: 128,
        20: 64
    }

    HEADER_SLOTS = ["timestamp", "rssi", "frame_control", "source_mac", "sequence_no", "core", "spatial_stream", "channel_spec",
     "chip"]
    EMPTY_HEADER = {k: 0 for k in HEADER_SLOTS}

    def __init__(self, fill_skipped_frames: bool = True):
        super().__init__()
        self.fill_skipped_frames = fill_skipped_frames

    @staticmethod
    def can_read(path: str) -> bool:
        return os.path.exists(path) and os.path.splitext(path)[1] == ".pcap"
            
    @staticmethod
    def unpack_float(format: int, nfft: int, nfftx1: np.array) -> np.array:
        if format == 0:
            return byteops.unpack_float_acphy(10, 1, 0, 1, 9, 5, nfft, nfftx1)
        elif format == 1:
            return byteops.unpack_float_acphy(10, 1, 0, 1, 12, 6, nfft, nfftx1)

    def read_stream(self, path: str, scaled: bool = False):
        self.chip = " UNKNOWN"
        self.scaled = scaled

        self.filename = os.path.basename(path)
        if not os.path.exists(path):
            raise Exception("File not found: {}".format(path))
        
        self.pcap = Pcap(path)
        for f in self.pcap.stream():
            ret_data = CSIData()
            ret_data.bandwidth = self.pcap.bandwidth
            data = self.read_frame(f, ret_data.bandwidth)
            ret_data.push_frame(data, data.timestamp)
            ret_data.set_backend("Nexmon CSI")
            ret_data.set_chipset("Broadcom BCM{}".format(self.chip))
            yield ret_data

    def read_file(self, path: str, scaled: bool = False, filter_mac: str = None) -> CSIData:

        self.chip = " UNKNOWN"

        self.filename = os.path.basename(path)
        if not os.path.exists(path):
            raise Exception("File not found: {}".format(path))

        self.pcap = Pcap(path)
        self.pcap.read()
        self.scaled = scaled

        ret_data = CSIData(self.filename, backend="Nexmon CSI", filter_mac=filter_mac)
        ret_data.bandwidth = self.pcap.bandwidth
        ret_data.skipped_frames = self.pcap.skipped_frames
        ret_data.expected_frames = len(self.pcap.frames)+self.pcap.skipped_frames

        data_frames = self.read_frames(self.pcap.frames, ret_data.bandwidth)
        for frame in data_frames:
            if frame is not None:
                ret_data.push_frame(frame, frame.timestamp)

        # if self.fill_skipped_frames:
        #     empty_subcount = self.BW_SUBS[ret_data.bandwidth]
        #     empty_csi = np.zeros((empty_subcount, 1), dtype=np.complex64)
        #     empty_frame = NEXCSIFrame(self.EMPTY_HEADER, empty_csi)
        #     for _ in range(ret_data.skipped_frames):
        #         ret_data.push_frame(empty_frame)

        ret_data.set_chipset("Broadcom BCM{}".format(self.chip))

        return ret_data

    def read_bfee(self, pcap_frame: PcapFrame, bandwidth: int, remove_unusable_subcarriers: bool=True) -> NEXCSIFrame:
        if pcap_frame is None:
            return None

        #ts_usec contains microseconds as an offset to the main seconds timestamp.
        usecs = pcap_frame.header["ts_usec"][0]/1e+6
        timestamp = pcap_frame.header["ts_sec"][0]+usecs

        data = pcap_frame.payload

        chipType = pcap_frame.payloadHeader["chip"]

        if chipType in ["4339", "43455c0"]:
            data.dtype = np.int16
            # data = data[30:]

            # TODO: Not this way.
            if len(data) == 184:
                data = data[56:]
            else:
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

        # Manually adding timestamp to the payloadHeader.
        # TODO: Merge differently.
        pcap_frame.payloadHeader["timestamp"] = timestamp

        if chipType != "UNKNOWN":
            self.chip = chipType

        # data is now a 1d matrix of int32 values.
        # To convert this to complex doubles, we'll first reshape into pairs.
        # And then interpret the int32 matrix as float32, before viewing as complex64.
        # This removes several for loops.
        if len(data) % 2 != 0:
            return NEXCSIFrame(pcap_frame.payloadHeader, np.zeros((self.BW_SUBS[bandwidth], 1)))

        csiData = data.reshape(-1, 2)
        csi = csiData.astype(np.float32).view(np.complex64)

        if self.scaled:
            csi = csitools.scale_csi_frame(csi, pcap_frame.payloadHeader["rssi"])

        no_subcarriers = csi.shape[0]
        # TODO: Revert.
        remove_unusable_subcarriers = True
        if remove_unusable_subcarriers and (bandwidth == 20 or bandwidth is None):
            csi = csi[[x for x in range(no_subcarriers) if x not in constants.PI_20MHZ_UNUSABLE]]

        return NEXCSIFrame(pcap_frame.payloadHeader, csi)

    def read_bfee_batch(self, pcap_frames: list, bandwidth: int, rx_num: int = 1, tx_num: int = 1) -> NEXCSIFrame:

        # TODO: Revert.
        total_csi = np.zeros((tx_num, rx_num, 52), dtype=complex)
        # total_csi = np.zeros((tx_num, rx_num, self.BW_SUBS[bandwidth]), dtype=complex)

        frame_header = pcap_frames[0].header
        payload_header = pcap_frames[0].payloadHeader

        # ts_usec contains microseconds as an offset to the main seconds timestamp.
        usecs = frame_header["ts_usec"][0] / 1e+6
        timestamp = frame_header["ts_sec"][0] + usecs

        # Manually adding timestamp to the payloadHeader.
        # TODO: Merge differently.
        payload_header["timestamp"] = timestamp

        chipType = payload_header["chip"]
        if chipType != "UNKNOWN":
            self.chip = chipType

        for pcap_frame in pcap_frames:
            data = pcap_frame.payload

            if chipType in ["4339", "43455c0"]:
                data.dtype = np.int16
                data = data[30:]
            elif chipType == "4358":
                data = data[15:15 + int(bandwidth * 3.2)]
                data = self.unpack_float(0, int(bandwidth * 3.2), data)
            elif chipType == "4366c0":
                data = data[15:15 + int(bandwidth * 3.2)]
                data = self.unpack_float(1, int(bandwidth * 3.2), data)
            else:
                print("Invalid chip: " + chipType)
                print("Current supported chipsets: 4339,43455c0,4358,4366c0")
                exit(1)

            # data is now a 1d matrix of int32 values.
            # To convert this to complex doubles, we'll first reshape into pairs.
            # And then view the int32 matrix as float32, before viewing as complex64.
            # This removes several for loops.
            if len(data) % 2 != 0:
                print("Incomplete payload on frame")
                exit(1)

            csiData = data.reshape(-1, 2)
            csi = csiData.astype(np.float32).view(np.complex64)

            if self.scaled:
                csi = csitools.scale_csi_frame(csi, pcap_frame.payloadHeader["rssi"])

            no_subcarriers = csi.shape[0]
            # TODO: Revert.
            remove_unusable_subcarriers = True
            if remove_unusable_subcarriers and bandwidth == 20:
                csi = csi[[x for x in range(no_subcarriers) if x not in constants.PI_20MHZ_UNUSABLE]]

            core = pcap_frame.payloadHeader["core"]
            spatial_stream = pcap_frame.payloadHeader["spatial_stream"]

            total_csi[core][spatial_stream] = csi.flatten()

        return NEXCSIFrame(payload_header, np.transpose(total_csi))

    def read_frame(self, frame, bandwidth: int):
        return self.read_bfee(frame, bandwidth)

    def read_frames(self, frames: list, bandwidth: int) -> list:

        # Check if sequence_no changes. If not, 1Rx/Tx stream. (nvm)
        # If sequence no changes, it may still be a 1Rx/Tx stream.
        if max([x.payloadHeader["core"] for x in frames]) == 0:
            return [self.read_bfee(x, bandwidth) for x in frames]

        # Otherwise, read sequential spatial streams in batches.
        sequences = []
        current_sequence = []
        current_sequence_no = 0

        max_core = 0
        max_spatial_stream = 0

        for frame in frames:
            if frame.payloadHeader["sequence_no"] == current_sequence_no:
                if frame.payloadHeader["core"] > max_core:
                    max_core = frame.payloadHeader["core"]

                if frame.payloadHeader["spatial_stream"] > max_spatial_stream:
                    max_spatial_stream = frame.payloadHeader["spatial_stream"]

                current_sequence.append(frame)
            else:
                if len(current_sequence) > 0:
                    sequences.append(current_sequence)

                current_sequence = [frame]
                current_sequence_no = frame.payloadHeader["sequence_no"]

        max_core += 1
        max_spatial_stream += 1

        if len(current_sequence) > 0:
            sequences.append(current_sequence)

        return [self.read_bfee_batch(seq, bandwidth, tx_num=max_core, rx_num=max_spatial_stream) for seq in sequences]