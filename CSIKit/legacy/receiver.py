import sys
import time

import netlink
import numpy as np
import utils
from read_bfee import BeamformReader
from realtime_graph import RealtimeGraph

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
            print("error")

    netlink.close_socket(sock)
