#!/usr/bin/env python3
#
# Common network implementation
#
import logging
import time
import socket
import selectors
import struct
import random
import multiprocessing as mp

import measurements_pb2 as measpb

class Networker:
    LISTEN_IP = '127.0.0.1'
    LISTEN_PORT = 5555
    BACKLOG = 10

    DISPATCH = {}
    
    def __init__(self, server = False):
        self.pipe = None
        self.server = server
        self.sel = selectors.DefaultSelector()

    def _setuplistener(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((Controller.LISTEN_IP, Controller.LISTEN_PORT))
        lsock.listen(Controller.BACKLOG)
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, self._accept)
        
    def _accept(self, sock, mask):
        (conn, addr) = sock.accept()
        self.logger.info("Accepted connection: %s:%s" % conn.getpeername())
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self._readsock)

    def _read(self, conn, mask):
        msg = self._get_msg_from_sock(conn)
        if msg:
            self.DISPATCH[msg.type](self, msg, conn)
        else:
            self.logger.warning("Connection to %s:%s closed unexpectedly." %
                                conn.getpeername())
            self.sel.unregister(conn)
            conn.close()

    def _readpipe(self, pipe, mask):
            msg = measpb.SessionMsg()
            msg.ParseFromString(pipe.recv())
            self.DISPATCH[msg.type](self, msg, conn)

    def _get_msg_from_sock(conn):
        smsg = None
        ldata = conn.recv(4)
        if ldata:
            mlen = struct.unpack(">L", ldata)[0]
            mbuf = conn.recv(mlen)
            smsg = measpb.SessionMsg()
            smsg.ParseFromString(mbuf)
        return smsg

    def send_msg(self, conn, msg):
        smsg = msg.SerializeToString()
        if isinstance(conn, mp.connection.Connection):
            conn.send(smsg)
        else:
            packed_len = struct.pack(">L", len(smsg))
            conn.sendall(packed_len + smsg)
         
    def run(self, pipe, logger):
        self.pipe = pipe
        self.sel.register(self.pipe, selectors.EVENT_READ, self._readpipe)
        self.logger = logger
        if self.server:
            self._setuplistener()

        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
