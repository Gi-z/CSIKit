import math
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from csitools import getCSI, getTimestamps
from filters import hampel, running_mean, running_stdev, bandpass
from matlab import db
from read_pcap import BeamformReader
from scipy import fftpack, signal, stats


def breathingfilter(scaled_csi):
    xax = getTimestamps(scaled_csi)
    csi, no_frames, no_subcarriers = getCSI(scaled_csi)

    # Zeroing out invalid subcarriers.
    # for i in []:
    #     for x in range(no_frames):
    #         csi[i][x] = 0

    # for x in range(no_subcarriers):
    for x in range(80, 100):
        finalEntry = csi[x].flatten()

        hampelData = hampel(finalEntry, 10)
        smoothedData = running_mean(hampelData, 10)
        # csi[x] = hampelData
        csi[x] = smoothedData
        plt.plot(xax, csi[x], alpha=0.5, label=x)

    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.legend(loc="upper right")
    plt.show()

def beatsfilter(scaled_csi):
    xax = getTimestamps(scaled_csi)
    csi, no_frames, no_subcarriers = getCSI(scaled_csi)

    Fs = 1/np.mean(np.diff(xax))

    stabilities = []

    for x in range(no_subcarriers):
        finalEntry = csi[x].flatten()
        variation = stats.variation(finalEntry)

        if not np.isnan(variation) and variation < 0.5:
            hampelData = hampel(finalEntry, 5)
            smoothedData = running_mean(hampelData, 5)
            filtData = bandpass(5, 1, 1.3, Fs, smoothedData)

            wLength = 1*Fs
            N = np.mod(len(filtData), wLength)
            windows = np.array_split(filtData, N)

            psds = []
            for window in windows:
                f, Pxx_den = signal.welch(window, Fs)
                fMax = f[np.argmax(Pxx_den)]
                psds.append(fMax)

            specStab = 1/np.var(psds)
            print("Sub: {} has spectral stability: {}".format(x, specStab))

            # plt.plot(xax, filtData, alpha=0.5)
            stabilities.append({"sub": x, "stability": specStab, "data": filtData})

    stabilities.sort(key=lambda x: x["stability"], reverse=True)

    bestStab = stabilities[0]["stability"]
    news = []
    for stab in stabilities:
        if stab["stability"] >= (bestStab/100)*20:
            news.append(stab)

    print("Using {} subcarriers.".format(len(news)))
    pxxs = []
    for sub in news:
        filtData = sub["data"]
        f, Pxx_den = signal.welch(filtData, Fs)
        pxxs.append(Pxx_den)

    meanPsd = np.mean(pxxs, axis=0)

    plt.plot(f*60, meanPsd, alpha=0.5)

    plt.xlabel("Estimated Heart Rate [bpm]")
    plt.ylabel("PSD [V**2/Hz]")
    plt.legend(loc="upper right")
    plt.show()

def heatmap(scaled_csi):

    timestamps = getTimestamps(scaled_csi)
    csi, no_frames, no_subcarriers = getCSI(scaled_csi)

    Fs = 1/np.mean(np.diff(timestamps))
    print("Sampling Rate: " + str(Fs))

    limits = [0, timestamps[-1], 1, no_subcarriers]

    for x in range(no_subcarriers):
        hampelData = hampel(csi[x].flatten(), 5)
        smoothedData = running_mean(hampelData, 5)
        butteredData = bandpass(7, 0.2, 0.3, Fs, smoothedData)
        csi[x] = butteredData

    fig, ax = plt.subplots()
    im = ax.imshow(csi, cmap="jet", extent=limits, aspect="auto")

    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Amplitude (dBm)")

    plt.xlabel("Time (s)")
    plt.ylabel("Subcarrier Index")

    plt.show()

def statsgraph(scaled_csi):

    xax = getTimestamps(scaled_csi)
    csi, no_frames, no_subcarriers = getCSI(scaled_csi)

    means = []
    stds = []

    for x in range(no_subcarriers):
        variation = stats.variation(csi[x])
        mean = np.mean(csi[x])
        std = np.std(csi[x])*20

        if variation <= 0.05:
            print(x)

        if np.isnan(variation):
            variation = np.array(0)
        csi[x] = variation

        means.append(mean)
        stds.append(std)


    fig, ax1 = plt.subplots()

    color = "tab:blue"
    ax1.set_xlabel("Subcarrier Index")

    ax1.plot(range(no_subcarriers), means, label="mean", color=color, linestyle="dashed")
    ax1.plot(range(no_subcarriers), stds, label="std dev x 20", color=color)
    ax1.tick_params(axis="y", labelcolor=color)

    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()

    color = "tab:red"

    ax2.bar(range(no_subcarriers), csi, label="CV", color=color)
    ax2.plot(range(no_subcarriers), np.full((no_subcarriers), 0.05), label="threshold", color=color, linestyle="dashed")

    ax2.legend(loc="upper right")

    fig.tight_layout()
    plt.show()

def traceStats(scaled_csi):
    xax = getTimestamps(scaled_csi)
    csi, no_frames, no_subcarriers = getCSI(scaled_csi)

    #Average sampling rate.
    tdelta = (xax[-1] - xax[0]) / len(xax)

    print("Frames: {}".format(no_frames))
    print("Average sampling rate: {}Hz".format((1/tdelta)))
    print("CSI Shape: {}".format(csi.shape))

def main():

    basePath = Path(__file__).parent
    path = (basePath / "./data/pi/walk.pcap").resolve()

    # path = r"E:\\DataLab PhD Albyn 2018\\Code\\sample_data\\hrtest2.pcap"

    # if len(sys.argv) > 1:
    #     tmpPath = sys.argv[1]
    #     if os.path.exists(tmpPath):
    #         path = tmpPath
    #     else:
    #         print("File at {} not found.".format(tmpPath))
    #         exit(1)

    reader = BeamformReader(path)
    scaled_csi = reader.csi_trace

    # traceStats(scaled_csi)
    # heatmap(scaled_csi)
    beatsfilter(scaled_csi)
    # breathingfilter(scaled_csi)
    # statsgraph(scaled_csi)

main()