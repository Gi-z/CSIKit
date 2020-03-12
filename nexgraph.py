from filters import hampel, running_mean, running_stdev
from matlab import db
from scipy import fftpack, signal, stats

from read_pcap import BeamformReader
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import os
import sys

def breathingfilter(reader):

    scaled_csi = reader.csi_trace

    #Grabbing the +128 subcarriers, under the assumption these
    #are from the Rx antenna.

    no_frames = len(scaled_csi)
    no_subcarriers = np.array(scaled_csi[0]["csi"]).shape[0]
    # no_subcarriers = 70
    xax = list([x["timestamp"] for x in scaled_csi])

    finalEntries = [np.zeros((no_frames, 1)) for x in range(no_subcarriers)]

    for x in range(no_frames):
        scaled_entry = scaled_csi[x]["csi"]
        for y in range(no_subcarriers):
            finalEntries[y][x] = db(abs(scaled_entry[y]))

    #We have finalEntries[subcarriers][frames].
    #Now we want to find subcarrier variance and clip a threshold.

    for x in range(no_subcarriers):
        finalEntry = finalEntries[x].flatten()
        if len(set(finalEntry)) != 1:
            variation = stats.variation(finalEntry)

            # if variation < 0.025:
            if x == 100:
                hampelData = hampel(finalEntry, 5)
                smoothedData = running_mean(hampelData, 5)
                finalEntries[x] = smoothedData
                plt.plot(xax, finalEntries[x], alpha=0.5)

    # entries = []

    # for x in range(no_subcarriers):
    #     finalEntry = finalEntries[x].flatten()
    #     if len(set(finalEntry)) != 1:
    #         variation = stats.variation(finalEntry)

    #         if not np.isnan(variation) and variation < 0.05:
    #             hampelData = hampel(finalEntry, 5)
    #             smoothedData = running_mean(hampelData, 2)
    #             finalEntries[x] = smoothedData
    #             entries.append(smoothedData)

    # plt.plot(xax, np.mean(entries, axis=0))

    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.legend(loc="upper right")
    plt.show()

def beatsfilter(reader):

    scaled_csi = reader.csi_trace

    #Grabbing the +128 subcarriers, under the assumption these
    #are from the Rx antenna.

    no_frames = len(scaled_csi)
    no_subcarriers = np.array(scaled_csi[0]["csi"]).shape[0]
    # no_subcarriers = 70
    xax = list([x["timestamp"] for x in scaled_csi])
    if xax[0] != 0:
        xax -= xax[0]

    Fs = 1/np.mean(np.diff(xax))

    finalEntries = [np.zeros((no_frames, 1)) for x in range(no_subcarriers)]

    for x in range(no_frames):
        scaled_entry = scaled_csi[x]["csi"]
        for y in range(no_subcarriers):
            finalEntries[y][x] = db(abs(scaled_entry[y]))

    #We have finalEntries[subcarriers][frames].
    #Now we want to find subcarrier variance and clip a threshold.

    stabilities = []

    for x in range(no_subcarriers):
        finalEntry = finalEntries[x].flatten()
        variation = stats.variation(finalEntry)

        if not np.isnan(variation) and variation < 0.5:
            hampelData = hampel(finalEntry, 20)
            smoothedData = running_mean(hampelData, 20)

            b, a = signal.butter(3, [1/(Fs/2), 2/(Fs/2)], "bandpass")
            filtData = signal.lfilter(b, a, smoothedData.flatten())[20:]

            #Removed the first 50 values to cut out the spike.
            #Average HR should be 70.

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

def multibreathefilter(reader):

    scaled_csi = reader.csi_trace

    no_frames = len(scaled_csi)
    no_subcarriers = np.array(scaled_csi[1]["csi"]).shape[0]
    xax = list([x["timestamp"] for x in scaled_csi])

    finalEntries = [np.zeros((no_frames, 1)) for x in range(no_subcarriers)]

    for x in range(no_frames):
        scaled_entry = scaled_csi[x]["csi"]
        for y in range(no_subcarriers):
            finalEntries[y][x] = db(abs(scaled_entry[y]))

    for x in range(no_subcarriers):
        finalEntry = finalEntries[x].flatten()
        hampelData = hampel(finalEntry, 20)
        smoothedData = running_mean(hampelData, 5)
        finalEntries[x] = smoothedData

        plt.plot(xax, finalEntries[x], alpha=0.5)

    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.legend(loc="upper right")
    plt.show()

