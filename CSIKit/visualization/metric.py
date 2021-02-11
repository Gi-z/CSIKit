
from cmath import phase
import numpy as np
import statistics
from typing import Dict, List, Tuple
from scipy.constants import c, pi

from CSIKit.csi import IWLCSIFrame as CsiEntry

"""
                     +--------------+
                     |              |
                     |    Metric    |
                     |              |
                     +------------+-+
                              ^
     +--------------------+   |   +---------------------+
+--->+ RSSI               +---+---+ TupleMetric         |
|    +--------------------+   |   +---------------------+
|                             |     ^
|    +--------------------+   |     |
|    | AGC                +---+     |   +----------------------+
|    +--------------------+   |     <---+Phase_Diff_Stability  |
|                             |     |   +----------------------+
|    +--------------------+   |     |
|    | Noise              +---+     |   +----------------------+
|    +--------------------+   |     +---+RSSI_PerAntenna       |
|    +--------------------+   |         +----------------------+
|    | Datarate           +---+
|    +--------------------+   |
|                             |
|    +--------------------+   |
+----+ SNR                +---+
     +--------------------+   |
     +--------------------+   |
     | Amplitude_Sum      +---+
     +--------------------+

"""


class Metric:
    def get_name(self):
        """
        Abstract Funktion to retrun the name 
        """
        raise Exception("not implemented function get_name")

    def get_unit(self):
        """
        Abstract Funktion to retrun the unit
        """
        raise Exception("not implemented function get_unit")
    def notice(self, entry:CsiEntry):
        """
        Abstract Funktion to notice a value by entry
        @entry : CsiEntry
        """
        raise Exception("not implemented function notice")
class TupleMetric:
    pass



class RSSI(Metric):
    def __init__(self):
        super().__init__()
    def notice(self, entry:CsiEntry):
        return self._get_total_rss(entry)
    def get_name(self):
        return "RSSI"
    def get_unit(self):
        return "dBm"
    @classmethod
    def _to_dBm(cls, rssi, agc):
        return rssi - 44 - agc
    @classmethod
    def _get_total_rss(cls, csiEntry: CsiEntry):
        # Calculates the Received Signal Strength (RSS) in dBm from
        # Careful here: rssis could be zero
        agc = csiEntry.agc
        rssi_a = csiEntry.rssi_a
        rssi_b = csiEntry.rssi_b
        rssi_c = csiEntry.rssi_c
        rssi_mag = 0
        if rssi_a != 0:
            rssi_mag = rssi_mag + np.power(10.0, rssi_a/10)

        if rssi_b != 0:
            rssi_mag = rssi_mag + np.power(10.0, rssi_b/10)

        if rssi_c != 0:
            rssi_mag = rssi_mag + np.power(10.0, rssi_c/10)

        ret = cls._to_dBm(10*np.log10(rssi_mag), agc)
        return ret

class AGC(Metric):
    def notice(self, entry:CsiEntry):
        return entry.agc
    def get_name(self):
        return "AGC"
    def get_unit(self):
        return "dB"

class Noise(Metric):
    def notice(self, entry:CsiEntry):
        return entry.noise
    def get_name(self):
        return "Noise"
    def get_unit(self):
        return "dBm"

class Datarate(Metric):
    def notice(self, entry:CsiEntry):
        return self.get_datarate(entry)
    def get_name(self):
        return "Datarate"
    def get_unit(self):
        return "MBit"
    @classmethod
    def get_datarate(cls, entry:CsiEntry):
        """ calcs and sets self.daterate coded from self.rate. 
            coding is spezified herehttps://github.com/dhalperi/linux-80211n-csitool/blob/csitool-3.13/drivers/net/wireless/iwlwifi/dvm/commands.h#L245-L334
        """
        if entry.rate is None:
            raise Exception("broken entry. rate is None")
        BANDWITHS_HT = {
            "index" : 3,
            0:6,
            1:12,
            2:18,
            3:24,
            4:36,
            5:48,
            6:54,
            7:60
        }
        BANDWITHS_OFDM= { 
            "index" : 4,
            0xD:6,
            0xF:9,
            0x5:12,
            0x7:18,
            0x9:24,
            0xB:36,
            0x1:48,
            0x3:54
        }
        BANDWITHs_CCK = {
            "index" : 6,
            10:1,
            20:2,
            55:5.5,
            110:11, 
        }
        
        rate = entry.rate
       
        if rate & (1 << (8 )):  # if 8. Bit is 1 -> HT
            #print("SET HT")
            BANDWITH = BANDWITHS_HT
        elif rate & (1 << (9)): # elif 9. Bit is 1 -> CCK
            print("SET CCK")
            BANDWITH = BANDWITHs_CCK # 
        else:                       # else OFDM
            print("SET OFDM")
            BANDWITH = BANDWITHS_OFDM


        mbit_index = rate % (2**BANDWITH["index"])# cut left side 
        if mbit_index in BANDWITH:
            return BANDWITH[mbit_index]
        else:
            raise Exception(f"self.rate is worng encoded. Index does not match:\n{BANDWITH}\nINDEX:{mbit_index}\nRATE:{rate} -----{bin(rate)}")

        # 13. BIT--> 0.4 usec (1) 0.8 usec(0) 
        #if rate & (1 << (13 - 1)): 


