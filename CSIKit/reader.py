import os

from .read_atheros import ATHBeamformReader
from .read_bfee import IWLBeamformReader
from .read_pcap import NEXBeamformReader

def get_reader(path):
    #Need to identify which reader is needed.
    #For now, we'll cheat and use the file extension.
    _, extension = os.path.splitext(path)

    if extension == ".dat":
        #Could be either Atheros or Intel sample.
        #Using first byte to check.
        with open(path, "rb") as file:
            first_byte = file.read(1)
            if first_byte in [b"\xff"]:
                #Is Atheros sample (currently only taking Big Endian format).
                return ATHBeamformReader(path)
            else:
                #Is Intel sample.
                return IWLBeamformReader(path, scaled=True)
    elif extension == ".pcap":
        return NEXBeamformReader(path)
    else:
        print("Extension not supported: {}.".format(extension))
        print("Exiting.")
        exit(1)

def get_hardware(reader):
    if type(reader) == IWLBeamformReader:
        return "Intel IWL5300"
    elif type(reader) == NEXBeamformReader:
        return "Broadcom BCM{}".format(reader.chip.upper())
    elif type(reader) == ATHBeamformReader:
        return "Atheros (Unknown chipset)"