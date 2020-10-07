#!/usr/bin/env python3

import numpy as np
import scipy.signal as sig
import matplotlib.pyplot as plt

def mk_sine(nsamps, wampl, wfreq, srate):
    vals = np.ones((1,nsamps), dtype=np.complex64) * np.arange(nsamps)
    return wampl * np.exp(vals * 2j * np.pi * wfreq/srate)

def butter_filt(samps, flo, fhi, srate, order = 5):
    nyq = 0.5*srate
    b, a = sig.butter(order, [flo/nyq, fhi/nyq], btype='band')
    return sig.lfilter(b, a, samps)

def get_avg_power(samps):
    return 10.0 * np.log10(np.sum(np.square(np.abs(samps)))/len(samps))

def compute_psd(nfft, samples):
    """Return the power spectral density of `samples`"""
    window = np.hamming(nfft)
    result = np.multiply(window, samples)
    result = np.fft.fftshift(np.fft.fft(result, nfft))
    result = np.square(np.abs(result))
    result = np.nan_to_num(10.0 * np.log10(result))
    return result

def plot_stuff(title, *args):
    plt.suptitle("Client: %s" % title)
    plt.plot(*args)
    plt.show()
