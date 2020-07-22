#!/usr/bin/env python3
#
# Measurements client
#

import logging
import multiprocessing as mp

import measurements_pb2 as measpb
from clientconnector import ClientConnector

LOGFILE="/var/tmp/ccontroller.log"
DEF_IP = "127.0.0.1"
DEF_PORT = 5555

class MeasurementsClient:
    def __init__(self, servip, servport):
        self.pipe = None
        self.conproc = None
        self.logger = None
        self.setup_logger()
        self.connector = ClientConnector(servip, servport)

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
    }
                    
if __name__ == "__main__":
    meascli = MeasurementsClient(DEF_IP, DEF_PORT)
    meascli.run()
