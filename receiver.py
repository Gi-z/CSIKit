from read_bfee import BeamformReader
from realtime_graph import RealtimeGraph

import netlink
import numpy as np
import utils
import sys
import time

if __name__ == "__main__":

    rxChains = "ABC"
    #utils.configure_rx_chains(rxChains)

    gType = "default"
    if len(sys.argv) == 2:
        gType = sys.argv[1]

    graph = RealtimeGraph(gType)

    sock = netlink.open_socket()
    bfRead = BeamformReader()
    
    while True:
        try:
            payload = netlink.recv_from_socket(sock)
            csiEntry = bfRead.read_bf_entry(payload)

            graph.update(csiEntry)
        except OSError:
            #Every 256 or so readings, we get an OSError about a buffer being out of space.
            #Really struggled to find anything that might help with it.
            #Turns out it only throws one error, so we can just go back to taking readings.
            
            #We may also want to double up the previous reading, to make up for not doing
            #any resampling with the skipped reading.
            graph.update(csiEntry)

    netlink.close_socket(sock)
