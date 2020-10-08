#!/usr/bin/env python3

import sys
import argparse
import multiprocessing as mp
import re

import numpy as np
import scipy.signal as sig
import matplotlib.pyplot as plt
import h5py

from sigutils import *

DEF_DATADIR="./mcondata"
DEF_DFNAME="measurements.hdf5"
MEAS_ROOT="measure_paths"
STATIC_ROOT="static_data"
DEF_FILTBW = 1e4

RATTRS = "_RUN_ATTRS"
DATA = "_DATA"
TXNAME = "_TXNAME"
RXNAME = "_RXNAME"

SITE_NAMES = ['bes', 'browning', 'dentistry', 'honors', 'hospital', 'fm', 'meb', 'smt', 'ustar']

SITE_PATTERNS = {
    'bes': r'-bes-?',
    'browning': r'-browning-?',
    'dentistry': r'-dentistry-?',
    'honors': r'-honors-?',
    'hospital': r'-hospital-?',
    'fm': r'-fm-?',
    'meb': r'-meb-?',
    'smt': r'-smt-?',
    'ustar': r'-ustar-?'
}

# Wrapper class to identify regex pattern string.
class RegexPattern(str):
    pass

# Simple class to represent timestamp ranges
class TimestampRange:
    def __init__(self, tmin, tmax):
        self.min = int(tmin)
        self.max = int(tmax)

def calc_powerdiffs_from_samples(attrs, ds, filtbw):
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
    return np.array(pwrs)

def do_psd_plots(attrs, name, allsamps):
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

def search_entries(filters, results, name, obj):
    pelts = name.split('/')
    if len(filters) == len(pelts):
        i = 0
        for filt in filters:
            match = False
            if type(filt) not in (list, tuple):
                filt = [filt]
            for fent in filt:
                match = False
                if type(fent) == RegexPattern:
                    if re.match(fent, pelts[i]): match = True
                elif type(fent) == TimestampRange:
                    try:
                        tstamp = int(pelts[i])
                        if tstamp <= fent.max and tstamp >= fent.min: match = True
                    except ValueError:
                        pass
                else:
                    if fent == '*' or fent == pelts[i]: match = True
                if match:
                    break
            i += 1
            if not match:
                return None
            elif i == len(pelts):
                results.append(obj)
    return None

def calc_measdiffs(objs, args):
    diffs = []
    for obj in objs:
        ent = {}
        run = obj.parent.parent
        ent[RATTRS] = run.attrs
        ent[TXNAME] = obj.parent.name.split('/')[-1]
        ent[RXNAME] = obj.name.split('/')[-1]
        if args.usesamps:
            ent[DATA] = calc_powerdiffs_from_samples(run.attrs, obj['samples'],
                                                     args.filtbw)
        else:
            ent[DATA] = obj['avgpower'][1] - obj['avgpower'][0]
        diffs.append(ent)
    return diffs

def get_site(name):
    return list(filter(lambda a: re.search(a[1],name), SITE_PATTERNS.items()))[0][0]

def plot_measdiffs(distdata, diffs):
    means = []
    dists = []
    for d in diffs:
        txname = get_site(d[TXNAME])
        rxname = get_site(d[RXNAME])
        x = distdata[txname].attrs[rxname]
        y = np.mean(d[DATA])
        plt.plot(x, y, 'rx')
        plt.annotate("%s,%s" % (txname, rxname), (x,y))
        dists.append(x)
        means.append(y)
    m, b = np.polyfit(dists, means, 1)
    plt.plot(dists, m*np.array(dists) + b, label = "slope: %f" % m)
    plt.legend()
    plt.show()

