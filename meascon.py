#!/usr/bin/env python3

import logging
import time
import multiprocessing as mp
import numpy as np

import measurements_pb2 as measpb
from serverconnector import ServerConnector

LOGFILE="/var/tmp/mcontroller.log"

WAITTIME = 10
MAXWCOUNT = 6

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

    def _add_attr(self, msg, key, val):
        attr = msg.attributes.add()
        attr.key = key
        attr.val = val

    def run(self):
        (c1, c2) = mp.Pipe()
        self.pipe = c1
        self.netproc = mp.Process(target=self.connector.run,
                                  args=(c2, self.logger))
        self.netproc.start()
        time.sleep(10) # TEMP

        # Get list of clients
        cmsg = measpb.SessionMsg()
        cmsg.type = measpb.SessionMsg.CALL
        self._add_attr(cmsg, "funcname", ServerConnector.CALL_GETCLIENTS)
        self.pipe.send(cmsg.SerializeToString())
        rmsg = measpb.SessionMsg()
        rmsg.ParseFromString(self.pipe.recv())

        # Call "recv" on all clients
        self.logger.info("Gathering samples.")
        msg = measpb.SessionMsg()
        msg.type = measpb.SessionMsg.CALL
        self._add_attr(msg, "clientid", "all")
        self._add_attr(msg, "funcname", "recv_samples")
        self._add_attr(msg, "nsamples", "1000")
        self._add_attr(msg, "tune_freq", "1e9")
        self._add_attr(msg, "gain", "70")
        self._add_attr(msg, "sample_rate", "1e6")
        self.pipe.send(msg.SerializeToString())

        # Get results
        rmsg = measpb.SessionMsg()
        wcount = 0
        self.logger.info("Waiting for client responses...")
        while wcount < MAXWCOUNT:
            if self.pipe.poll(WAITTIME):
                rmsg.ParseFromString(self.pipe.recv())
                print("=== Call response:\n%s" % rmsg)
            else:
                wcount += 1
        self.logger.info("Done with calls...")
        self.netproc.join()

if __name__ == "__main__":
    # Daemonize
    #dcxt = daemon.DaemonContext(umask=0o022)
    #dcxt.open()

    # Set up logging.

    meas = MeasurementsController()
    meas.run()
