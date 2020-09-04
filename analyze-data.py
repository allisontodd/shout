#!/usr/bin/env python3

import argparse
import multiprocessing as mp

import numpy as np
import scipy.signal as sig
import h5py

from sigutils import *

DEF_OUTDIR="./mcondata"
DEF_DFNAME="measurements.hdf5"
MEAS_ROOT="measure_paths"
DEF_FILTBW = 1e5

def get_powerdiffs(attrs, rxds, filtbw):
    rate = attrs['rate']
    fstep = attrs['freq_step']
    steps = int(np.floor(rate/fstep/2))
    nsamps = attrs['nsamps']
    foff = filtbw/2
    pwrs = []
    for i in range(1,steps):
        rsamps = rxds[0][(i-1)*nsamps:i*nsamps]
        tsamps = rxds[1][(i-1)*nsamps:i*nsamps]
        rsamps = butter_filt(rsamps, i*fstep - foff,
                             i*fstep + foff, rate)
        tsamps = butter_filt(tsamps, i*fstep - foff,
                             i*fstep + foff, rate)
        pwr = [get_avg_power(s) for s in (rsamps, tsamps)]
        pwrs.append(pwr[1] - pwr[0])
    return pwrs

def main(args):
    dsfile = h5py.File("%s/%s" % (args.datadir, args.dfname), "r")
    if args.listds:
        dsfile.visit(print)
    if args.measdiff:
        run = dsfile[MEAS_ROOT][args.runstamp]
        rate = run.attrs['rate']
        if run.attrs['get_samples']:
            if args.txname:
                txgrp = run[args.txname]
                if args.rxname:
                    rxds = txgrp[args.rxname]
                    pwrs = get_powerdiffs(run.attrs, rxds, args.filtbw)
                    print(pwrs)
                else:
                    for rxname, rxds in txgrp.items():
                        rxds = txgrp[args.rxname]
                        pwrs = get_powerdiffs(run.attrs, rxds, args.filtbw)
                        print(pwrs)
            for txname, txgrp in run.items():
                for rxname, rxds in txgrp.items():
                    pwrs = get_powerdiffs(run.attrs, rxds, args.filtbw)
                    print(pwrs)
        else:
            for txname, txgrp in run.items():
                for rxname, rxds in txgrp.items():
                    print(rxds[1]-rxds[0])

    if args.plotpsd:
        run = dsfile[MEAS_ROOT][args.runstamp]
        rate = run.attrs['rate']
        for txname, txgrp in run.items():
            for rxname, rxds in txgrp.items():
                fstep = run.attrs['freq_step']
                steps = int(np.floor(rate/fstep/2))
                nsamps = run.attrs['nsamps']
                for i in range(1,steps):
                    tsamps = rxds[1][(i-1)*nsamps:i*nsamps]
                    psd = compute_psd(nsamps, tsamps)
                    freqs = np.fft.fftshift(np.fft.fftfreq(nsamps, 1/rate))
                    plproc = mp.Process(target=plot_stuff,
                                        args=(rxname, freqs, psd))
                    plproc.start()

def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--datadir", type=str, default=DEF_OUTDIR)
    parser.add_argument("-f", "--dfname", type=str, default=DEF_DFNAME)
    parser.add_argument("--txname", type=str)
    parser.add_argument("--rxname", type=str)
    parser.add_argument("-l", "--listds", action="store_true")
    parser.add_argument("-m", "--measdiff", action="store_true")
    parser.add_argument("-p", "--plotpsd", action="store_true")
    parser.add_argument("-t", "--runstamp", type=str, default=0)
    parser.add_argument("-b", "--filtbw", type=float, default=DEF_FILTBW)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
