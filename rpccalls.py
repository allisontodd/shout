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
    def __init__(self, funcname, funcargs = []):
        self.funcname = funcname
        self.funcargs = funcargs

    def call(self, *args, **kwargs):
        def add_arg(msg, aname, val, atype):
            if type(val) != atype:
                raise RuntimeError("Argument does not match type signature")
            add_attr(msg, aname, val)

        cmsg = measpb.SessionMsg()
        cmsg.type = measpb.SessionMsg.CALL
        add_attr(cmsg, 'funcname', self.funcname)
        for i in range(len(funcargs)):
            farg = self.funcargs[i]
            aname = farg['name']
            if i < len(args):
                add_arg(cmsg, aname, args[i], farg['type'])
            elif aname in kwargs:
                add_arg(cmsg, aname, kwargs[aname], farg['type'])
            else:
                add_attr(cmsg, aname, farg['default'])
        return cmsg


RPCCALLS['txsine'] = \
    RPCCall('txsine',
            [
                {'name': 'duration', 'type': int, 'default': 0}
                {'name': 'tune_freq', 'type': float, 'default': None}
                {'name': 'gain', 'type': float, 'default': 30.0}
                {'name': 'rate', 'type': float, 'default': 1e6}
                {'name': 'wfreq', 'type': float, 'default': 1e5}
                {'name': 'wampl', 'type': float, 'default': 0.3}
            ])

RPCCALLS['rxsamples'] = \
    RPCCall('rxsamples',
            [
                {'name': 'nsamps', 'type': int, 'default': 256}
                {'name': 'tune_freq', 'type': float, 'default': None}
                {'name': 'gain', 'type': float, 'default': 30.0}
                {'name': 'rate', 'type': float, 'default': 1e6}
            ])

RPCCALLS['measure_power'] = \
    RPCCall('measure_power',
            [
                {'name': 'duration', 'type': int, 'default': 5}
                {'name': 'tune_freq', 'type': float, 'default': None}
                {'name': 'gain', 'type': float, 'default': 30.0}
                {'name': 'freq_min', 'type': float, 'default': None}
                {'name': 'freq_max', 'type': float, 'default': None}
            ])
