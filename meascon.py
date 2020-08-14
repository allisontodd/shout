#!/usr/bin/env python3

import logging
import time
import multiprocessing as mp
import numpy as np
import matplotlib.pyplot as plt

import measurements_pb2 as measpb
from serverconnector import ServerConnector

LOGFILE="/var/tmp/mcontroller.log"

WAITTIME = 10
MAXWCOUNT = 6

def compute_psd(nfft, samples):
    """Return the power spectral density of `samples`"""
    window = np.hamming(nfft)
    result = np.multiply(window, samples)
    result = np.fft.fftshift(np.fft.fft(result, nfft))
    result = np.square(np.abs(result))
    result = np.nan_to_num(10.0 * np.log10(result))
    return result

def plot_stuff(*args):
    plt.plot(*args)
    plt.show()

class MeasurementsController:

    def __init__(self):
        self.clients = {}
        self.pipe = None
        self.conproc = None
        self.setup_logger()
        self.connector = ServerConnector()

    def setup_logger(self):
        fmat = logging.Formatter(fmt='%(asctime)s:%(levelname)s: %(message)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
        shandler = logging.StreamHandler()
        shandler.setFormatter(fmat)
        fhandler = logging.FileHandler(LOGFILE)
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
            self._add_attr(msg, "clientid", client)
            self.pipe.send(msg.SerializeToString())

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
            
    def run(self, args):
        (c1, c2) = mp.Pipe()
        self.pipe = c1
        self.netproc = mp.Process(target=self.connector.run,
                                  args=(c2, self.logger))
        self.netproc.start()
        time.sleep(10) # TEMP
        
        # DO STUFF HERE.
        clients = self.get_clients()
        self.xmit_sine(args.duration, args.freq, args.txgain, args.rate,
                       args.wfreq, args.wampl, [clients[0]])
        time.sleep(5)
        self.get_samples(args.nsamps, args.freq, args.rxgain, args.rate,
                         clients[1:])

        # Get/process results
        rmsg = measpb.SessionMsg()
        wcount = 0
        self.logger.info("Waiting for client responses...")
        while wcount < MAXWCOUNT:
            if self.pipe.poll(WAITTIME):
                rmsg.ParseFromString(self.pipe.recv())
                clientid = self._get_attr(rmsg, "clientid")
                if clientid == clients[1]:
                    vals = np.zeros(args.nsamps, dtype=np.complex64)
                    for kv in rmsg.attributes:
                        if kv.key.startswith("s"):
                            idx = int(kv.key[1:])
                            vals[idx] = complex(kv.val)
                    psd = compute_psd(len(vals), vals)
                    freqs = np.fft.fftshift(np.fft.fftfreq(len(vals),
                                                           1/args.rate))
                    plproc = mp.Process(target=plot_stuff, args=(freqs, psd))
                    plproc.start()
                else:
                    print("=== Call response:\n%s" % rmsg)
            else:
                wcount += 1
        self.logger.info("Done with calls...")
        self.netproc.join()

def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--freq", type=float, required=True)
    parser.add_argument("-r", "--rate", default=1e6, type=float)
    parser.add_argument("-d", "--txduration", default=10.0, type=float)
    parser.add_argument("-g", "--txgain", type=int, default=50)
    parser.add_argument("-g", "--rxgain", type=int, default=38)
    parser.add_argument("--wfreq", default=1e5, type=float)
    parser.add_argument("--wampl", default=0.5, type=float)
    parser.add_argument("-n", "--nsamps", default=256, type=int)
    return parser.parse_args()
        
if __name__ == "__main__":
    args = parse_args()
    meas = MeasurementsController()
    meas.run(args)
