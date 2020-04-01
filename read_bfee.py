from math import floor
from matlab import db, dbinv
from pathlib import Path

import scipy.io

import numpy as np
import os
import struct
import sys

import time
start = time.time()

DTYPE_CSI_HEADER_TLV = np.dtype([
    ("code", np.uint8),
    ("timestamp_low", np.uint32),
    ("bfee_count", np.uint16),
    ("reserved1", np.uint16),
    ("Nrx", np.uint8),
    ("Ntx", np.uint8),
    ("rssiA", np.uint8),
    ("rssiB", np.uint8),
    ("rssiC", np.uint8),
    ("noise", np.int8),
    ("agc", np.uint8),
    ("antenna_sel", np.uint8),
    ("len", np.uint16),
    ("fake_rate_n_flags", np.uint16),
]).newbyteorder('<')

class BeamformReader:

    def __init__(self, filename="", x_antenna=0, y_antenna=0):
        self.filename = filename
        self.x_antenna = x_antenna
        self.y_antenna = y_antenna

        if os.path.exists(filename):
            with open(filename, "rb") as file:
                self.csi_trace = self.read_bf_file(file)
                self.scale_timestamps(self.csi_trace)

    def scale_timestamps(self, csi_trace):
        time = [x["timestamp_low"] for x in csi_trace]

        timediff = (np.diff(time))*10e-6
        time_stamp = np.cumsum(timediff)

        csi_trace[0]["timestamp"] = 0
        for x in csi_trace[1:]:
            x["timestamp"] = time_stamp[csi_trace.index(x)-1]

    def read_bfee(self, header, csiData):
        code = header["code"][0]
        timestamp_low = header["timestamp_low"][0]
        bfee_count = header["bfee_count"][0]
        Nrx = header["Nrx"][0]
        Ntx = header["Ntx"][0]
        rssiA = header["rssiA"][0]
        rssiB = header["rssiB"][0]
        rssiC = header["rssiC"][0]
        noise = header["noise"][0]
        agc = header["agc"][0]
        antenna_sel = header["antenna_sel"][0]
        length = header["len"][0]
        rate = header["fake_rate_n_flags"][0]

        payload = csiData

        perm = [0, 1, 2]
        if sum(perm) == Nrx:
            perm[0] = ((antenna_sel) & 0x3)
            perm[1] = ((antenna_sel >> 2) & 0x3)
            perm[2] = ((antenna_sel >> 4) & 0x3)

        csi = np.empty((30, Nrx, Ntx), dtype=np.clongdouble)

        index = 0
        for i in range(30):
            index += 3
            remainder = index % 8
            for k in range(Nrx):
                for j in range(Ntx):
                    ind8 = floor(index/8)

                    tmp = (payload[ind8] >> remainder) | (payload[1+ind8] << (8-remainder))
                    tmp2 = (payload[1+ind8] >> remainder) | (payload[2+ind8] << (8-remainder))

                    tmp = np.int8(tmp)
                    tmp2 = np.int8(tmp2)

                    complexNo = tmp + tmp2 * 1j

                    csi[i][perm[k]][j] = complexNo
                    index += 16

        #Calculate the scale factor between normalized CSI and RSSI (mW).
        csi_sq = np.multiply(csi, np.conj(csi))
        csi_pwr = np.sum(csi_sq)
        csi_pwr = np.real(csi_pwr)

        rssi_pwr_db = self.get_total_rss(rssiA, rssiB, rssiC, agc)
        rssi_pwr = dbinv(rssi_pwr_db)
        #Scale CSI -> Signal power : rssi_pwr / (mean of csi_pwr)
        scale = rssi_pwr / (csi_pwr / 30)

        #Thermal noise may be undefined if the trace was captured in monitor mode.
        #If so, set it to 92.
        noise_db = noise
        if (noise == -127):
            noise_db = -92

        noise_db = np.float(noise_db)
        thermal_noise_pwr  = dbinv(noise_db)

        #Quantization error: the coefficients in the matrices are 8-bit signed numbers,
        #max 127/-128 to min 0/1. Given that Intel only uses a 6-bit ADC, I expect every
        #entry to be off by about +/- 1 (total across real and complex parts) per entry.

        #The total power is then 1^2 = 1 per entry, and there are Nrx*Ntx entries per
        #carrier. We only want one carrier's worth of error, since we only computed one
        #carrier's worth of signal above.
        quant_error_pwr = scale * (Nrx * Ntx)

        #Noise and error power.
        total_noise_pwr = thermal_noise_pwr + quant_error_pwr

        # ret now has units of sqrt(SNR) just like H in textbooks.
        ret = csi * np.sqrt(scale / total_noise_pwr)
        if Ntx == 2:
            ret = ret * np.sqrt(2)
        elif Ntx == 3:
            #Note: this should be sqrt(3)~ 4.77dB. But 4.5dB is how
            #Intel and other makers approximate a factor of 3.
            #You may need to change this if your card does the right thing.
            ret = ret * np.sqrt(dbinv(4.5))

        # ret = np.transpose(ret)

        return {
            "timestamp_low": timestamp_low,
            "bfee_count": bfee_count,
            "Nrx": Nrx,
            "Ntx": Ntx,
            "rssi_a": rssiA,
            "rssi_b": rssiB,
            "rssi_c": rssiC,
            "noise": noise,
            "agc": agc,
            "antenna_sel": antenna_sel,
            "length": length,
            "rate": rate,
            "csi": ret,
            "perm": perm
        }

    def read_bf_entry(self, data):
        csiHeader = np.frombuffer(data[4:25], dtype=DTYPE_CSI_HEADER_TLV)
        allData = [x[0] for x in struct.Struct(">B").iter_unpack(data[25:])]

        ret = self.read_bfee(csiHeader, allData)

        return ret

    def read_bf_file(self, file):
        data = file.read()
        length = len(data)

        ret = []
        cur = 0
        count = 0

        while cur < (length - 3):
            field_len = struct.unpack(">H", data[cur:cur+2])[0]
            cur += 2
            
            csiHeader = np.frombuffer(data[cur:cur+21], dtype=DTYPE_CSI_HEADER_TLV)
            allData = [x[0] for x in struct.Struct("B").iter_unpack(data[cur+21:cur+field_len])]
            cur += field_len

            ret.append(self.read_bfee(csiHeader, allData))
            count += 1

        return ret

    def get_total_rss(self, rssi_a, rssi_b, rssi_c, agc):
    # Calculates the Received Signal Strength (RSS) in dBm from
    # Careful here: rssis could be zero
        rssi_mag = 0
        if rssi_a != 0:
            rssi_mag = rssi_mag + dbinv(rssi_a)
        if rssi_b != 0:
            rssi_mag = rssi_mag + dbinv(rssi_b)
        if rssi_c != 0:
            rssi_mag = rssi_mag + dbinv(rssi_c)

        return db(rssi_mag) - 44 - agc

if __name__ == "__main__":

    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        # basePath = Path(__file__).parent
        # path = (basePath / "../../sample_data/out.pcap").resolve()
        path = r"E:\\DataLab PhD Albyn 2018\\Code\\sample_data\\10breathtest.dat"

    reader = BeamformReader(path)
    print("Have CSI for {} packets.".format(len(reader.csi_trace)))
    end = time.time()
    print(end-start)

    # scipy.io.savemat("inteltest.mat", {"csi": reader.csi_trace})