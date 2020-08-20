#!/usr/bin/env python3
#
# Measurement client/server RPC call definitions
#
import measurements_pb2 as measpb

RPCCALLS = {}

def get_attr(msg, key):
    for kv in msg.attributes:
        if kv.key == key: return kv.val
    return None

def add_attr(msg, key, val):
    attr = msg.attributes.add()
    attr.key = key
    attr.val = val

class RPCCall:
    def __init__(self, funcname, funcargs = {}):
        self.funcname = funcname
        self.funcargs = funcargs

    def call(self, **kwargs):
        cmsg = measpb.SessionMsg()
        cmsg.type = measpb.SessionMsg.CALL
        add_attr(cmsg, 'funcname', self.funcname)
        for aname,adict in self.funcargs:
            if aname in kwargs:
                val = kwargs[aname]
                if type(val) != adict['type']:
                    raise RuntimeError("Argument does not match type signature")
                add_attr(cmsg, aname, val)
            else:
                add_attr(cmsg, aname, adict['default'])
        return cmsg


RPCCALLS['txsine'] = \
    RPCCall('txsine',
            {
                'duration':  {'type': int, 'default': 0},
                'tune_freq': {'type': float, 'default': None},
                'gain':      {'type': float, 'default': 30.0},
                'rate':      {'type': float, 'default': 1e6},
                'wfreq':     {'type': float, 'default': 1e5},
                'wampl':     {'type': float, 'default': 0.3},
            })

RPCCALLS['rxsamples'] = \
    RPCCall('rxsamples',
            {
                'nsamps':    {'type': int, 'default': 256},
                'tune_freq': {'type': float, 'default': None},
                'gain':      {'type': float, 'default': 30.0},
                'rate':      {'type': float, 'default': 1e6},
            })
