#!/usr/bin/env python3

import logging
import time
import multiprocessing as mp

import measurements_pb2 as measpb
from serverconnector import ServerConnector

LOGFILE="/var/tmp/mcontroller.log"

WAITTIME = 1
MAXWCOUNT = 5

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
        time.sleep(5) # TEMP

        # Get list of clients
        cmsg = measpb.SessionMsg()
        cmsg.type = measpb.SessionMsg.CALL
        self._add_attr(cmsg, "funcname", ServerConnector.CALL_GETCLIENTS)
        self.pipe.send(cmsg.SerializeToString())
        rmsg = measpb.SessionMsg()
        rmsg.ParseFromString(self.pipe.recv())

        # Call "echo" on list of clients
        for cli in rmsg.attributes:
            self.logger.info("Sending to client %s" % cli.val)
            msg = measpb.SessionMsg()
            msg.type = measpb.SessionMsg.CALL
            self._add_attr(msg, "funcname", "echo")
            self._add_attr(msg, "type", "request")
            self._add_attr(msg, "clientid", cli.val)
            self.pipe.send(msg.SerializeToString())

        # Get results
        rmsg = measpb.SessionMsg()
        wcount = 0
        while wcount < MAXWCOUNT:
            if self.pipe.poll(WAITTIME):
                rmsg.ParseFromString(self.pipe.recv())
                print("=== Call response:\n%s" % rmsg)
            else:
                wcount += 1
        print("Done with calls...")
        self.netproc.join()
    
if __name__ == "__main__":
    # Daemonize
    #dcxt = daemon.DaemonContext(umask=0o022)
    #dcxt.open()

    # Set up logging.

    meas = MeasurementsController()
    meas.run()
