#!/usr/bin/env python3

import time
import struct
import socket
import logging
import selectors
import random
import select
import multiprocessing as mp

import measurements_pb2 as measpb

DEF_IP = "127.0.0.1"
DEF_PORT = 5555

class InterfaceConnector:
    MAX_CONN_TRIES = 1  # Each try waits CONN_SLEEP seconds before next.
    CONN_SLEEP = 0

    CALL_QUIT = "quit"
    CALL_STATUS = "status"

    RES_READY = "ready"
    RES_NOTREADY = "notready"
    
    def __init__(self, srvaddr = DEF_IP, srvport = DEF_PORT):
        self.srvip = socket.gethostbyname(srvaddr)
        self.srvport = srvport
        self.name = socket.gethostname().split('.',1)[0]
        self.logger = None
        self.pipe = None
        self.sock = None
        self.sid = 0
        self.stopme = False
        self.sel = selectors.DefaultSelector()

    def __del__(self):
        if self.sock:
            msg = measpb.SessionMsg()
            msg.type = measpb.SessionMsg.CLOSE
            msg.peertype = measpb.SessionMsg.IFACE_CLIENT
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
            mbuf = bytearray()
            while len(mbuf) < mlen:
                rd, wt, xt = select.select([conn], [], [], 1)
                if not rd:
                    self.logger.warning("No data ready for read from socket.")
                mbuf += conn.recv(mlen - len(mbuf))
            self.logger.debug("Received %d, indicated size %d." % (len(mbuf), mlen))
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
                if tries >= self.MAX_CONN_TRIES:
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
        elif msg.peertype == measpb.SessionMsg.IFACE_CLIENT:
            # Send calls from actual iface client to orchestrator
            msg.sid = self.sid
            self._send_msg(self.sock, msg)
        else:
            # Pass along calls to measurement interface (not used yet).
            self._send_msg(self.pipe, msg)

    def handle_result(self, msg, conn):
        # Pass result up to interface client code.
        self._send_msg(self.pipe, msg)

    def handle_hb(self, msg, conn):
        pass

    def handle_close(self, msg, conn):
        pass
    
    def send_init(self):
        self._connect()
        msg = measpb.SessionMsg()
        msg.type = measpb.SessionMsg.INIT
        msg.peertype = measpb.SessionMsg.IFACE_CLIENT
        msg.sid = self.sid
        self._add_attr(msg, "clientname", self.name)
        self._send_msg(self.sock, msg)

    def run(self, pipe, logger):
        self.pipe = pipe
        self.sel.register(self.pipe, selectors.EVENT_READ, self._readpipe)
        self.logger = logger
        try:
            self.send_init()
        except:
            self.logger.error("Failed to connect to orchestrator!")
            self.pipe.close()
            exit(1)

        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
            if self.stopme:
                self.logger.info("Interface connector process exiting.")
                cmsg = measpb.SessionMsg()
                cmsg.sid = self.sid
                cmsg.type = measpb.SessionMsg.CLOSE
                cmsg.peertype = measpb.SessionMsg.IFACE_CLIENT
                self._send_msg(self.sock, cmsg)
                exit(0)

    def status_call(self, msg):
        rmsg = measpb.SessionMsg()
        rmsg.type = measpb.SessionMsg.RESULT
        rmsg.sid = self.sid
        if self.sid != 0:
            self._add_attr(rmsg, "result", self.RES_READY)
        else:
            self._add_attr(rmsg, "result", self.RES_NOTREADY)
        return rmsg

    def stop_connector_call(self, msg):
        self.stopme = True
        return msg
                
    CALLS = {
        CALL_QUIT: stop_connector_call,
        CALL_STATUS: status_call,
    }
                
    DISPATCH = {
        measpb.SessionMsg.INIT: handle_init,
        measpb.SessionMsg.CALL: handle_call,
        measpb.SessionMsg.RESULT: handle_result,
        measpb.SessionMsg.HB: handle_hb,
        measpb.SessionMsg.CLOSE: handle_close,
    }
