from CSIKit.reader import ATHBeamformReader, CSVBeamformReader, IWLBeamformReader, NEXBeamformReader, PicoScenesBeamformReader
from CSIKit.reader import Reader

READERS = [ATHBeamformReader, CSVBeamformReader, IWLBeamformReader, NEXBeamformReader, PicoScenesBeamformReader]

def get_reader(path: str) -> Reader:
    for reader in READERS:
        if reader.can_read(path):
            return reader()

    #If no reader was selected, manual selection should be encouraged.
    print("Unable to automatically select a reader.")
    print("Defaulting to Intel format.")

    return IWLBeamformReader()