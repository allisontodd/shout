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
DEF_FILTBW = 1e4

# Wrapper class to identify regex pattern string.
class RegexPattern(str):
    pass

# Simple class to represent timestamp ranges
class TimestampRange:
    def __init__(self, tmin, tmax):
        self.min = int(tmin)
        self.max = int(tmax)

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

def search_entries(filters, results, obj):
    pelts = obj.name.split('/')
    if len(filters) == len(pelts):
        i = 0
        for filt in filters:
            match = False
            if type(filt) not in (list, tuple):
                filt = [filt]
            for fent in filt:
                if type(fent) == RegexPattern:
                    if re.match(fent, pelts[i]): match = True
                elif type(fent) == TimestampRange:
                    tstamp = int(pelts[i])
                    if tstamp <= fent.max and tstamp >= fent.min: match = True
                else:
                    if fent == '*' or fent == pelts[i]: match = True
                if match:
                    break
            i += 1
            if match and i == len(pelts):
                results.append(obj)
    return None
        
def main(args):
    tstamp = args.runstamp if args.runstamp else '*'
    txname = args.txname if args.txname else '*'
    rxname = args.rxname if args.rxname else '*'
    dsfile = h5py.File("%s/%s" % (args.datadir, args.dfname), "r")

    if args.listds:
        dsfile.visit(print)

    elif args.measdiff:
        measurements = dsfile[MEAS_ROOT]
        filters = [tstamp, txname, rxname]
        if args.usesamps:
            print("Computing (average) power diff from samples.")
            filters.append('samples')
            results = []
            run.visit(lambda obj: search_entries(filters, results, obj))
            for dset in results:
                path = dset.name.split('/')
                run = measurements[path[1]]
                pwrs = get_powerdiffs(run.attrs, dset, args.filtbw)
                print(pwrs)
        else:
            print("Computing (average) power diff from pre-computed values.")
            filters.append('avgpower')
            results = []
            run.visit(lambda obj: search_entries(filters, results, obj))
            for dset in results:
                print(dset[1] - dset[0])

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
