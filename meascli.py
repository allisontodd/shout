#!/usr/bin/env python3
#
# Measurements client
#

import logging
import time
import multiprocessing as mp
import numpy as np
import scipy.signal as sig
import daemon
import argparse

from rpccalls import *
from sigutils import *
import measurements_pb2 as measpb
from clientconnector import ClientConnector
from radio import Radio

LOGFILE="/var/tmp/ccontroller.log"
DEF_IP = "127.0.0.1"
DEF_PORT = 5555
DEF_LOGLEVEL = logging.DEBUG

class MeasurementsClient:
    XMIT_SAMPS_MIN = 500000
    TOFF = 0.5
    
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
        self.logger.setLevel(DEF_LOGLEVEL)
        self.logger.addHandler(shandler)
        self.logger.addHandler(fhandler)

    def echo_reply(self, args, rmsg):
        self.logger.info("Received Echo Request. Sending response.")
        add_attr(rmsg, "type", "reply")
        self.pipe.send(rmsg.SerializeToString())

    def recv_samps(self, args, rmsg):
        add_attr(rmsg, "rate", args['rate'])
        self.logger.info("Collecting %d samples." % args['nsamps'])
        self.radio.tune(args['freq'], args['gain'], args['rate'])
        self._do_recv_samps(args, rmsg)

    def xmit_sine(self, args, rmsg):
        self.logger.info("Sending sine wave with freq %f" % args['wfreq'])
        self.radio.tune(args['freq'], args['gain'], args['rate'])
        args['end_time'] = time.time() + args['duration']
        self._do_xmit(args, rmsg)
        add_attr(rmsg, "result", "done")

    def meas_power(self, args, rmsg):
        self.radio.tune(args['freq'], args['gain'], args['rate'])
        self._do_meas_power(args, rmsg)

    def _do_recv_samps(self, args, rmsg):
        samples = self.radio.recv_samples(args['nsamps'])
        for samp in samples[0]:
            msamp = rmsg.samples.add()
            msamp.r, msamp.j = samp.real, samp.imag

    def _do_meas_power(self, args, rmsg):
        foff = args['filter_bw']/2
        flo, fhi = args['wfreq']-foff, args['wfreq']+foff
        #self.logger.info("Sampling power between %f and %f" %
        #                 (args['freq'] + flo, args['freq'] + fhi))
        samps = self.radio.recv_samples(args['nsamps'])
        fsamps = butter_filt(samps, flo, fhi, args['rate'])
        rmsg.measurements.append(get_avg_power(fsamps))

    def _do_xmit(self, args, rmsg):
        ratio = args['rate']/args['wfreq']
        nsamps = ratio * np.ceil(self.XMIT_SAMPS_MIN/ratio)
        sinebuf = mk_sine(int(nsamps), args['wampl'], args['wfreq'],
                          args['rate'])
        while time.time() < args['end_time']:
            self.radio.send_samples(sinebuf)

    def _do_seq(self, args, rmsg, func):
        self.logger.info("Performing radio command sequence...")
        self.radio.tune(args['freq'], args['gain'], args['rate'])
        steps = int(np.floor(args['rate']/args['freq_step']/2))
        if not args['start_time']:
            args['start_time'] = np.ceil(time.time())
        for i in range(1,steps):
            args['wfreq'] = i*args['freq_step']
            args['end_time'] = args['start_time'] + (i+1)*args['time_step'] - \
                self.TOFF
            sltime = args['start_time'] + i*args['time_step'] - time.time()
            if sltime > 0:
                time.sleep(sltime)
            else:
                self.logger.info("Late: %f" % sltime)
            func(self, args, rmsg)

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
                args = RPCCALLS[func].decode(msg)
                rmsg = measpb.SessionMsg()
                rmsg.type = measpb.SessionMsg.RESULT
                add_attr(rmsg, "funcname", func)
                if func.startswith('seq'):
                    self._do_seq(args, rmsg, self.CALLS[func])
                else:
                    self.CALLS[func](self, args, rmsg)
                self.pipe.send(rmsg.SerializeToString())
            else:
                self.logger.error("Unknown function called: %s" % func)

    CALLS = {
        "echo": echo_reply,
        "rxsamples": recv_samps,
        "txsine": xmit_sine,
        "measure_power": meas_power,
        "seq_rxsamples": _do_recv_samps,
        "seq_measure":  _do_meas_power,
        "seq_transmit": _do_xmit,
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