class SNR(RSSI,Metric):
    def notice(self, entry:CsiEntry):
        return self._get_total_rss(entry) - entry.noise
    def get_name(self):
        return "SNR"
    def get_unit(self):
        return "dB"

class Amplitude_Sum(Metric):
    def notice(self, entry: CsiEntry):
        return self.__calc_amplitude(entry)
    def get_name(self):
        return "Amplitude"
    def get_unit(self):
        return "dB"
    @classmethod
    def __calc_amplitude(cls, entry: CsiEntry):
        if entry.n_tx < 1:
            raise Exception("corrupted csi Entry. No Tx found")
        amplitude = 0
        # TODO what is when tx > 1
        for sub in entry.csi_matrix:
            for rx in range(entry.n_rx):
                amplitude += sum([abs(comp) for comp in sub[rx]])
        amplitude = amplitude /(30*entry.n_rx) # average amplitude per subcarrier per antenna
        return amplitude


class Phase_Diff_Stability(TupleMetric):

    def notice(self, entry):
        diffs = self._calc_phasediff(entry)
        std_errs =[statistics.stdev(diff) for diff in diffs]
        return tuple(std_errs)
        # std_errors = self._calc_std_err(diffs)
        # return std_errors
    def get_name(self):
        return "Phase std err"
    def get_unit(self):
        return "dB"
    @classmethod
    def _calc_phasediff(cls, entry: CsiEntry):
            """ Calculates the phasediffs A->B, B->C
            """
            if entry.n_rx !=3:
                raise Exception("csi entry has wrong count of nrx. Maybe you want to filter Nrx !=3")

            diffs = [[],[]] # diffs per antenna
            #TODO what happends if tx > 1
            for sub_carrier in entry.csi_matrix:

                for rx in range(entry.n_rx):
                    if rx is 0: # skip first antenna to not compare A->A
                        continue
                    last_phase = phase(sub_carrier[rx-1])
                    cur_phase = phase(sub_carrier[rx])
                    diff = last_phase-cur_phase
                    diffs[rx-1].append((diff+pi)%(pi/2))
                    #diffs[rx-1].append(((diff+pi)% (2*pi))-pi)
                    #modulo definition range of -pi -> pi
                    #diffs[rx-1].append(((diff+pi)% (2*pi))-pi)
            return(diffs)


    @classmethod
    def _calc_std_err(cls, phase_diffs: List):
        std_errs=[]
        for diff in phase_diffs:
            #average = statistics.mean(diff)
            std_err = statistics.stdev(diff)
            std_errs.append(std_err)

       
        return tuple(std_errs)



class RSSI_PerAntenna(RSSI,TupleMetric):

    def notice(self, entry: CsiEntry):
        agc = entry.agc
        return (
                self._to_dBm(entry.rssi_a, agc),
                self._to_dBm(entry.rssi_b, agc),
                self._to_dBm(entry.rssi_c, agc)) 
    def get_name(self):
        return "RSSI pro Antenne"
    def get_unit(self):
        return "dBm"
    

class Amplitude_per_Antenna(TupleMetric):
    def notice(self, entry: CsiEntry):
        if entry.n_tx < 1:
            raise Exception("corrupted csi Entry. No Tx found")

        results = []
        for rx in range(entry.n_rx):
            results.append(sum([abs(comp) for comp in entry.csi_matrix[0][rx]])/len(entry.csi_matrix[0][rx]))
        return(tuple(results))

    def get_name(self):
        return "Amplitude pro Antenne"
    def get_unit(self):
        return "dB"

class CSI_Matrix(Metric):
    def notice(self, entry:CsiEntry):
        return entry.csi_matrix
    def get_name(self):
        return "Amplitude"
    def get_unit(self):
        return "dBm"