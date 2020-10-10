#!/usr/bin/env python3

import os
import time
import argparse
import logging
import json
import multiprocessing as mp
import random

import numpy as np
import h5py

import measurements_pb2 as measpb
from ifaceconnector import InterfaceConnector
from rpccalls import *
from sigutils import *

DEF_IP = "127.0.0.1"
DEF_PORT = 5555
DEF_OUTDIR="./mcondata"
DEF_DFNAME="measurements.hdf5"
DEF_LOGFILE="/var/tmp/measiface.log"
DEF_LOGLEVEL = logging.DEBUG

class MeasurementsInterface:
    POLLTIME = 10
    DEF_TOFF = 2
    TX_TOFF = 0.5
    LOGFMAT = '%(asctime)s:%(levelname)s: %(message)s'
    LOGDATEFMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(self, args):
        self.clients = {}
        self.pipe = None
        self.conproc = None
        self.datadir = None
        self.dsfile = None
        self.start_time = 0
        self.last_results = []
        self.dfname = args.dfname
        self._setup_logger(args.logfile)
        self._setup_datadir(args.datadir)
        self.connector = InterfaceConnector(args.host, args.port)

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

    def _start_netproc(self):
        (c1, c2) = mp.Pipe()
        self.pipe = c1
        self.netproc = mp.Process(target=self.connector.run,
                                  args=(c2, self.logger))
        self.netproc.start()
        cmsg = measpb.SessionMsg()
        cmsg.type = measpb.SessionMsg.CALL
        add_attr(cmsg, "funcname", InterfaceConnector.CALL_STATUS)
        while True:
            self.pipe.send(cmsg.SerializeToString())
            rmsg = measpb.SessionMsg()
            rmsg.ParseFromString(self.pipe.recv())
            res = get_attr(rmsg, "result")
            if res == InterfaceConnector.RES_READY:
                break
            time.sleep(1)

    def _stop_netproc(self):
        cmsg = measpb.SessionMsg()
        cmsg.type = measpb.SessionMsg.CALL
        add_attr(cmsg, "funcname", InterfaceConnector.CALL_QUIT)
        self.pipe.send(cmsg.SerializeToString())
        self.netproc.join()
        
    def _setup_datadir(self, ddir):
        self.datadir = ddir
        if not os.path.exists(ddir):
            os.mkdir(ddir)
        
    def _set_start_time(self, toff = DEF_TOFF):
        self.start_time = np.ceil(time.time()) + toff

    def _clear_start_time(self):
        self.start_time = 0

    def _get_connected_clients(self):
        # Get list of clients from the Orchestrator
        cmsg = measpb.SessionMsg()
        cmsg.type = measpb.SessionMsg.CALL
        cmsg.peertype = measpb.SessionMsg.IFACE_CLIENT
        cmsg.uuid = random.getrandbits(31)
        add_attr(cmsg, "funcname", "getclients")
        self.pipe.send(cmsg.SerializeToString())
        rmsg = measpb.SessionMsg()
        rmsg.ParseFromString(self.pipe.recv())
        return rmsg.clients

    def _get_client_list(self, cmd):
        clients = None
        if 'client_list' in cmd:
            clients = list(cmd['client_list'])
        if not clients or clients[0] == "all":
            clients = self._get_connected_clients()
        return clients

    def _rpc_call(self, cmd):
        self.logger.info("Running %s on: %s" % (cmd['cmd'], cmd['client_list']))
        cmsg = RPCCALLS[cmd['cmd']].encode(**cmd)
        cmsg.clients.extend(cmd['client_list'])
        cmsg.peertype = measpb.SessionMsg.IFACE_CLIENT
        cmsg.uuid = random.getrandbits(31)
        self.pipe.send(cmsg.SerializeToString())

    def _get_datafile(self):
        if not self.dsfile:
            self.dsfile = h5py.File("%s/%s" %
                                    (self.datadir, self.dfname), "a")
        return self.dsfile

    def cmd_pause(self, cmd):
        self.logger.info("Pausing for %d seconds" % cmd['duration'])
        time.sleep(cmd['duration'])
        
    def cmd_waitres(self, cmd):
        clients = self._get_client_list(cmd)
        waittime = time.time() + cmd['timeout']
        self.last_results = []
        self.logger.info("Waiting for clients: %s" % clients)
        while time.time() < waittime and len(clients):
            if self.pipe.poll(self.POLLTIME):
                rmsg = measpb.SessionMsg()
                rmsg.ParseFromString(self.pipe.recv())
                clientname = get_attr(rmsg, "clientname")
                self.logger.info("Received result from: %s", clientname)
                for i in range(len(clients)):
                    if clients[i] == clientname:
                        self.last_results.append(rmsg)
                        del clients[i]
                        break

    def cmd_plotpsd(self, cmd):
        clients = self._get_client_list(cmd)
        for res in self.last_results:
            clientname = get_attr(res, 'clientname')
            if clientname in clients and res.samples:
                rate = float(get_attr(res, 'rate'))
                vals = np.array([complex(c.r, c.j) for c in res.samples],
                                dtype=np.complex64)
                psd = compute_psd(len(vals), vals)
                freqs = np.fft.fftshift(np.fft.fftfreq(len(vals), 1/rate))
                plproc = mp.Process(target=plot_stuff,
                                    args=(clientname, freqs, psd))
                plproc.start()
        
    def cmd_printres(self, cmd):
        clients = self._get_client_list(cmd)
        for res in self.last_results:
            clientname = get_attr(res, 'clientname')
            if clientname in clients:
                print(res)

    def cmd_measpaths(self, cmd):
        clients = self._get_client_list(cmd)
        if 'client_list' in cmd:
            del cmd['client_list']
        if not 'get_samples' in cmd:
            cmd['get_samples'] = False
        self.logger.info("Running path measurements over clients: %s" % clients)
        toff = cmd['toff'] if 'toff' in cmd else self.DEF_TOFF
        dfile = self._get_datafile()
        if not 'measure_paths' in dfile:
            dfile.create_group('measure_paths')
        measgrp = dfile['measure_paths'].create_group("%d" % int(time.time()))
        measgrp.attrs.update(cmd)
        cmd['gain'] = cmd['txgain']
        txcmd = RPCCALLS['seq_transmit'].encode(**cmd)
        txcmd.peertype = measpb.SessionMsg.IFACE_CLIENT
        cmd['gain'] = cmd['rxgain']
        rxcmd = RPCCALLS['seq_measure'].encode(**cmd)
        rxcmd.peertype = measpb.SessionMsg.IFACE_CLIENT
        del cmd['gain']
        del cmd['cmd']

        for txclient in clients:
            rxclients = [x for x in clients if x != txclient]
            txgrp = measgrp.create_group(txclient)
            stime = rxcmd.start_time = int(time.time())
            self.logger.info("Running with transmitter: %s" % txclient)
            txcmd.ClearField("clients")
            txcmd.clients.append(txclient)
            rxcmd.ClearField("clients")
            rxcmd.clients.extend(rxclients)
            rxcmd.uuid = random.getrandbits(31)
            self.pipe.send(rxcmd.SerializeToString())
            self.cmd_waitres({'client_list': rxclients,
                              'timeout': cmd['timeout']})
            for res in self.last_results:
                rxclient = get_attr(res, 'clientname')
                sgrp = txgrp.create_group(rxclient)
                if res.samples:
                    arr = np.array([complex(c.r, c.j) for c in res.samples],
                                   dtype=np.complex64)
                    ds = sgrp.create_dataset('samples', (2,arr.size),
                                             dtype=arr.dtype)
                    ds[0] = arr
                if res.measurements:
                    arr = np.array(res.measurements, dtype=np.float32)
                    ds = sgrp.create_dataset('avgpower', (2,arr.size),
                                             dtype=arr.dtype)
                    ds[0] = arr
            rxcmd.start_time = np.ceil(time.time()) + toff
            txcmd.start_time = rxcmd.start_time - self.TX_TOFF
            rxcmd.uuid = random.getrandbits(31)
            txcmd.uuid = random.getrandbits(31)
            self.pipe.send(txcmd.SerializeToString())
            self.pipe.send(rxcmd.SerializeToString())
            self.cmd_waitres({'client_list': rxclients + [txclient],
                              'timeout': cmd['timeout']})
            for res in self.last_results:
                rxclient = get_attr(res, 'clientname')
                if res.samples:
                    arr = np.array([complex(c.r, c.j) for c in res.samples],
                                   dtype=np.complex64)
                    ds = txgrp[rxclient]['samples'][1] = arr
                if res.measurements:
                    arr = np.array(res.measurements, dtype=np.float32)
                    ds = txgrp[rxclient]['avgpower'][1] = arr

    def run(self, cmdfile):
        self._start_netproc()

        # Read in and execute commands
        with open(cmdfile) as cfile:
            commands = json.load(cfile)
            for cmd in commands:
                if 'sync' in cmd and cmd['sync'] == True:
                    if 'toff' in cmd:
                        self._set_start_time(cmd['toff'])
                    elif not self.start_time:
                        self._set_start_time()
                    cmd['start_time'] = self.start_time
                else:
                    self._clear_start_time()

                if cmd['cmd'] in self.CMD_DISPATCH:
                    self.CMD_DISPATCH[cmd['cmd']](self, cmd)
                else:
                    self._rpc_call(cmd)

        self.logger.info("Done with commands...")
        self._stop_netproc()

    CMD_DISPATCH = {
        "pause":         cmd_pause,
        "wait_results":  cmd_waitres,
        "plot_psd":      cmd_plotpsd,
        "print_results": cmd_printres,
        "measure_paths": cmd_measpaths,
    }


def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cmdfile", type=str, required=True)
    parser.add_argument("-l", "--logfile", type=str, default=DEF_LOGFILE)
    parser.add_argument("-o", "--datadir", type=str, default=DEF_OUTDIR)
    parser.add_argument("-f", "--dfname", type=str, default=DEF_DFNAME)
    parser.add_argument("-s", "--host", help="Orchestrator host", default=DEF_IP, type=str)
    parser.add_argument("-p", "--port", help="Orchestrator port", default=DEF_PORT, type=int)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    meas = MeasurementsInterface(args)
    meas.run(args.cmdfile)
