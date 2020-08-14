#!/usr/bin/env python3

import time
import struct
import socket
import logging
import selectors
import random
import multiprocessing as mp

import measurements_pb2 as measpb

DEF_IP = "127.0.0.1"
DEF_PORT = 5555


class ClientConnector:
    MAX_CONN_TRIES = 12 * 15  # Each try waits CONN_SLEEP seconds before next.
    CONN_SLEEP = 5
    
    def __init__(self, srvaddr, srvport):
        self.srvip = socket.gethostbyname(srvaddr)
        self.srvport = srvport
        self.logger = None
        self.pipe = None
        self.sock = None
        self.sid = 0
        self.sel = selectors.DefaultSelector()

    def __del__(self):
        if self.sock:
            msg = measpb.SessionMsg()
            msg.type = measpb.SessionMsg.CLOSE
            try:
                self._send_msg(self.sock, msg)
                self.sock.close()
            except:
                pass

    def _get_msg_from_sock(self, conn):
        smsg = None
        ldata = conn.recv(4)
        if ldata:
            mlen = struct.unpack(">L", ldata)[0]
            mbuf = conn.recv(mlen)
            smsg = measpb.SessionMsg()
            smsg.ParseFromString(mbuf)
        return smsg

    def _send_msg(self, conn, msg):
        smsg = msg.SerializeToString()
        if isinstance(conn, mp.connection.Connection):
            conn.send(smsg)
        else:
            packed_len = struct.pack(">L", len(smsg))
            conn.sendall(packed_len + smsg)

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
                if tries > self.MAX_CONN_TRIES:
                    self.logger.error("Too many connection attempts! Exiting.")
                    raise Exception("Too many connection attempts! Exiting.")
                time.sleep(self.CONN_SLEEP)

    def _readsock(self, conn, mask):
        msg = self._get_msg_from_sock(conn)
        if msg:
            self.DISPATCH[msg.type](self, msg, conn)
        else:
            self.logger.warning("Connection to %s:%s closed unexpectedly." %
                                conn.getpeername())
            self.sel.unregister(conn)
            self.send_init()

    def _readpipe(self, pipe, mask):
            msg = measpb.SessionMsg()
            msg.ParseFromString(pipe.recv())
            self.DISPATCH[msg.type](self, msg, pipe)

    def _get_attr(self, msg, key):
        for kv in msg.attributes:
            if kv.key == key: return kv.val
        return None

    def _add_attr(self, msg, key, val):
        attr = msg.attributes.add()
        attr.key = key
        attr.val = val

    def handle_init(self, msg, conn):
        self.sid = msg.sid
        self.logger.info("Connected with session id: %d" % self.sid)

    def handle_call(self, msg, conn):
        func = self._get_attr(msg, "funcname")
        if func in self.CALLS:
            # Handle calls meant for the connector (this class).
            self._send_msg(conn, self.CALLS[func](self, msg))
        else:
            # Send along calls destined for the client measurement code
            self._send_msg(self.pipe, msg)

    def handle_result(self, msg, conn):
        # Pass result back to server.
        self._add_attr(msg, "clientid", str(self.sid))
        self._add_attr(msg, "clientname", socket.gethostname())
        self._send_msg(self.sock, msg)

    def handle_hb(self, msg, conn):
        pass

    def handle_close(self, msg, conn):
        pass
    
    def send_init(self):
        self._connect()
        msg = measpb.SessionMsg()
        msg.type = measpb.SessionMsg.INIT
        msg.sid = self.sid
        self._send_msg(self.sock, msg)

    def run(self, pipe, logger):
        self.pipe = pipe
        self.sel.register(self.pipe, selectors.EVENT_READ, self._readpipe)
        self.logger = logger
        self.send_init()

        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    CALLS = {}
                
    DISPATCH = {
        measpb.SessionMsg.INIT: handle_init,
        measpb.SessionMsg.CALL: handle_call,
        measpb.SessionMsg.RESULT: handle_result,
        measpb.SessionMsg.HB: handle_hb,
        measpb.SessionMsg.CLOSE: handle_close,
    }
