#!/usr/bin/env python3

#
# Script for inserting static data into HDF5 file
#

import sys
import argparse
import json

import numpy as np
import h5py

DEF_DATADIR="./mcondata"
DEF_DFNAME="measurements.hdf5"
STATIC_ROOT = "static_data"

DSGRP = "dsgroup"
DSENTS = "entries"
DSNAME = "dsname"
DATA = "data"
ATTRS = "attributes"

def main(args):
    dsfile = h5py.File("%s/%s" % (args.datadir, args.dfname), "a")
    if not STATIC_ROOT in dsfile:
        dsfile.create_group(STATIC_ROOT)
    sroot = dsfile[STATIC_ROOT]
    with open(args.infile, "r") as infile:
        indata = json.load(infile)
        for grent in indata:
            dsgname = grent[DSGRP]
            if not dsgname in sroot:
                sroot.create_group(dsgname)
            dsgrp = sroot[dsgname]
            for dent in grent[DSENTS]:
                if DATA in dent:
                    dset = dsgrp.create_dataset(dent[DSNAME], data=dent[DATA])
                if ATTRS in dent:
                    dsgrp.attrs.update(dent[ATTRS])
            

def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--datadir", type=str, default=DEF_DATADIR, help="The directory where the data file resides. Default: %s" % DEF_DATADIR)
    parser.add_argument("-f", "--dfname", type=str, default=DEF_DFNAME, help="The name of the HDF5 format data file. Default: %s" % DEF_DFNAME)
    parser.add_argument("-i", "--infile", type=str, required=True, help="Input data to store in 'static' area of HDF5 file.")
    return parser.parse_args()

if __name__ == "__main__":
    main(parse_args())

