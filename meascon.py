#!/usr/bin/env python3

import logging
import time
import multiprocessing as mp

import measurements_pb2 as measpb
import controller

LOGFILE="/var/tmp/mcontroller.log"

class MeasurementsController:
    
    def __init__(self):
        self.clients = {}
        self.pipe = None
        self.conproc = None
        self.setup_logger()
        self.networker = controller.ControllerNetworker()

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
        
    def run(self):
        (c1, c2) = mp.Pipe()
        self.pipe = c1
        self.netproc = mp.Process(target=self.networker.run,
                                  args=(c2, self.logger))
        self.netproc.start()
        time.sleep(5) # TEMP
        msg = measpb.SessionMsg()
        msg.type = measpb.SessionMsg.CALL
        attr = msg.attributes.add()
        attr.key = "funcname"
        attr.val = controller.ControllerNetworker.CALL_GETCLIENTS
        self.pipe.send(msg.SerializeToString())
        rmsg = measpb.SessionMsg()
        rmsg.ParseFromString(self.pipe.recv())
        print("Client call response:\n%s" % rmsg)
        self.netproc.join()
    
if __name__ == "__main__":
    # Daemonize
    #dcxt = daemon.DaemonContext(umask=0o022)
    #dcxt.open()

    # Set up logging.

    meas = MeasurementsController()
    meas.run()