def heatmap(reader):

    scaled_csi = reader.csi_trace

    no_frames = len(scaled_csi)
    no_subcarriers = int(np.array(scaled_csi[0]["csi"]).shape[0])
    xax = list([x["timestamp"] for x in scaled_csi])
    if xax[0] != 0:
        xax -= xax[0]

    Fs = 1/np.mean(np.diff(xax))
    print("Sampling Rate: " + str(Fs))

    limits = [0, xax[-1], 1, no_subcarriers]

    finalEntry = np.zeros((no_subcarriers, no_frames))

    # Replace complex CSI with amplitude.
    for y in range(no_subcarriers):
        for x in range(no_frames):
            scaled_entry = scaled_csi[x]["csi"]
            finalEntry[y][x] = db(abs(scaled_entry[y]))

    #x = subcarrier index
    #y = time (s)
    #z = amplitude (dBm)

    for x in range(no_subcarriers):
        fe = finalEntry[x].flatten()

        variation = stats.variation(fe)
        if not np.isnan(variation) and variation < 0.05:
            hampelData = hampel(finalEntry[x].flatten(), 10)
            smoothedData = running_mean(hampelData, 10)

            b, a = signal.butter(2, [1/(Fs/2), 2/(Fs/2)], "bandpass")
            finalEntry[x] = signal.lfilter(b, a, finalEntry[x].flatten())
            # for i in range(0, 100):
            #     finalEntry[x][i] = 0
        else:
            finalEntry[x] = np.zeros((no_frames))

    fig, ax = plt.subplots()
    im = ax.imshow(finalEntry, cmap="jet", extent=limits, aspect="auto")

    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Amplitude (dBm)")

    plt.xlabel("Time (s)")
    plt.ylabel("Subcarrier Index")

    plt.show()

def statsgraph(reader):

    scaled_csi = reader.csi_trace

    no_frames = len(scaled_csi)
    no_subcarriers = np.array(scaled_csi[1]["csi"]).shape[0]
    xax = list([x["timestamp"] for x in scaled_csi])

    finalEntries = [np.zeros((no_frames, 1)) for x in range(no_subcarriers)]

    for x in range(no_frames):
        scaled_entry = scaled_csi[x]["csi"]
        for y in range(no_subcarriers):
            finalEntries[y][x] = db(abs(scaled_entry[y]))

    means = []
    stds = []

    for x in range(no_subcarriers):
        variation = stats.variation(finalEntries[x])
        mean = np.mean(finalEntries[x])
        std = np.std(finalEntries[x])*20

        if variation <= 0.05:
            print(x)

        if np.isnan(variation):
            variation = np.array(0)
        finalEntries[x] = variation

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

    ax2.bar(range(no_subcarriers), finalEntries, label="CV", color=color)
    ax2.plot(range(no_subcarriers), np.full((no_subcarriers), 0.05), label="threshold", color=color, linestyle="dashed")

    ax2.legend(loc="upper right")

    fig.tight_layout()
    plt.show()

    # plt.xticks(np.arange(0, no_subcarriers, step=10))

    # plt.xlabel("Subcarrier Index")
    # plt.ylabel("Coefficient of Variance")
    # plt.legend(loc="upper right")
    # plt.show()

def traceStats(reader):

    csi_trace = reader.csi_trace

    #Average sampling rate.
    x = list([x["timestamp"] for x in csi_trace])
    tdelta = (x[-1] - x[0]) / len(x)

    print("Frames: {}".format(len(csi_trace)))
    print("Average sampling rate: {}Hz".format((1/tdelta)))
    print("CSI Shape: {}".format(np.array(csi_trace[0]["csi"]).shape))

def main():

    basePath = Path(__file__).parent
    path = (basePath / "../sample_data/breathtest1.pcap").resolve()

    if len(sys.argv) > 1:
        tmpPath = sys.argv[1]
        if os.path.exists(tmpPath):
            path = tmpPath
        else:
            print("File at {} not found.".format(tmpPath))
            exit(1)

    reader = BeamformReader(path)

    # traceStats(reader)
    # heatmap(reader)
    # beatsfilter(reader)
    # multibreathefilter(reader)
    breathingfilter(reader)
    # statsgraph(reader)

main()