def plot_diffbars(distdata, diffs):
    sites = {}
    cnt = {}
    w = 0.15
    colors = ['midnightblue','cornflowerblue','darkcyan','royalblue','deepskyblue','cadetblue','darkturquoise','steelblue','teal']
    for d in diffs:
        txname = get_site(d[TXNAME])
        rxname = get_site(d[RXNAME])
        if not txname in sites:
            sites[txname] = {}
        if not rxname in sites[txname]:
            sites[txname][rxname] = []
        sites[txname][rxname].append(d[DATA])
    i = 0.0
    lbls = []
    fig, ax = plt.subplots()
    for txname, rxset in sites.items():
        for rxname,data in rxset.items():
            lbls.append("%s\n%s" % (txname, rxname))
            avgs = np.mean(sites[txname][rxname],0)
            stds = np.std(sites[txname][rxname],0)
            l = len(sites[txname][rxname][0])
            xstep = w*(l + 3)
            for k in range(l):
                off = i + w*(k - l/2)
                v = avgs[k] if avgs[k] > 0 else 0
                ax.bar(off, v, w, color=colors[k], yerr=[[0],[stds[k]]])
            i += xstep
    ax.set_xticks(np.arange(i, step=xstep))
    ax.set_xticklabels(lbls)
    fig.tight_layout()
    plt.xticks(rotation=90)
    plt.ylabel("Power difference (dB)")
    plt.show()
    
def main(args):
    filters = []
    tsmin = -1
    tsmax = -1
    tstamp = None
    if args.timerange:
        tsmin, tsmax = [int(t) for t in args.timerange.split(",")]
        filters.append(TimestampRange(tsmin, tsmax))
    elif args.runstamp:
        tstamp = args.runstamp
        filters.append(tstamp)
    else:
        tstamp = '*'
        filters.append(tstamp)
    txname = args.txname if args.txname else '*'
    filters.append(txname)
    rxname = args.rxname if args.rxname else '*'
    filters.append(rxname)

    dsfile = h5py.File("%s/%s" % (args.datadir, args.dfname), "r")

    if args.listds:
        filters.insert(0,'*')
        results = []
        dsfile.visititems(lambda name, obj:
                          search_entries(filters, results, name, obj))
        for res in results:
            print(res.name)

    elif args.measdiff:
        results = []
        filters.insert(0, MEAS_ROOT)
        dsfile.visititems(lambda name, obj:
                          search_entries(filters, results, name, obj))
        diffs = calc_measdiffs(results, args)
        distgrp = dsfile[STATIC_ROOT]['distances']
        for d in diffs:
            txname = get_site(d[TXNAME])
            rxname = get_site(d[RXNAME])
            print("Transmitter: %s, Receiver: %s, Distance: %d" %
                  (txname, rxname, distgrp[txname].attrs[rxname]))
            print(d[DATA])
        plot_measdiffs(distgrp, diffs)
        plot_diffbars(distgrp, diffs)

    elif args.plotpsd:
        if not args.runstamp or not args.txname or not args.rxname:
            print("To plot a PSD, you must specify a runstamp, txname, and rxname.", file=sys.stderr)
            exit(1)
        run = dsfile[MEAS_ROOT][args.runstamp]
        samps = run[args.txname][args.rxname]['samples'][1]
        do_psd_plots(run.attrs, args.rxname, samps)

def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--datadir", type=str, default=DEF_DATADIR, help="The directory where the data file resides. Default: %s" % DEF_DATADIR)
    parser.add_argument("-f", "--dfname", type=str, default=DEF_DFNAME, help="The name of the HDF5 format data file. Default: %s" % DEF_DFNAME)
    parser.add_argument("--txname", type=str, help="Specify a particular transmitter to search for.")
    parser.add_argument("--rxname", type=str, help="Specify a particular receiver to search for.")
    parser.add_argument("-l", "--listds", action="store_true", help="List all datasets that match the given search/filter criteria.")
    parser.add_argument("-m", "--measdiff", action="store_true", help="Print the measurements difference between noise power and transmit power for the matching path measurement data.")
    parser.add_argument("-p", "--plotpsd", action="store_true", help="Plot the PSD of a set of stored samples. Must specify runstamp, txname, and rxname.")
    parser.add_argument("-t", "--runstamp", type=str, default=0, help="Limit to entries logged at a specific unix timestamp.")
    parser.add_argument("-r", "--timerange", type=str, default="", help="Search for entries in a time range define by two unix timestamps separated by commas (e.g. 1602005000,1602006000).")
    parser.add_argument("-b", "--filtbw", type=float, default=DEF_FILTBW, help="Bandpass filter bandwidth for calculating average power for carrier wave transmissions. Default: %f" % DEF_FILTBW)
    parser.add_argument("-s", "--usesamps", action="store_true", help="Use stored samples (if they exist) to calculate the requested data.")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
