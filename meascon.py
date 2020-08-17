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
        clients = []
        for kv in rmsg.attributes:
            if kv.key == "client":
                clients.append(kv.val)
        return clients

    def get_samples(self, nsamps, tfreq, gain, srate, clients = ["all"]):
        # Call "recv" on list of clients
        self.logger.info("Gathering samples.")
        msg = measpb.SessionMsg()
        msg.type = measpb.SessionMsg.CALL
        self._add_attr(msg, "funcname", "recv_samples")
        self._add_attr(msg, "nsamples", str(nsamps))
        self._add_attr(msg, "tune_freq", str(tfreq))
        self._add_attr(msg, "gain", str(gain))
        self._add_attr(msg, "sample_rate", str(srate))
        for client in clients:
            tmsg = measpb.SessionMsg()
            tmsg.CopyFrom(msg)
            self._add_attr(tmsg, "clientid", client)
            self.pipe.send(tmsg.SerializeToString())

    def xmit_sine(self, duration, tfreq, gain, srate, wfreq, wampl, clients = ["all"]):
        self.logger.info("Transmitting sine wave on client(s)")
        msg = measpb.SessionMsg()
        msg.type = measpb.SessionMsg.CALL
        self._add_attr(msg, "funcname", "xmit_sine")
        self._add_attr(msg, "duration", str(duration))
        self._add_attr(msg, "tune_freq", str(tfreq))
        self._add_attr(msg, "gain", str(gain))
        self._add_attr(msg, "sample_rate", str(srate))
        self._add_attr(msg, "wave_freq", str(wfreq))
        self._add_attr(msg, "wave_ampl", str(wampl))
        for client in clients:
            tmsg = measpb.SessionMsg()
            tmsg.CopyFrom(msg)
            self._add_attr(msg, "clientid", client)
            self.pipe.send(msg.SerializeToString())

    def cmd_pause(self, cmd):
        self.logger.info("Pausing for %d seconds" % cmd['pause_time'])
        time.sleep(cmd['pause_time'])

    def cmd_txsine(self, cmd):
        self.logger.info("Transmitting sine on: %s", cmd['client_list'])
        self.xmit_sine(cmd['duration'], cmd['freq'], cmd['gain'], cmd['rate'],
                       cmd['wfreq'], cmd['wampl'], clients = cmd['client_list'])

    def cmd_rxsamples(self, cmd):
        self.logger.info("Receiving samples from: %s", cmd['client_list'])
        self.get_samples(cmd['nsamps'], cmd['freq'], cmd['rxgain'], cmd['rate'],
                         clients = cmd['client_list'])

    def wait_results(self, cmd):
        clients = cmd['client_list']
        waittime = time.time() + cmd['wait_time']
        self.last_results = []
        while time.time() < waittime or len(clients):
            if self.pipe.poll(self.POLLTIME):
                rmsg = measpb.SessionMsg()
                rmsg.ParseFromString(self.pipe.recv())
                clientid = self._get_attr(rmsg, "clientid")
                clientname = self._get_attr(rmsg, "clientname")
                self.logger.info("Received result from: %s", clientname)
                if clientname in clients:
                    self.last_results.append(rmsg)
                    del clients[clientname]

    def plot_psd(self, cmd):
        for res in self.last_results:
            if self._get_attr(res, "funcname") != "recv_samples": continue
            clientname = self._get_attr(res, 'clientname')
            rate = int(self._get_attr(res, 'sample_rate'))
            arr = []
            for kv in res.attributes:
                if kv.key.startswith("s"):
                    idx = int(kv.key[1:])
                    arr.append(complex(kv.val))
            vals = np.array(arr, dtype=np.complex64)
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
                self.CMD_DISPATCH[command{'cmd'}](command)

        self.logger.info("Done with commands...")
        self.netproc.join()

    CMD_DISPATCH = {
        "pause":     MeasurementsController.cmd_pause,
        "txsine":    MeasurementsController.cmd_txsine,
        "rxsamples": MeasurementsController.cmd_rxsamples,
        "wait_results": MeasurementsController.cmd_waitres,
        "plot_psd:": MeasurementsController.cmd_plotpsd,
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
