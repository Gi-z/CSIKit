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
    while True:
        try:
            payload = netlink.recv_from_socket(sock)

            bfRead = BeamformReader()
            csiEntry = bfRead.read_bf_entry(payload)

            graph.update(csiEntry)
        except KeyboardInterrupt:
            break

    netlink.close_socket(sock)
