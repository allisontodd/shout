#!/usr/bin/env python3

import argparse

import numpy as np
import scipy.signal as sig
import h5py

from sigutils import *

DEF_OUTDIR="./mcondata"
DEF_DFNAME="measurements.hdf5"
MEAS_ROOT="measure_paths"
FOFF = 1e4

def main(args):
    dsfile = h5py.File("%s/%s" % (args.datadir, args.dfname), "r")
    if args.listds:
        dsfile.visit(print)
    if args.measdiff:
        if args.runstamp:
            run = dsfile[MEAS_ROOT][args.runstamp]
            rate = run.attrs['rate']
            if run.attrs['get_samples']:
                for tx in run.keys():
                    for rx in tx.keys():
                        fstep = run.attrs['freq_step']
                        steps = int(np.floor(rate/fstep/2))
                        nsamps = run.attrs['nsamps']
                        pwrs = []
                        for i in range(1,steps):
                            rsamps = rx[0][(i-1)*nsamps:i*nsamps]
                            tsamps = rx[1][(i-1)*nsamps:i*nsamps]
                            rsamps = butter_filt(rsamps, i*fstep - FOFF,
                                                 i*fstep + FOFF, rate)
                            tsamps = butter_filt(tsamps, i*fstep - FOFF,
                                                 i*fstep + FOFF, rate)
                            pwr = [get_avg_power(s) for s in (rsamps, tsamps)]
                            pwrs.append(pwr[1] - pwr[0])
                        print(pwrs)
            else:
                for tx in run.keys():
                    for rx in tx.keys():
                        print(rx[1]-rx[0])


def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--datadir", type=str, default=DEF_OUTDIR)
    parser.add_argument("-f", "--dfname", type=str, default=DEF_DFNAME)
    parser.add_argument("-l", "--listds", action="store_true")
    parser.add_argument("-t", "--runstamp", type=int, default=0)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
