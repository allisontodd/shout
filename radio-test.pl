#!/usr/bin/env python3

import argparse
import numpy as np
import uhd
import matplotlib.pyplot as plt

def parse_args():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--args", default="", type=str)
    parser.add_argument("-f", "--freq", type=float, required=True)
    parser.add_argument("-r", "--rate", default=1e6, type=float)
    parser.add_argument("-g", "--gain", type=int, default=10)
    parser.add_argument("-c", "--channel", type=int, default=0)
    parser.add_argument("-n", "--nsamps", type=int, default=256)
    return parser.parse_args()


def psd(nfft, samples):
    """Return the power spectral density of `samples`"""
    window = np.hamming(nfft)
    result = np.multiply(window, samples)
    result = np.fft.fftshift(np.fft.fft(result, nfft))
    result = np.square(np.abs(result))
    result = np.nan_to_num(10.0 * np.log10(result))
    return result

def main():
    args = parse_args()
    usrp = uhd.usrp.MultiUSRP(args.args)

    # Set the USRP rate, freq, and gain
    usrp.set_rx_rate(args.rate, args.channel)
    usrp.set_rx_freq(uhd.types.TuneRequest(args.freq), args.channel)
    usrp.set_rx_gain(args.gain, args.channel)

    # Create the buffer to recv samples
    samples = np.empty((1, args.nsamps), dtype=np.complex64)

    st_args = uhd.usrp.StreamArgs("fc32", "sc16")
    st_args.channels = [args.channel]

    metadata = uhd.types.RXMetadata()
    streamer = usrp.get_rx_stream(st_args)
    buffer_samps = streamer.get_max_num_samps()
    recv_buffer = np.zeros((1, buffer_samps), dtype=np.complex64)

    stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
    stream_cmd.stream_now = True
    streamer.issue_stream_cmd(stream_cmd)

    # Receive the samples
    for i in range(10):
        recv_samps = 0
        while recv_samps < args.nsamps:
            samps = streamer.recv(recv_buffer, metadata)

            if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
                print(metadata.strerror())
            if samps:
                real_samps = min(args.nsamps - recv_samps, samps)
                samples[:, recv_samps:recv_samps + real_samps] = recv_buffer[:, 0:real_samps]
                recv_samps += real_samps

    # Get the power in each bin
    bins = psd(args.nsamps, samples[args.channel][0:args.nsamps])

    # Stop streamer
    stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
    streamer.issue_stream_cmd(stream_cmd)

    # Plot it
    freqs = np.fft.fftshift(np.fft.fftfreq(bins.size, 1/args.rate))
    plt.plot(freqs, bins)
    plt.show()

if __name__ == "__main__":
    main()
