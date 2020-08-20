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
from rpccalls import RPCCALLS

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

    def __init__(self):
        self.clients = {}
        self.pipe = None
        self.conproc = None
        self.last_results = []
        self.setup_logger()
        self.connector = ServerConnector()

    def setup_logger(self):
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

    def _get_attr(self, msg, key):
        for kv in msg.attributes:
            if kv.key == key: return kv.val
        return None

    def _add_attr(self, msg, key, val):
        attr = msg.attributes.add()
        attr.key = key
        attr.val = val

    def get_clients(self):
        # Get list of clients
        cmsg = measpb.SessionMsg()
        cmsg.type = measpb.SessionMsg.CALL
        self._add_attr(cmsg, "funcname", ServerConnector.CALL_GETCLIENTS)
        self.pipe.send(cmsg.SerializeToString())
        rmsg = measpb.SessionMsg()
        rmsg.ParseFromString(self.pipe.recv())
        return rmsg.clients

    def rpc_call(self, cmd):
        self.logger.info("Running %s on: %s" % (cmd['cmd'], cmd['client_list']))
        cmsg = RPCCALLS[cmd['cmd']](**cmd)
        cmsg.clients.extend(cmd['client_list'])
        self.pipe.send(cmsg.SerializeToString)

    def cmd_pause(self, cmd):
        self.logger.info("Pausing for %d seconds" % cmd['duration'])
        time.sleep(cmd['duration'])
        
    def cmd_waitres(self, cmd):
        clients = cmd['client_list']
        waittime = time.time() + cmd['wait_time']
        self.last_results = []
        while time.time() < waittime and len(clients):
            if self.pipe.poll(self.POLLTIME):
                rmsg = measpb.SessionMsg()
                rmsg.ParseFromString(self.pipe.recv())
                clientid = self._get_attr(rmsg, "clientid")
                clientname = self._get_attr(rmsg, "clientname")
                self.logger.info("Received result from: %s", clientname)
                for i in range(len(clients)):
                    if clients[i] == clientname:
                        self.last_results.append(rmsg)
                        del clients[i]
                        break

    def cmd_plotpsd(self, cmd):
        for res in self.last_results:
            if self._get_attr(res, "funcname") != "recv_samples": continue
            clientname = self._get_attr(res, 'clientname')
            rate = float(self._get_attr(res, 'sample_rate'))
            vals = np.array([complex(c.r, c.j) for c in res.samples],
                            dtype=np.complex64)
            psd = compute_psd(len(vals), vals)
            freqs = np.fft.fftshift(np.fft.fftfreq(len(vals), 1/rate))
            plproc = mp.Process(target=plot_stuff,
                                args=(clientname, freqs, psd))
            plproc.start()

    def run(self, args):
        (c1, c2) = mp.Pipe()
        self.pipe = c1
        self.netproc = mp.Process(target=self.connector.run,
                                  args=(c2, self.logger))
        self.netproc.start()

        # Read in and execute commands
        with open(args.cmdfile) as cfile:
            commands = json.load(cfile)
            for command in commands:
                if command['cmd'] in CMD_DISPATCH:
                    self.CMD_DISPATCH[command['cmd']](self, command)
                else:
                    self.rpc_call(command)

        self.logger.info("Done with commands...")
        self.netproc.join()

    CMD_DISPATCH = {
        "pause":         cmd_pause,
        "wait_results":  cmd_waitres,
        "plot_psd":      cmd_plotpsd,
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
