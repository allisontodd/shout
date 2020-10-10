#!/usr/bin/env python3
#
# Measurement server networking stuff
#

import logging
import time
import argparse
import socket
import selectors
import struct
import random
import select
import ipaddress
import multiprocessing as mp

import daemon
import measurements_pb2 as measpb

IPRANGES = ['127.0.0.0/8', '155.98.32.0/20']
DEF_LOGFILE="/var/tmp/measiface.log"
DEF_LOGLEVEL = logging.DEBUG
DEF_PORT = 5555

class Client:
    def __init__(self, host, port, sid, name, ctype, conn):
        self.host = host
        self.port = port
        self.sid = sid
        self.name = name
        self.type = ctype
        self.conn = conn
        self.last = time.time()

class Orchestrator:
    LISTEN_IP = '0.0.0.0'
    LISTEN_PORT = 5555
    BACKLOG = 10
    LOGFMAT = '%(asctime)s:%(levelname)s: %(message)s'
    LOGDATEFMAT = '%Y-%m-%d %H:%M:%S'

    CALL_GETCLIENTS = "getclients"

    def __init__(self, args):
        self.clients = {}
        self.callmap = {}
        self._setup_logger(args.logfile)
        self.sel = selectors.DefaultSelector()
        self.ipranges = []
        for ipr in IPRANGES:
            self.ipranges.append(ipaddress.IPv4Network(ipr))

    def _setup_logger(self, logfile = DEF_LOGFILE):
        fmat = logging.Formatter(fmt=self.LOGFMAT, datefmt=self.LOGDATEFMAT)
        shandler = logging.StreamHandler()
        shandler.setFormatter(fmat)
        fhandler = logging.FileHandler(logfile)
        fhandler.setFormatter(fmat)
        self.logger = mp.get_logger()
        self.logger.setLevel(DEF_LOGLEVEL)
        self.logger.addHandler(shandler)
        self.logger.addHandler(fhandler)

    def _setuplistener(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind((self.LISTEN_IP, self.LISTEN_PORT))
        lsock.listen(self.BACKLOG)
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, self._accept)
        self.logger.info("Orchestrator started and listening for connections.")

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

    def _get_msg_from_sock(self, conn):
        smsg = None
        try:
            ldata = conn.recv(4)
        except (ConnectionResetError,) as e:
            self.logger.error("Client connection reset unexpectedly: %s:%s" %
                              conn.getpeername())
            return None
        if ldata:
            mlen = struct.unpack(">L", ldata)[0]
            mbuf = bytearray()
            while len(mbuf) < mlen:
                rd, wt, xt = select.select([conn], [], [], 1)
                if not rd:
                    self.logger.warning("No data ready for read from socket.")
                try:
                    mbuf += conn.recv(mlen - len(mbuf))
                except (ConnectionResetError,) as e:
                    self.logger.error("Client connection reset unexpectedly: %s:%s" % conn.getpeername())
                    return None
            self.logger.debug("Received %d, indicated size %d." % (len(mbuf), mlen))
            smsg = measpb.SessionMsg()
            smsg.ParseFromString(mbuf)
        return smsg

    def _send_msg(self, conn, msg):
        smsg = msg.SerializeToString()
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
        self.clients[repr(peerinfo)] = Client(*peerinfo, sid, name, msg.peertype, conn)
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
            self.callmap[msg.uuid] = msg.sid
            if clients[0] == "all":
                self.logger.info("Sending '%s' call (UUID %s) to all measurement clients" % (func, msg.uuid))
                for cli in filter(lambda c: c.type == measpb.SessionMsg.MEAS_CLIENT, self.clients.values()):
                    self._send_msg(cli.conn, msg)
            else:
                self.logger.info("Sending '%s' call to clients (UUID %s): %s" % (func, msg.uuid, clients))
                for cname in clients:
                    cli = self._get_client_with_name(cname)
                    if not cli:
                        self.logger.error("Client %s is not connected!  Cannot send %s call to it." % (cname, func))
                    else:
                        self._send_msg(cli.conn, msg)
        else:
            self.logger.warning("Unhandled call '%s' from peer %s" % (func, msg.sid))

    def handle_result(self, msg, conn):
        # Pass results back to calling client.
        mcli = self.clients[repr(conn.getpeername())]
        if not msg.uuid in self.callmap:
            self.logger.warning("No call (UUID) mapping for %s! Dropping result." % msg.uuid)
        else:
            ifcli = self._get_client_with_sid(self.callmap[msg.uuid])
            #del self.callmap[msg.uuid]  FIX: Need to clean up callmap.
            if not ifcli:
                self.logger.warning("Destination client for call with uuid %s is not connected! Dropping result." % msg.uuid)
            else:
                self.logger.info("Passing along result from client %s to iface client %s" % (mcli.sid, ifcli.sid))
                self._send_msg(ifcli.conn, msg)

    def handle_hb(self, msg, conn):
        pass

    def handle_close(self, msg, conn):
        peerinfo = conn.getpeername()
        self.logger.info("CLOSE message from %s:%s" % peerinfo)
        self.sel.unregister(conn)
        conn.close()
        if repr(peerinfo) in self.clients:
            del(self.clients[repr(peerinfo)])

    def get_clients_call(self, msg):
        rmsg = measpb.SessionMsg()
        #rmsg.uuid = msg.uuid
        rmsg.type = measpb.SessionMsg.RESULT
        rmsg.peertype = measpb.SessionMsg.ORCH
        rmsg.clients.extend([cli.name for cli in filter(lambda c: c.type == measpb.SessionMsg.MEAS_CLIENT, self.clients.values())])
        return rmsg

    def run(self):
        self._setuplistener()

        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    CALLS = {
        CALL_GETCLIENTS: get_clients_call,
    }

    DISPATCH = {
        measpb.SessionMsg.INIT: handle_init,
        measpb.SessionMsg.CALL: handle_call,
        measpb.SessionMsg.RESULT: handle_result,
        measpb.SessionMsg.HB: handle_hb,
        measpb.SessionMsg.CLOSE: handle_close,
    }

def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--logfile", type=str, default=DEF_LOGFILE)
    parser.add_argument("-p", "--port", help="Orchestrator port", default=DEF_PORT, type=int)
    parser.add_argument("-d", "--daemon", help="Run as daemon", action="store_true")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.daemon:
        # Daemonize
        dcxt = daemon.DaemonContext(umask=0o022)
        dcxt.open()
    orch = Orchestrator(args)
    orch.run()
