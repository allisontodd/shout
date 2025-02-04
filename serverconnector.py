#!/usr/bin/env python3
#
# Measurement server networking stuff
#

import logging
import time
import socket
import selectors
import struct
import random
import select
import ipaddress
import multiprocessing as mp

import measurements_pb2 as measpb

IPRANGES = ['127.0.0.0/8', '155.98.32.0/20']

class Client:
    def __init__(self, host, port, sid, name, conn):
        self.host = host
        self.port = port
        self.sid = sid
        self.name = name
        self.conn = conn
        self.last = time.time()

class ServerConnector:
    LISTEN_IP = '0.0.0.0'
    LISTEN_PORT = 5555
    BACKLOG = 10

    CALL_GETCLIENTS = "getclients"

    def __init__(self):
        self.clients = {}
        self.pipe = None
        self.logger = None
        self.sel = selectors.DefaultSelector()
        self.ipranges = []
        for ipr in IPRANGES:
            self.ipranges.append(ipaddress.IPv4Network(ipr))

    def _setuplistener(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind((self.LISTEN_IP, self.LISTEN_PORT))
        lsock.listen(self.BACKLOG)
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, self._accept)

    def _accept(self, sock, mask):
        (conn, addr) = sock.accept()
        (ip, port) = conn.getpeername()
        ipobj = ipaddress.IPv4Address(ip)
        validip = False
        for iprange in self.ipranges:
            if ipobj in iprange:
                validip = True
                break
        if not validip:
            self.logger.info("Rejected connection from %s" % ip)
            conn.close()
            return
        self.logger.info("Accepted connection: %s:%s" % (ip, port))
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self._readsock)

    def _readsock(self, conn, mask):
        msg = self._get_msg_from_sock(conn)
        if msg:
            self.DISPATCH[msg.type](self, msg, conn)
        else:
            peerinfo = conn.getpeername()
            self.logger.warning("Connection to %s:%s closed unexpectedly." %
                                peerinfo)
            self.sel.unregister(conn)
            conn.close()
            if repr(peerinfo) in self.clients:
                del(self.clients[repr(peerinfo)])

    def _readpipe(self, pipe, mask):
            msg = measpb.SessionMsg()
            msg.ParseFromString(pipe.recv())
            self.DISPATCH[msg.type](self, msg, pipe)

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

    def _get_client_with_sid(self, sid):
        for cli in self.clients.values():
            if cli.sid == sid: return cli
        return None

    def _get_client_with_name(self, name):
        for cli in self.clients.values():
            if cli.name == name: return cli
        return None

    def _get_attr(self, msg, key):
        for kv in msg.attributes:
            if kv.key == key: return kv.val
        return None

    def handle_init(self, msg, conn):
        sid = msg.sid
        if not sid:
            sid = random.getrandbits(31)
        name = self._get_attr(msg, "clientname")
        peerinfo = conn.getpeername()
        self.logger.info("INIT message from %s:%s" % peerinfo)
        self.clients[repr(peerinfo)] = Client(*peerinfo, sid, name, conn)
        msg.sid = sid
        self._send_msg(conn, msg)

    def handle_call(self, msg, conn):
        func = self._get_attr(msg, "funcname")
        clients = msg.clients
        msg.ClearField("clients")
        if func in self.CALLS:
            # Handle calls meant for the connector (this class).
            self._send_msg(conn, self.CALLS[func](self, msg))
        elif clients:
            # Send along calls destined for measurement clients.
            if clients[0] == "all":
                self.logger.debug("Sending '%s' call to all clients" % func)
                for cli in self.clients.values():
                    self._send_msg(cli.conn, msg)
            else:
                self.logger.debug("Sending '%s' call to clients: %s" % (func, clients))
                for cname in clients:
                    cli = self._get_client_with_name(cname)
                    self._send_msg(cli.conn, msg)

    def handle_result(self, msg, conn):
        # Just pass up to measurements controller for now.
        cli = self.clients[repr(conn.getpeername())]
        self.logger.debug("Passing along result from client %s" % cli.sid)
        self._send_msg(self.pipe, msg)

    def handle_hb(self, msg, conn):
        pass

    def handle_close(self, msg, conn):
        peerinfo = conn.getpeername()
        self.logger.info("CLOSE message from %s:%s" % peerinfo)
        self.sel.unregister(conn)
        conn.close()
        if repr(peerinfo) in self.clients:
            del(self.clients[repr(peerinfo)])

    def get_clients(self, msg):
        rmsg = measpb.SessionMsg()
        #rmsg.uuid = msg.uuid
        rmsg.type = measpb.SessionMsg.RESULT
        rmsg.clients.extend([cli.name for cli in self.clients.values()])
        return rmsg

    def run(self, pipe, logger):
        self.pipe = pipe
        self.sel.register(self.pipe, selectors.EVENT_READ, self._readpipe)
        self.logger = logger
        self._setuplistener()

        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    CALLS = {
        CALL_GETCLIENTS: get_clients,
    }

    DISPATCH = {
        measpb.SessionMsg.INIT: handle_init,
        measpb.SessionMsg.CALL: handle_call,
        measpb.SessionMsg.RESULT: handle_result,
        measpb.SessionMsg.HB: handle_hb,
        measpb.SessionMsg.CLOSE: handle_close,
    }
