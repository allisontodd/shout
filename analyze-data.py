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

def get_powerdiffs(attrs, ds, filtbw):
    rate = attrs['rate']
    fstep = attrs['freq_step']
    steps = int(np.floor(rate/fstep/2))
    nsamps = attrs['nsamps']
    foff = filtbw/2
    pwrs = []
    for i in range(1,steps):
        bsamps = np.array(ds[0][(i-1)*nsamps:i*nsamps])
        tsamps = np.array(ds[1][(i-1)*nsamps:i*nsamps])
        fbsamps = butter_filt(bsamps, i*fstep - foff,
                              i*fstep + foff, rate)
        ftsamps = butter_filt(tsamps, i*fstep - foff,
                              i*fstep + foff, rate)
        pwrs.append(get_avg_power(ftsamps) - get_avg_power(fbsamps))
    return pwrs

def do_plots(attrs, name, allsamps):
    rate = attrs['rate']
    fstep = attrs['freq_step']
    steps = int(np.floor(rate/fstep/2))
    nsamps = attrs['nsamps']
    for i in range(1,steps):
        tsamps = allsamps[(i-1)*nsamps:i*nsamps]
        psd = compute_psd(nsamps, tsamps)
        freqs = np.fft.fftshift(np.fft.fftfreq(nsamps, 1/rate))
        title = "%s-%f" % (name, i*fstep)
        plproc = mp.Process(target=plot_stuff,
                            args=(title, freqs, psd))
        plproc.start()

def main(args):
    dsfile = h5py.File("%s/%s" % (args.datadir, args.dfname), "r")
    if args.listds:
        dsfile.visit(print)

    elif args.measdiff:
        run = dsfile[MEAS_ROOT][args.runstamp]
        if args.usesamps and run.attrs['get_samples']:
            print("Computing avg power from samples.")
            if args.txname:
                txgrp = run[args.txname]
                if args.rxname:
                    rxds = txgrp[args.rxname]['samples']
                    pwrs = get_powerdiffs(run.attrs, rxds, args.filtbw)
                    print(pwrs)
                else:
                    for rxname, rxgrp in txgrp.items():
                        pwrs = get_powerdiffs(run.attrs, rxgrp['samples'],
                                              args.filtbw)
                        print(pwrs)
            else:
                for txname, txgrp in run.items():
                    for rxname, rxgrp in txgrp.items():
                        pwrs = get_powerdiffs(run.attrs, rxgrp['samples'],
                                              args.filtbw)
                        print(pwrs)
        else:
            print("Printing stored average power values.")
            for txname, txgrp in run.items():
                for rxname, rxgrp in txgrp.items():
                    print(rxgrp['avgpower'][1] - rxgrp['avgpower'][0])

    elif args.plotpsd:
        run = dsfile[MEAS_ROOT][args.runstamp]
        samps = run[args.txname][args.rxname]['samples'][1]
        do_plots(run.attrs, args.rxname, samps)

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
    parser.add_argument("-s", "--usesamps", action="store_true")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
