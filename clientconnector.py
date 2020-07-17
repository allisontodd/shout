#!/usr/bin/env python3

import time
import struct
import socket
import logging
import selectors

import measurements_pb2 as measpb

DEF_IP = "127.0.0.1"
DEF_PORT = 5555

def get_msg_from_sock(conn):
    smsg = None
    ldata = conn.recv(4)
    if ldata:
        mlen = struct.unpack(">L", ldata)[0]
        mbuf = conn.recv(mlen)
        smsg = measpb.SessionMsg()
        smsg.ParseFromString(mbuf)
    return smsg

class Client:
    MAX_CONN_TRIES = 10
    
    def __init__(self, srvip, srvport, logger):
        self.logger = logger
        self.srvip = srvip
        self.srvport = srvport
        self.sock = None
        self.sid = 0
        self.sel = selectors.DefaultSelector()

    def __del__(self):
        if self.sock:
            msg = measpb.SessionMsg()
            msg.type = measpb.SessionMsg.CLOSE
            try:
                self.send_msg(msg)
                self.sock.close()
            except:
                pass

    def send_msg(self, msg):
        smsg = msg.SerializeToString()
        packed_len = struct.pack(">L", len(smsg))
        self.logger.debug("Sending type %d message." % msg.type)
        self.sock.sendall(packed_len + smsg)
        self.logger.debug("Message type %d sent." % msg.type)

    def _connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sel.register(self.sock, selectors.EVENT_READ, self._readsock)
        tries = 0
        while True:
            try:
                self.sock.connect((self.srvip, self.srvport))
                break
            except (ConnectionRefusedError,) as e:
                self.logger.warning("Failed to connect to %s:%s: %s" %
                                    (self.srvip, self.srvport, e))
                tries += 1
                if tries > Client.MAX_CONN_TRIES:
                    self.logger.error("Too many connection attempts! Exiting.")
                    raise Exception("Too many connection attempts! Exiting.")
                time.sleep(1)

    def _readsock(self, conn, mask):
        msg = get_msg_from_sock(conn)
        if msg:
            Client.DISPATCH[msg.type](self, msg, conn)
        else:
            self.logger.warning("Connection to %s:%s closed unexpectedly." %
                                conn.getpeername())
            self.sel.unregister(conn)
            self.do_init()
                
    def do_init(self):
        self._connect()
        msg = measpb.SessionMsg()
        msg.type = measpb.SessionMsg.INIT
        self.send_msg(msg)
        rmsg = get_msg_from_sock(self.sock)
        self.sid = rmsg.sid
        self.logger.info("Connected with session id: %d" % self.sid)

    def run(self):
        self.do_init()

        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

if __name__ == "__main__":
    fmat = logging.Formatter(fmt='%(asctime)s:%(name)s:%(levelname)s: %(message)s',
                             datefmt='%Y-%m-%d %H:%M:%S')
    shandler = logging.StreamHandler()
    shandler.setFormatter(fmat)
    logger = logging.getLogger("MeasClient")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(shandler)
    cli = Client(DEF_IP, DEF_PORT, logger)
    cli.run()
