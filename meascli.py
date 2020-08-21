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

from rpccalls import *
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

    def echo_reply(self, msg):
        self.logger.info("Received Echo Request. Sending response.")
        rmsg = measpb.SessionMsg()
        rmsg.type = measpb.SessionMsg.RESULT
        add_attr(rmsg, "funcname", self._get_attr(msg), "funcname")
        add_attr(rmsg, "type", "reply")
        self.pipe.send(rmsg.SerializeToString())

    def recv_samps(self, msg):
        funcname = get_attr(msg, 'funcname')
        args = RPCCALLS[funcname].decode(msg)
        rmsg = measpb.SessionMsg()
        rmsg.type = measpb.SessionMsg.RESULT
        add_attr(rmsg, "funcname", funcname)
        add_attr(rmsg, "rate", args['rate'])
        self.logger.info("Collecting %d samples." % args['nsamps'])
        self.radio.tune(args['tune_freq'], args['gain'], args['rate'])
        samples = self.radio.recv_samples(args['nsamps'])
        for samp in samples[0]:
            msamp = rmsg.samples.add()
            msamp.r, msamp.j = samp.real, samp.imag
        self.pipe.send(rmsg.SerializeToString())

    def xmit_sine(self, msg):
        funcname = get_attr(msg, 'funcname')
        args = RPCCALLS[funcname].decode(msg)
        rmsg = measpb.SessionMsg()
        rmsg.type = measpb.SessionMsg.RESULT
        add_attr(rmsg, "funcname", funcname)
        end    = time.time() + args['duration']
        nsamps = np.floor(args['rate']/args['wfreq'])
        nsamps *= np.ceil(self.XMIT_SAMPS_MIN/nsamps)
        sinebuf = mk_sine(int(nsamps), args['wampl'], args['wfreq'],
                          args['rate'])
        self.logger.info("Sending sine wave with freq %f" % args['wfreq'])
        self.radio.tune(args['tune_freq'], args['gain'], args['rate'])
        while time.time() < end:
            for i in range(self.SEND_SAMPS_COUNT):
                self.radio.send_samples(sinebuf)
        add_attr(rmsg, "result", "done")
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
            func = get_attr(msg, "funcname")
            if func in self.CALLS:
                self.CALLS[func](self, msg)
            else:
                self.logger.error("Unknown function called: %s" % func)


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
