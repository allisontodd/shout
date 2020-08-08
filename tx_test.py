#!/usr/bin/env python3

import argparse
import time
import radio
import numpy as np
import multiprocessing as mp

def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--args", default="", type=str)
    parser.add_argument("-f", "--freq", type=float, required=True)
    parser.add_argument("-r", "--rate", default=1e6, type=float)
    parser.add_argument("-d", "--duration", default=10.0, type=float)
    parser.add_argument("-g", "--gain", type=int, default=50)
    parser.add_argument("--wfreq", default=1e5, type=float)
    parser.add_argument("--wampl", default=0.3, type=float)
    return parser.parse_args()

def do_alarm(runvar, duration):
    time.sleep(duration)
    print("whee!")
    runvar.value = False

if __name__ == '__main__':
    args = parse_args()

    runvar = mp.Value('b', True)
    proc = mp.Process(target=do_alarm, args=(runvar, args.duration))
    proc.start()

    endtime = time.time() + args.duration
    rad = radio.Radio()
    rad.tune(args.freq, args.gain)

    nsamps = 10000 * int(np.floor(args.rate/args.wfreq))
    vals = np.ones((1, nsamps), dtype=np.complex64) * np.arange(nsamps)
    samps = args.wampl * np.exp(vals * 2j * np.pi * args.wfreq / args.rate)

    while runvar.value:
        for i in range(10):
            rad.send_samples(samps)

    proc.join()
