#!/usr/bin/env python3

import logging
import time
import multiprocessing as mp
import numpy as np
import matplotlib.pyplot as plt
import argparse
import json

import measurements_pb2 as measpb
from serverconnector import ServerConnector
from rpccalls import *

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
    LOGFILE="/var/tmp/mcontroller.log"
    DEF_TOFF = 2

    def __init__(self):
        self.clients = {}
        self.pipe = None
        self.conproc = None
        self.start_time = 0;
        self.last_results = []
        self._setup_logger()
        self.connector = ServerConnector()

    def _setup_logger(self):
        fmat = logging.Formatter(fmt='%(asctime)s:%(levelname)s: %(message)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
        shandler = logging.StreamHandler()
        shandler.setFormatter(fmat)
        fhandler = logging.FileHandler(self.LOGFILE)
        fhandler.setFormatter(fmat)
        self.logger = mp.get_logger()
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(shandler)
        self.logger.addHandler(fhandler)

    def _set_start_time(self, toff = DEF_TOFF):
        self.start_time = np.ceil(time.time()) + toff

    def _clear_start_time(self):
        self.start_time = 0

    def get_clients(self):
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

    def cmd_pause(self, cmd):
        self.logger.info("Pausing for %d seconds" % cmd['duration'])
        time.sleep(cmd['duration'])
        
    def cmd_waitres(self, cmd):
        clients = cmd['client_list']
        if not clients or clients[0] == "all":
            clients = self.get_clients()
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
        clients = cmd['client_list']
        if not clients or clients[0] == "all":
            clients = self.get_clients()
        for txclient in clients:
            rxclients = [x for x in foo if x != txclient]
            cmd['start_time'] = np.ceil(time.time()) + toff
            cmd['gain'] = cmd['txgain']
            txcmd = RPCCALLS['seq_transmit'].encode(**cmd)
            txcmd.clients.append(txclient)
            cmd['gain'] = cmd['rxgain']
            rxcmd = RPCCALLS['seq_measure'].encode(**cmd)
            rxcmd.clients.extend(rxclients)
            self.pipe.send(txcmd.SerializeToString())
            self.pipe.send(rxcmd.SerializeToString())
            self.cmd_waitres(cmd)
            self.cmd_printres({'client_list': rxclients})

    def run(self, args):
        (c1, c2) = mp.Pipe()
        self.pipe = c1
        self.netproc = mp.Process(target=self.connector.run,
                                  args=(c2, self.logger))
        self.netproc.start()

        # Read in and execute commands
        with open(args.cmdfile) as cfile:
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
    }


def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--cmdfile", type=str, required=True)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    meas = MeasurementsController()
    meas.run(args)
