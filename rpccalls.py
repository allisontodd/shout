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
    attr.val = str(val)
    
class RPCCall:
    def __init__(self, funcname, funcargs = {}):
        self.funcname = funcname
        self.funcargs = funcargs

    def encode(self, **kwargs):
        cmsg = measpb.SessionMsg()
        cmsg.type = measpb.SessionMsg.CALL
        add_attr(cmsg, 'funcname', self.funcname)
        for aname,adict in self.funcargs.items():
            if aname in kwargs:
                add_attr(cmsg, aname, kwargs[aname])
        return cmsg

    def decode(self, cmsg):
        argdict = {}
        argdict['start_time'] = cmsg.start_time
        cattrs = {kv.key: kv.val for kv in cmsg.attributes}
        for aname,adict in self.funcargs.items():
            if aname in cattrs:
                argdict[aname] = adict['type'](cattrs[aname])
            else:
                argdict[aname] = adict['default']
        return argdict

    
RPCCALLS['txsine'] = \
    RPCCall('txsine',
            {
                'duration':  {'type': int, 'default': 0},
                'freq':      {'type': float, 'default': None},
                'gain':      {'type': float, 'default': 30.0},
                'rate':      {'type': float, 'default': 1e6},
                'wfreq':     {'type': float, 'default': 1e5},
                'wampl':     {'type': float, 'default': 0.3},
            })

RPCCALLS['rxsamples'] = \
    RPCCall('rxsamples',
            {
                'nsamps':    {'type': int, 'default': 256},
                'freq':      {'type': float, 'default': None},
                'gain':      {'type': float, 'default': 30.0},
                'rate':      {'type': float, 'default': 1e6},
            })

RPCCALLS['measure_power'] = \
    RPCCall('measure_power',
            {
                'nsamps':    {'type': int, 'default': 256},
                'freq':      {'type': float, 'default': None},
                'gain':      {'type': float, 'default': 30.0},
                'rate':      {'type': float, 'default': 1e6},
                'wfreq':     {'type': float, 'default': 1e5},
            })

RPCCALLS['seq_measure'] = \
    RPCCall('seq_measure',
            {
                'nsamps':    {'type': int, 'default': 256},
                'freq':      {'type': float, 'default': None},
                'gain':      {'type': float, 'default': 30.0},
                'rate':      {'type': float, 'default': 1e6},
                'freq_step': {'type': float, 'default': 5e4},
                'time_step': {'type': float, 'default': 1},
            })

RPCCALLS['seq_transmit'] = \
    RPCCall('seq_transmit',
            {
                'freq':      {'type': float, 'default': None},
                'gain':      {'type': float, 'default': 30.0},
                'rate':      {'type': float, 'default': 1e6},
                'wampl':     {'type': float, 'default': 0.3},
                'freq_step': {'type': float, 'default': 5e4},
                'time_step': {'type': float, 'default': 1},
            })

RPCCALLS['seq_rxsamples'] = \
    RPCCall('seq_rxsamples',
            {
                'nsamps':    {'type': int, 'default': 256},
                'freq':      {'type': float, 'default': None},
                'gain':      {'type': float, 'default': 30.0},
                'rate':      {'type': float, 'default': 1e6},
                'freq_step': {'type': float, 'default': 5e4},
                'time_step': {'type': float, 'default': 1},
            })
