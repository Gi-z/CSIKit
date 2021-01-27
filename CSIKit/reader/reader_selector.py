from .readers import *

READERS = [ATHBeamformReader, IWLBeamformReader, NEXBeamformReader]

def get_reader(path):
    for reader in READERS:
        if reader.can_read(path):
            return reader()

    #If no reader was selected, manual selection should be encouraged.
    print("Unable to automatically select a reader.")
    print("Defaulting to Intel format.")

    return IWLBeamformReader()