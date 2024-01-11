import os

from CSIKit.csi import CSIData
from CSIKit.csi.frames import FeitCSIFrame
from CSIKit.reader import Reader
from CSIKit.util import csitools, constants
import numpy as np
import struct

RATE_MCS_MOD_TYPE_POS = 8
RATE_MCS_MOD_TYPE_MSK = (0x7 << RATE_MCS_MOD_TYPE_POS)
RATE_MCS_CCK_MSK = (0 << RATE_MCS_MOD_TYPE_POS)
RATE_MCS_LEGACY_OFDM_MSK = (1 << RATE_MCS_MOD_TYPE_POS)
RATE_MCS_HT_MSK = (2 << RATE_MCS_MOD_TYPE_POS)
RATE_MCS_VHT_MSK = (3 << RATE_MCS_MOD_TYPE_POS)
RATE_MCS_HE_MSK = (4 << RATE_MCS_MOD_TYPE_POS)
RATE_MCS_EHT_MSK = (5 << RATE_MCS_MOD_TYPE_POS)
RATE_MCS_CHAN_WIDTH_POS = 11
RATE_MCS_CHAN_WIDTH_MSK = (0x7 << RATE_MCS_CHAN_WIDTH_POS)
RATE_MCS_CHAN_WIDTH_20_VAL = 0
RATE_MCS_CHAN_WIDTH_20 = (RATE_MCS_CHAN_WIDTH_20_VAL << RATE_MCS_CHAN_WIDTH_POS)
RATE_MCS_CHAN_WIDTH_40_VAL = 1
RATE_MCS_CHAN_WIDTH_40 = (RATE_MCS_CHAN_WIDTH_40_VAL << RATE_MCS_CHAN_WIDTH_POS)
RATE_MCS_CHAN_WIDTH_80_VAL = 2
RATE_MCS_CHAN_WIDTH_80 = (RATE_MCS_CHAN_WIDTH_80_VAL << RATE_MCS_CHAN_WIDTH_POS)
RATE_MCS_CHAN_WIDTH_160_VAL = 3
RATE_MCS_CHAN_WIDTH_160 = (RATE_MCS_CHAN_WIDTH_160_VAL << RATE_MCS_CHAN_WIDTH_POS)
RATE_MCS_CHAN_WIDTH_320_VAL = 4
RATE_MCS_CHAN_WIDTH_320 = (RATE_MCS_CHAN_WIDTH_320_VAL << RATE_MCS_CHAN_WIDTH_POS)
RATE_HT_MCS_CODE_MSK = 7
RATE_MCS_ANT_A_POS = 14
RATE_MCS_ANT_A_MSK = (1 << RATE_MCS_ANT_A_POS)
RATE_MCS_ANT_B_POS = 15
RATE_MCS_ANT_B_MSK = (1 << RATE_MCS_ANT_B_POS)
RATE_MCS_LDPC_POS = 16
RATE_MCS_LDPC_MSK = (1 << RATE_MCS_LDPC_POS)
RATE_MCS_SS_POS = 16
RATE_MCS_SS_MSK = (1 << RATE_MCS_SS_POS)
RATE_MCS_BEAMF_POS = 16
RATE_MCS_BEAMF_MSK = (1 << RATE_MCS_BEAMF_POS)

MAX_TICK = 4294967295
TICK_RESOLUTION = 3.125

