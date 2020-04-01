import os
import socket
import struct

IWL_NL_BUFFER_SIZE = 4096

CN_NETLINK_USERS = 10
CN_IDX_IWLAGN = (CN_NETLINK_USERS + 0xf)

NETLINK_ADD_MEMBERSHIP = 1
SOL_NETLINK = 270

#Define NETLINK_CONNECTOR attribute for socket.
if getattr(socket, "NETLINK_CONNECTOR", None) is None:
    socket.NETLINK_CONNECTOR = 11

def open_socket():
    #Start socket.
    sock = socket.socket(socket.AF_NETLINK, socket.SOCK_DGRAM, socket.NETLINK_CONNECTOR)

    #Bind socket.
    sock.bind((os.getpid(), CN_IDX_IWLAGN))

    #270 is SOL_NETLINK and 1 is NETLINK_ADD_MEMBERSHIP
    sock.setsockopt(SOL_NETLINK, NETLINK_ADD_MEMBERSHIP, CN_IDX_IWLAGN)
    return sock

def close_socket(sock):
    sock.close()

def recv_from_socket(sock):
    data = sock.recv(IWL_NL_BUFFER_SIZE)

    #decode netlink header
    #msg_len, msg_type, flags, seq, pid = struct.unpack("=LHHLL", data[:16])

    #get payload
    payload = data[32:]
    return payload
