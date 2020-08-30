#!/usr/bin/env python3

import os
import time
import argparse
import logging
import json
import multiprocessing as mp
import numpy as np
import matplotlib.pyplot as plt
import h5py

import measurements_pb2 as measpb
from serverconnector import ServerConnector
from rpccalls import *

DEF_OUTDIR="./mcondata"
DEF_DFNAME="measurements.hdf5"
DEF_LOGFILE="/var/tmp/mcontroller.log"
LOGLEVEL = logging.DEBUG

def compute_psd(nfft, samples):
    """Return the power spectral density of `samples`"""
    window = np.hamming(nfft)
    result = np.multiply(window, samples)
    result = np.fft.fftshift(np.fft.fft(result, nfft))
    result = np.square(np.abs(result))
    result = np.nan_to_num(10.0 * np.log10(result))
    return result

def plot_stuff(title, *args):
    plt.suptitle("Client: %s" % title)
    plt.plot(*args)
    plt.show()

class MeasurementsController:
    POLLTIME = 10
    DEF_TOFF = 2
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
        self.connector = ServerConnector()

    def _setup_logger(self, logfile):
        fmat = logging.Formatter(fmt=self.LOGFMAT, datefmt=self.LOGDATEFMAT)
        shandler = logging.StreamHandler()
        shandler.setFormatter(fmat)
        fhandler = logging.FileHandler(logfile)
        fhandler.setFormatter(fmat)
        self.logger = mp.get_logger()
        self.logger.setLevel(LOGLEVEL)
        self.logger.addHandler(shandler)
        self.logger.addHandler(fhandler)

    def _setup_datadir(self, ddir):
        self.datadir = ddir
        if not os.path.exists(ddir):
            os.mkdir(ddir)
        
    def _set_start_time(self, toff = DEF_TOFF):
        self.start_time = np.ceil(time.time()) + toff

    def _clear_start_time(self):
        self.start_time = 0

    def _get_clients(self):
        # Get list of clients
        cmsg = measpb.SessionMsg()
        cmsg.type = measpb.SessionMsg.CALL
        add_attr(cmsg, "funcname", ServerConnector.CALL_GETCLIENTS)
        self.pipe.send(cmsg.SerializeToString())
        rmsg = measpb.SessionMsg()
        rmsg.ParseFromString(self.pipe.recv())
        return rmsg.clients

    def _rpc_call(self, cmd):
        self.logger.info("Running %s on: %s" % (cmd['cmd'], cmd['client_list']))
        cmsg = RPCCALLS[cmd['cmd']].encode(**cmd)
        cmsg.clients.extend(cmd['client_list'])
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
        clients = cmd['client_list']
        if not clients or clients[0] == "all":
            clients = self._get_clients()
        waittime = time.time() + cmd['timeout']
        self.last_results = []
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
        for res in self.last_results:
            if not res.samples: continue
            clientname = get_attr(res, 'clientname')
            rate = float(get_attr(res, 'rate'))
            vals = np.array([complex(c.r, c.j) for c in res.samples],
                            dtype=np.complex64)
            psd = compute_psd(len(vals), vals)
            freqs = np.fft.fftshift(np.fft.fftfreq(len(vals), 1/rate))
            plproc = mp.Process(target=plot_stuff,
                                args=(clientname, freqs, psd))
            plproc.start()
        
    def cmd_printres(self, cmd):
        doall = False
        if 'client_list' not in cmd or cmd['client_list'][0] == "all":
            doall = True
        for res in self.last_results:
            clientname = get_attr(res, 'clientname')
            if doall or clientname in cmd['client_list']:
                print(res)

    def cmd_measpaths(self, cmd):
        toff = cmd['toff'] if 'toff' in cmd else self.DEF_TOFF
        dfile = self._get_datafile()
        if not 'measure_paths' in dfile:
            dfile.create_group('measure_paths')
        subgrp = dfile['measure_paths'].create_group("%d" % int(time.time()))
        subgrp.attrs.update(cmd)
        clients = None
        if "client_list" in cmd:
            clients = cmd['client_list']
            del cmd['client_list']
        if not clients or clients[0] == "all":
            clients = self._get_clients()
        cmd['gain'] = cmd['txgain']
        txcmd = RPCCALLS['seq_transmit'].encode(**cmd)
        cmd['gain'] = cmd['rxgain']
        rxcmd = RPCCALLS['seq_measure'].encode(**cmd)
        del cmd['gain']
        del cmd['cmd']

        for txclient in clients:
            rxclients = [x for x in clients if x != txclient]
            stime = rxcmd.start_time = int(time.time())
            txcmd.ClearField("clients")
            txcmd.clients.append(txclient)
            rxcmd.ClearField("clients")
            rxcmd.clients.extend(rxclients)
            self.pipe.send(rxcmd.SerializeToString())
            self.cmd_waitres({'client_list': rxclients,
                              'timeout': cmd['timeout']})
            for res in self.last_results:
                rxclient = get_attr(res, 'clientname')
                arr = np.array(res.measurements)
                dsname = "%s-%d" % (rxclient, stime)
                ds = subgrp.create_dataset(dsname, (2,arr.size),
                                           dtype=np.float32)
                ds[0] = np.array(res.measurements)
                ds.attrs['tx'] = txclient
                ds.attrs['rx'] = rxclient
            rxcmd.start_time = txcmd.start_time = np.ceil(time.time()) + toff
            self.pipe.send(txcmd.SerializeToString())
            self.pipe.send(rxcmd.SerializeToString())
            self.cmd_waitres({'client_list': [txclient, *rxclients],
                              'timeout': cmd['timeout']})
            for res in self.last_results:
                if not res.measurements: continue
                print("Here!")
                arr = np.array(res.measurements)
                rxclient = get_attr(res, 'clientname')
                dsname = "%s-%d" % (rxclient, stime)
                dfile[dsname][1] = arr
                print(arr - np.array(dfile[dsname][0]))

    def run(self, cmdfile):
        (c1, c2) = mp.Pipe()
        self.pipe = c1
        self.netproc = mp.Process(target=self.connector.run,
                                  args=(c2, self.logger))
        self.netproc.start()

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
        self.netproc.join()

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
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    meas = MeasurementsController(args)
    meas.run(args.cmdfile)
