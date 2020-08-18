#!/usr/bin/env python3
#
# Measurements client
#

import logging
import time
import multiprocessing as mp
import numpy as np
import daemon
import argparse

import measurements_pb2 as measpb
from clientconnector import ClientConnector
from radio import Radio

LOGFILE="/var/tmp/ccontroller.log"
DEF_IP = "127.0.0.1"
DEF_PORT = 5555

def mk_sine(nsamps, wampl, wfreq, srate):
    vals = np.ones((1,nsamps), dtype=np.complex64) * np.arange(nsamps)
    return wampl * np.exp(vals * 2j * np.pi * wfreq/srate)

class MeasurementsClient:
    XMIT_SAMPS_MIN = 100000
    SEND_SAMPS_COUNT = 10
    
    def __init__(self, servaddr, servport, radio_args = ""):
        self.pipe = None
        self.conproc = None
        self.logger = None
        self.setup_logger()
        self.radio = Radio(radio_args)
        self.connector = ClientConnector(servaddr, servport)

    def setup_logger(self):
        fmat = logging.Formatter(fmt='%(asctime)s:%(levelname)s: %(message)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
        shandler = logging.StreamHandler()
        shandler.setFormatter(fmat)
        fhandler = logging.FileHandler(LOGFILE)
        fhandler.setFormatter(fmat)
        self.logger = mp.get_logger()
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(shandler)
        self.logger.addHandler(fhandler)

    def _add_attr(self, msg, key, val):
        attr = msg.attributes.add()
        attr.key = key
        attr.val = val

    def _get_attr(self, msg, key):
        for kv in msg.attributes:
            if kv.key == key: return kv.val
        return None

    def echo_reply(self, msg):
        self.logger.info("Received Echo Request. Sending response.")
        rmsg = measpb.SessionMsg()
        rmsg.type = measpb.SessionMsg.RESULT
        self._add_attr(rmsg, "funcname", "echo")
        self._add_attr(rmsg, "type", "reply")
        self.pipe.send(rmsg.SerializeToString())

    def recv_samps(self, msg):
        rmsg = measpb.SessionMsg()
        rmsg.type = measpb.SessionMsg.RESULT
        self._add_attr(rmsg, "funcname", self._get_attr(msg, "funcname"))
        self._add_attr(rmsg, "rate", self._get_attr(msg, "sample_rate"))
        nsamps = int(self._get_attr(msg, "nsamples"))
        tfreq  = float(self._get_attr(msg, "tune_freq"))
        gain   = int(self._get_attr(msg, "gain"))
        srate  = float(self._get_attr(msg, "sample_rate"))
        self.logger.info("Collecting %d samples." % nsamps)
        self.radio.tune(tfreq, gain, srate)
        samples = self.radio.recv_samples(nsamps)
        i = 0
        for samp in samples[0]:
            self._add_attr(rmsg, "s%d" % i, str(samp))
            i += 1
        self.pipe.send(rmsg.SerializeToString())

    def xmit_sine(self, msg):
        rmsg = measpb.SessionMsg()
        rmsg.type = measpb.SessionMsg.RESULT
        self._add_attr(rmsg, "funcname", self._get_attr(msg, "funcname"))
        tfreq  = float(self._get_attr(msg, "tune_freq"))
        gain   = int(self._get_attr(msg, "gain"))
        srate  = float(self._get_attr(msg, "sample_rate"))
        end    = time.time() + int(self._get_attr(msg, "duration"))
        wfreq  = float(self._get_attr(msg, "wave_freq"))
        wampl  = float(self._get_attr(msg, "wave_ampl"))
        nsamps = np.floor(srate/wfreq)
        nsamps *= np.ceil(self.XMIT_SAMPS_MIN/nsamps)
        sinebuf = mk_sine(int(nsamps), wampl, wfreq, srate)
        self.logger.info("Sending sine wave with freq %f" % wfreq)
        self.radio.tune(tfreq, gain, srate)
        while time.time() < end:
            for i in range(self.SEND_SAMPS_COUNT):
                self.radio.send_samples(sinebuf)
        self._add_attr(rmsg, "result", "done")
        self.pipe.send(rmsg.SerializeToString())
        
    def run(self):
        (c1, c2) = mp.Pipe()
        self.pipe = c1
        self.netproc = mp.Process(target=self.connector.run,
                                  args=(c2, self.logger))
        self.netproc.start()

        while True:
            msg = measpb.SessionMsg()
            msg.ParseFromString(self.pipe.recv())
            func = self._get_attr(msg, "funcname")
            if func in self.CALLS:
                self.CALLS[func](self, msg)


    CALLS = {
        "echo": echo_reply,
        "recv_samples": recv_samps,
        "xmit_sine": xmit_sine,
    }

def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--args", help="USRP radio arguments", default="", type=str)
    parser.add_argument("-s", "--host", help="Orchestrator host to connect to", default=DEF_IP, type=str)
    parser.add_argument("-p", "--port", help="Orchestrator port", default=DEF_PORT, type=int)
    parser.add_argument("-f", "--foreground", help="Run in foreground (don't daemonize)", action="store_true")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if not args.foreground:
        # Daemonize
        dcxt = daemon.DaemonContext(umask=0o022)
        dcxt.open()
    meascli = MeasurementsClient(args.host, args.port, args.args)
    meascli.run()
