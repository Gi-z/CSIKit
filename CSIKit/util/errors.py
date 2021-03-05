import os

def print_length_error(length: int, data_length: int, i: int, filename: str):
    """
        Prints an error to highlight a difference between the frame's stated data size and the actual size.
        This usually stems from early file termination.

        Parameters:
            length {int} -- Stated length of the CSI data payload from the frame header.
            data_length {int} -- Actual length as derived from the payload.
    """

    print("Invalid length for CSI frame {} in {}.".format(i, os.path.basename(filename)))
    print("\tExpected {} bytes but got {} bytes.".format(length, data_length))
    if data_length < length:
        print("\tLast packet was likely cut off by an improper termination.")
        print("\tWhen killing log_to_file, use SIGTERM and ensure writes have been flushed, and files closed.")