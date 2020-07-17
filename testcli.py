#!/usr/bin/env python3

#
# Measurement collector test client
#

import time
import socket
import struct
import measurements_pb2 as measpb

CONN_IP = "127.0.0.1"
CONN_PORT = 5555

def send_msg(conn, msg):
    smsg = msg.SerializeToString()
    packed_len = struct.pack(">L", len(smsg))
    conn.sendall(packed_len + smsg)
    
def main():
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((CONN_IP, CONN_PORT))
    msg = measpb.SessionMsg()
    msg.type = measpb.SessionMsg.INIT
    send_msg(conn, msg)
    msg.type = measpb.SessionMsg.CLOSE
    send_msg(conn, msg)
    #time.sleep(1)
    conn.close()
    exit(0)

if __name__ == "__main__":
    main()
