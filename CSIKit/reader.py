import os

from .read_bfee import IWLBeamformReader
from .read_pcap import NEXBeamformReader

def get_reader(path):
    #Need to identify which reader is needed.
    #For now, we'll cheat and use the file extension.
    _, extension = os.path.splitext(path)

    if extension == ".dat":
        return IWLBeamformReader(path, scaled=True)
    elif extension == ".pcap":
        return NEXBeamformReader(path)
    else:
        print("Extension not supported: {}.".format(extension))
        print("Exiting.")
        exit(1)

def get_hardware(reader):
    if type(reader) == IWLBeamformReader:
        return "Intel IWL5300n"
    elif type(reader) == NEXBeamformReader:
        return "Broadcom BCM{}".format(reader.chip.upper())