class FeitCSIBeamformReader(Reader):

    """
        This class handles parsing for CSI data from FeitCSI (AX200/AX210).
    """

    def __init__(self):
        pass

    @staticmethod
    def can_read(path: str) -> bool:
        file = open(path, "rb")
        fileContent = file.read()
        step = 0
        output = []
        while (len(fileContent) > step):
            csi_length = struct.unpack("I", fileContent[step:(step+272)][0:4])[0]
            step += 272
            step += csi_length

        if step == len(fileContent):
            return True

        return False

    def parseHeader(self, data):
        header = {}
        header["csi_length"] = struct.unpack("I", data[0:4])[0]
        header["ftm_clock"] = struct.unpack("I", data[8:12])[0]
        header["num_rx"] = data[46]
        header["num_tx"] = data[47]
        header["num_subcarriers"] = struct.unpack("I", data[52:56])[0]
        header["rssi_1"] = struct.unpack("I", data[60:64])[0]
        header["rssi_2"] = struct.unpack("I", data[64:68])[0]
        header["source_mac"] = struct.unpack("BBBBBB", data[68:74])
        header["source_mac_string"] = "%02x:%02x:%02x:%02x:%02x:%02x" % struct.unpack("BBBBBB", data[68:74])
        header["mu_clock"] = struct.unpack("I", data[88:92])[0]
        header["rate_flags"] = struct.unpack("I", data[92:96])[0]

        rate_format = header["rate_flags"] & RATE_MCS_MOD_TYPE_MSK
        if rate_format == RATE_MCS_CCK_MSK:
            rate_format = "CCK"
        elif rate_format == RATE_MCS_LEGACY_OFDM_MSK:
            rate_format = "LEGACY_OFDM"
        elif rate_format == RATE_MCS_VHT_MSK:
            rate_format = "VHT"
        elif rate_format == RATE_MCS_HT_MSK:
            rate_format = "HT"
        elif rate_format == RATE_MCS_HE_MSK:
            rate_format = "HE"
        elif rate_format == RATE_MCS_EHT_MSK:
            rate_format = "EHT"
        else:
            rate_format = "unknown"
        header["rate_format"] = rate_format

        channel_width = header["rate_flags"] & RATE_MCS_CHAN_WIDTH_MSK
        if channel_width == RATE_MCS_CHAN_WIDTH_20:
            channel_width = "20"
        elif channel_width == RATE_MCS_CHAN_WIDTH_40:
            channel_width = "40"
        elif channel_width == RATE_MCS_CHAN_WIDTH_80:
            channel_width = "80"
        elif channel_width == RATE_MCS_CHAN_WIDTH_160:
            channel_width = "160"
        elif channel_width == RATE_MCS_CHAN_WIDTH_320:
            channel_width = "320"
        else:
            channel_width = "unknown"
        header["channel_width"] = channel_width

        header["mcs"] = header["rate_flags"] & RATE_HT_MCS_CODE_MSK
        header["antenna_a"] = True if header["rate_flags"] & RATE_MCS_ANT_A_MSK else False
        header["antenna_b"] = True if header["rate_flags"] & RATE_MCS_ANT_B_MSK else False
        header["ldpc"] = True if header["rate_flags"] & RATE_MCS_LDPC_MSK else False
        header["ss"] = 2 if header["rate_flags"] & RATE_MCS_SS_MSK else 1
        header["beamforming"] = True if header["rate_flags"] & RATE_MCS_BEAMF_MSK else False

        return header

    def parseCsiData(self, data, header):
        csi_matrix = np.zeros((header["num_subcarriers"], header["num_rx"], header["num_tx"]), dtype=complex)
        pos = 0
        for j in range(header["num_rx"]):
            for k in range(header["num_tx"]):
                for n in range(header["num_subcarriers"]):
                    real = struct.unpack("h", data[pos:pos + 2])[0]
                    imag = struct.unpack("h", data[pos + 2:pos + 4])[0]
                    pos += 4
                    csi_matrix[n, j, k] = complex(real, imag)
        return csi_matrix

    def cubicInterpolate(self, y0, y1, y2, y3, mu):
        mu2 = mu * mu
        a0 = y3 - y2 - y0 + y1
        a1 = y0 - y1 - a0
        a2 = y2 - y0
        a3 = y1
        value = a0 * mu * mu2 + a1 * mu2 + a2 * mu + a3
        return value

    def linearInterpolate(self, y1, y2, mu):
        value = (y1 * (1 - mu) + y2 * mu)
        return value

    def interpolate(self, csi):
        indices = []
        if csi["header"]["rate_format"] in ("HT", "VHT") and csi["header"]["channel_width"] == "20":
            indices = [7, 21, 34, 48]
        elif csi["header"]["rate_format"] in ("HT", "VHT") and csi["header"]["channel_width"] == "40":
            indices = [5, 33, 47, 66, 80, 108]
        elif csi["header"]["rate_format"] == "VHT" and csi["header"]["channel_width"] == "80":
            indices = [19, 47, 83, 111, 130, 158, 194, 222]
        elif csi["header"]["rate_format"] == "VHT" and csi["header"]["channel_width"] == "160":
            indices = [19, 47, 83, 111, 130, 158, 194, 222, 261, 289, 325, 353, 372, 400, 436, 464]
        elif csi["header"]["rate_format"] == "HE" and csi["header"]["channel_width"] == "20":
            indices = [6, 32, 74, 100, 141, 167, 209, 235]
        elif csi["header"]["rate_format"] == "HE" and csi["header"]["channel_width"] == "40":
            indices = [6, 32, 74, 100, 140, 166, 208, 234, 249, 275, 317, 343, 383, 409, 451, 477]
        elif csi["header"]["rate_format"] == "HE" and csi["header"]["channel_width"] == "80":
            indices = [32, 100, 166, 234, 274, 342, 408, 476, 519, 587, 653, 721, 761, 829, 895, 963]
        elif csi["header"]["rate_format"] == "HE" and csi["header"]["channel_width"] == "160":
            indices = [32, 100, 166, 234, 274, 342, 408, 476, 519, 587, 653, 721, 761, 829, 895, 963, 1028, 1096, 1162, 1230, 1270, 1338, 1404, 1472, 1515, 1583, 1649, 1717, 1757, 1825, 1891, 1959]

        amplitude = abs(csi["csi_matrix"])
        phase = np.angle(csi["csi_matrix"])
        # phase = np.unwrap(phase)
        for i in indices:
            for j in range(csi["csi_matrix"].shape[1]):
                amplitude[i, j] = self.cubicInterpolate(amplitude[i - 2, j], amplitude[i - 1, j], \
                    amplitude[i + 1, j], amplitude[i + 2, j], 0.5)
                phase[i, j] = self.linearInterpolate(phase[i - 1, j], phase[i + 1, j], 0.5)
                if phase[i - 1, j] > 2 and phase[i + 1, j] < -2:
                    phase[i, j] = self.linearInterpolate(phase[i + 1, j], phase[i + 2, j], -1)
                csi["csi_matrix"][i, j] = amplitude[i, j] * np.exp(1j * phase[i, j])
        return csi


    def read_file(self, path: str, scaled: bool = False, remove_unusable_subcarriers: bool = True, filter_mac: str = None, interpolate: bool = True) -> CSIData:

        self.filename = os.path.basename(path)
        if not os.path.exists(path):
            raise Exception("File not found: {}".format(path))

        file = open(path, "rb")

        ret_data = CSIData(self.filename, "FeitCSI", "Intel AX2xx", filter_mac=filter_mac)

        fileContent = file.read()
        step = 0
        output = []
    
        while (len(fileContent) > step):
            data = {}
            data["header"] = self.parseHeader(fileContent[step:(step+272)])
            if not ret_data.bandwidth:
                ret_data.bandwidth = data["header"]["channel_width"]
            step += 272
            data["csi_matrix"] = self.parseCsiData(fileContent[step:(step + data["header"]["csi_length"])], data["header"])

            if interpolate:
                data = self.interpolate(data)
            
            if scaled:
                for j in range(data["header"]["num_rx"]):
                    data["csi_matrix"][:,j,:] = csitools.scale_csi_frame(data["csi_matrix"][:,j,:], data["header"]["rssi_1"])

            frame = FeitCSIFrame(data["header"], data["csi_matrix"])
            step += data["header"]["csi_length"]
            output.append(data)

            # timestamp calculation from ftm_clock (tick counter 3.125ns resolution) max ~13.4s then overflow
            timestamp = 0
            if len(ret_data.frames) > 0:
                if (data["header"]["mu_clock"] - ret_data.frames[-1].mu_clock)/1e6 < (MAX_TICK * TICK_RESOLUTION)/1e9:
                    if data["header"]["ftm_clock"] > ret_data.frames[-1].ftm_clock:
                        diff = data["header"]["ftm_clock"] - ret_data.frames[-1].ftm_clock
                    #overflow ftm_clock
                    else: 
                        diff = data["header"]["ftm_clock"] + (MAX_TICK - ret_data.frames[-1].ftm_clock)
                    timestamp = ret_data.timestamps[-1] + ((diff * TICK_RESOLUTION) / 1e9)
                # if size between mu_clock si larger than 13s we used mu_clock as reference time
                else: 
                    if data["header"]["mu_clock"] > ret_data.frames[-1].mu_clock:
                        diff = data["header"]["mu_clock"] - ret_data.frames[-1].mu_clock
                    #overflow mu_clock
                    else: 
                        diff = data["header"]["mu_clock"] + (MAX_TICK - ret_data.frames[-1].mu_clock)

                    timestamp = ret_data.timestamps[-1] + (diff / 1e6)

            ret_data.push_frame(frame, timestamp)

        return ret_data