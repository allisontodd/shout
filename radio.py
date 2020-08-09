#!/usr/bin/env python3
#
# SDR interaction class
#

import uhd
import numpy as np

class Radio:
    TUNE_CLEAR_COUNT = 10

    def __init__(self, usrp_args = "", chan = 0):
        self.usrp = uhd.usrp.MultiUSRP(usrp_args)
        self.channel = chan
        self.rxstreamer = None
        self.txstreamer = None

    def __del__(self):
        self._kill_streamers()

    def _kill_streamers(self):
        if self.rxstreamer:
            stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
            self.rxstreamer.issue_stream_cmd(stream_cmd)
            self.rxstreamer = None

        if self.txstreamer:
            # Send a mini EOB packet
            metadata = uhd.types.TXMetadata()
            metadata.end_of_burst = True
            self.txstreamer.send(np.zeros((1, 0), dtype=np.complex64), metadata)
            self.txstreamer = None

    def tune(self, freq, gain, rate = None):
        # Kill any existing streamers
        self._kill_streamers()

        # Set the USRP freq, gain, and rate (if provided)
        self.usrp.set_rx_freq(uhd.types.TuneRequest(freq), self.channel)
        self.usrp.set_rx_gain(gain, self.channel)
        self.usrp.set_tx_freq(uhd.types.TuneRequest(freq), self.channel)
        self.usrp.set_tx_gain(gain, self.channel)
        if rate:
            self.usrp.set_tx_rate(rate, self.channel)
            self.usrp.set_rx_rate(rate, self.channel)

        # Set up streamers
        st_args = uhd.usrp.StreamArgs("fc32", "sc16")
        st_args.channels = [self.channel]
        self.txstreamer = self.usrp.get_tx_stream(st_args)
        self.rxstreamer = self.usrp.get_rx_stream(st_args)
        rx_stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        rx_stream_cmd.stream_now = True
        self.rxstreamer.issue_stream_cmd(rx_stream_cmd)

        ### Flush the pipes
        # For collecting metadata from radio command (i.e., errors, etc.)
        metadata = uhd.types.RXMetadata()
        # Figure out the size of the receive buffer and make it
        buffer_samps = self.rxstreamer.get_max_num_samps()
        recv_buffer = np.zeros((1, buffer_samps), dtype=np.complex64)
        # Loop several times and read samples to clear out gunk.
        for i in range(self.TUNE_CLEAR_COUNT):
            samps = self.rxstreamer.recv(recv_buffer, metadata)
            if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
                print(metadata.strerror())

    def recv_samples(self, nsamps, rate = None):
        # Set the sampling rate if necessary
        if rate:
            self.usrp.set_rx_rate(rate, self.channel)

        # Create the array to hold the return samples.
        samples = np.empty((1, nsamps), dtype=np.complex64)

        # For collecting metadata from radio command (i.e., errors, etc.)
        metadata = uhd.types.RXMetadata()

        # Figure out the size of the receive buffer and make it
        buffer_samps = self.rxstreamer.get_max_num_samps()
        recv_buffer = np.zeros((1, buffer_samps), dtype=np.complex64)

        # Loop until we get the number of samples requested.  Append each
        # batch received to the return array.
        recv_samps = 0
        while recv_samps < nsamps:
            samps = self.rxstreamer.recv(recv_buffer, metadata)

            if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
                print(metadata.strerror())
            if samps:
                real_samps = min(nsamps - recv_samps, samps)
                samples[:, recv_samps:recv_samps + real_samps] = \
                    recv_buffer[:, 0:real_samps]
                recv_samps += real_samps

        # Done.  Return samples.
        return samples

    def send_samples(self, samples, rate = None):
        # Set the sampling rate if necessary
        if rate:
            self.usrp.set_tx_rate(rate, self.channel)

        # For collecting metadata from radio command (i.e., errors, etc.)
        metadata = uhd.types.TXMetadata()

        # Figure out the size of the receive buffer and make it
        max_tx_samps = self.txstreamer.get_max_num_samps()
        tot_samps = samples.size

        tx_buffer = np.zeros((1, max_tx_samps), dtype=np.complex64)
        
        tx_samps = 0
        while tx_samps < tot_samps:
            nsamps = min(tot_samps - tx_samps, max_tx_samps)
            tx_buffer[:, 0:0 + nsamps] = samples[:, tx_samps:tx_samps + nsamps]
            if nsamps < max_tx_samps:
                tx_buffer[:, nsamps:] = 0. + 0.j
            tx_samps += self.txstreamer.send(tx_buffer, metadata)

            #if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
            #    print(metadata.strerror())
