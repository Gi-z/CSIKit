import os

import matplotlib.pyplot as plt
import numpy as np
import scipy.io
from filters import hampel, running_mean, running_stdev, dynamic_detrend, bandpass
from matlab import db
from read_bfee import BeamformReader
from scipy import fftpack, signal, stats


def getCSI(scaled_csi, metric="amplitude"):
    no_frames = len(scaled_csi)
    no_subcarriers = scaled_csi[0]["csi"].shape[0]

    finalEntries = np.zeros((no_subcarriers, no_frames))

    for x in range(no_frames):
        scaled_entry = scaled_csi[x]["csi"]
        for y in range(no_subcarriers):
            if metric == "phasediff":
                if scaled_entry.shape[1] >= 2:
                    #Not 100% sure this generates correct Phase Difference.
                    finalEntries[y][x] = np.angle(scaled_entry[y][1][0])-np.angle(scaled_entry[y][0][0])
                else:
                    #In cases where only one antenna is available,
                    #reuse the previous value.
                    finalEntries[y][x] = finalEntries[y][x-1]
            elif metric == "amplitude":
                if scaled_entry.shape[1] >= 2:
                    finalEntries[y][x] = db(abs(scaled_entry[y][1][0]))
                else:
                    finalEntries[y][x] = db(abs(scaled_entry[y][0][0]))

    return (no_frames, no_subcarriers, finalEntries)

def fft(reader):

    scaled_csi = reader.csi_trace

    Fs = 20

    no_frames, no_subcarriers, finalEntry = getCSI(scaled_csi)

    y = bandpass(7, 1, 1.5, Fs, finalEntry[15])

    #rfft is a real Fast Fourier Transform, as we aren't interested in the imaginary parts.
    #as half of the points lie in the imaginary/negative domain, we get an n/2 point FFT.

    #rfftfreq produces a list of frequency bins, which requires calculation to produce
    #interpretable frequencies for BPM tracking. by plotting calculated bpm values,
    #the graph can be more easily read.

    #despite rfft producing an n/2 point fft, the calculation still uses n,
    #because the point spacing is still based on n points.

    # ((binNumber*samplingRate)/n)*60 produces a per minute rate.

    ffty = np.fft.rfft(y, len(y))
    freq = np.fft.rfftfreq(len(y), 0.05)
    freqX = [((i*Fs)/no_frames)*60 for i in range(len(freq))]

    plt.subplot(211)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude (Hz)")

    plt.plot(y)

    plt.subplot(212)
    plt.xlabel("Breaths Per Minute (BPM)")
    plt.ylabel("Amplitude (dB/Hz)")

    axes = plt.gca()
    axes.set_xlim([50, 100])

    plt.plot(freqX, np.abs(ffty))

    plt.show()

def shorttime(reader, subcarrier):

    scaled_csi = reader.csi_trace

    #Replace complex CSI with amplitude.

    no_frames, no_subcarriers, finalEntry = getCSI(scaled_csi)
    # hampelData = hampel(finalEntry, 30)
    # smoothedData = running_mean(hampelData, 20)
    y = finalEntry[subcarrier]
    n = no_frames

    Fs = 20

    fmin = 1
    fmax = 1.7

    y = bandpass(9, fmin, fmax, Fs, y)

    # f, t, Zxx = signal.stft(y, Fs, nperseg=2000, noverlap=1750)
    f, t, Zxx = signal.stft(y, Fs)

    #bin indices for the observed amplitude peak in each segment.
    Zxx = np.abs(Zxx)
    maxAx = np.argmax(Zxx, axis=0)

    freqs = []
    for i in maxAx:
        arc = f[i]
        if arc >= fmin and arc <= fmax:
            arc *= 60
            freqs.append(arc)
        else:
            freqs.append(None)

    bpms = []
    for freq in freqs:
        if freq != None:
            bpms.append(freq)

    print(bpms)
    print("Average HR: " + str(np.average(bpms)))

    #We're only interested in frequencies between 0.5 and 2.
    freq_slice = np.where((f >= fmin) & (f <= fmax))

    f = f[freq_slice]
    Zxx = Zxx[freq_slice,:][0]

    plt.pcolormesh(t, f*60, np.abs(Zxx))
    plt.plot(t, freqs, color="red", marker="x")

    plt.title('STFT Magnitude')
    # plt.ylabel('Frequency [Hz]')
    plt.ylabel('Heart Rate [BPM]')
    plt.xlabel('Time [sec]')
    plt.show()

#Averages the PSD measurements from every subcarrier after data preprocessing.
def beatsfilter(reader, Fs):
    scaled_csi = reader.csi_trace
    no_frames, no_subcarriers, finalEntries = getCSI(scaled_csi, metric="phasediff")

    sigs = []

    for x in range(no_subcarriers):
        finalEntry = finalEntries[x]
        # hampelData = hampel(finalEntry, 10, 5)
        # # detrended = dynamic_detrend(hampelData, 5, 3, 1.2, Fs)
        # # rehampeledData = hampel(detrended, 10, 0.1)

        # # hampelData = hampel(finalEntry, 10)
        # # runningMeanData = running_mean(hampelData, 20)

        # filtData = bandpass(7, 1, 1.5, Fs, hampelData)

        # hampelData = hampel(finalEntries[x], 5, 3)
        # runningMeanData = running_mean(hampelData, 20)
        # smoothedData = dynamic_detrend(runningMeanData, 5, 3, 1.2, 10)
        # doubleHampel = hampel(smoothedData, 10, 3)

        filtData = bandpass(7, 1.1, 1.4, Fs, finalEntry)
        
        for i in range(0, 70):
            filtData[i] = 0

        sigs.append(filtData)

    pxxs = []

    for data in sigs:
        f, Pxx_den = signal.welch(data, Fs)
        pxxs.append(Pxx_den)

    meanPsd = np.mean(pxxs, axis=0)
    # plt.plot(f*60, meanPsd)
    # plt.xlim([40, 100])
    # plt.show()

    return f[np.argmax(meanPsd)]*60

#Attempts to recreate the Spectral Stability subcarrier selection metric from CardioFi.

def specstabfilter(reader, Fs):

    scaled_csi = reader.csi_trace
    no_frames, no_subcarriers, finalEntries = getCSI(scaled_csi)

    #Using CSI phase difference data.

    stabilities = []

    for x in range(no_subcarriers):
        finalEntry = finalEntries[x]

        #CardioFi paper uses 100Hz uniformly sampled data, which may mean we need to use different
        #filter parameters. For now, we will copy them verbatim.
        #Currently the initial hampel filter is run using T1=0.5s t1=0.4
        #              dynamic_detrending is run with c=5 l=3 alpha=1.2 Fs=Fs
        #          the second hampel filter is run using T1=0.5s t1=0.1
        #          the bandpass filter is run at 5th order with a range of 1-2Hz.

        hampelData = hampel(finalEntry, 20)
        detrended = dynamic_detrend(hampelData, 5, 3, 1.2, Fs)
        rehampeledData = hampel(detrended, 20)

        filtData = bandpass(7, 1, 1.5, Fs, rehampeledData)

        #Spectral Stability section.
        #The spectral stability metric aims to score subcarriers based on the
        #variance of their heart rate estimations.

        #To do this, both the length of the data being used for estimations,
        #and a sliding window length must be selected.

        #While the dataLength should ideally be around 40s to mirror that used
        #in the CardioFi paper, this is difficult to replicate using the data
        #which was produced over the last few months.

        #Shorter data and window lengths are being experimented with but do not
        #appear to be working well. This is evidenced by the number of subcarriers
        #being selected using the metric, which is typically lower than that seen
        #in the CardioFi paper.

        #Notably, it is also difficult to take consistent ground truth heart rate
        #measurements over a 40 second period.

        wLength = 5*Fs
        dataLength = 10 *Fs
        windows = []
        position = 0

        #This sliding window system splits filtData into wLength-sized windows,
        #except for the final window which contains the remainder of the data.
        #Each sliding window has an overlap of 1 second (or Fs).

        while position < dataLength:
            if (position + wLength) > dataLength:
                window = filtData[position:]
            else:
                window = filtData[position:position+wLength]
            windows.append(window)
            position += wLength-Fs

        #PSD measurements are then taken for each window, and the variance of
        #these measurements are then collected to produce a final score for
        #this subcarrier.

        psds = []
        for window in windows:
            f, Pxx_den = signal.welch(window, Fs)
            fMax = f[np.argmax(Pxx_den)]
            psds.append(fMax)

        specStab = 1/np.var(psds)

        if specStab == np.inf:
            specStab = 0
        stabilities.append([x, specStab, filtData])

        # print("Sub: {} has spectral stability: {}".format(x, specStab))
        # print("Sub: {} mean pred: {}".format(x, np.mean(psds)*60))

    stabilities.sort(key=lambda x: x[1], reverse=True)
    bestStab = stabilities[0][1]
    news = [x for x in stabilities if x[1] > bestStab*0.2]

    print("Using {} subcarriers.".format(len(news)))
    pxxs = []
    for sub in news:
        data = sub[2]
        f, Pxx_den = signal.welch(data, Fs)
        pxxs.append(Pxx_den)

    #The mean PSD of the top subcarriers is then selected, with the
    #peak taken as the final heart rate estimation.

    meanPsd = np.mean(pxxs, axis=0)
    return f[np.argmax(meanPsd)]*60

def prepostfilter(reader):

    scaled_csi = reader.csi_trace

    no_frames = len(scaled_csi)
    no_subcarriers = scaled_csi[0]["csi"].shape[0]
    finalEntry = getCSI(scaled_csi)[15]

    stdev = running_stdev(finalEntry, 2)
    hampelData = hampel(finalEntry, 15)
    smoothedData = running_mean(hampelData.copy(), 15)

    y = finalEntry
    y2 = hampelData
    y3 = smoothedData

    x = list([x["timestamp"] for x in scaled_csi])

    plt.plot(x, y, label="Raw")
    plt.plot(x, y2, label="Hampel")
    # plt.plot(x, stdev, label="Standard Deviation")
    plt.plot(x, y3, "r", label="Hampel + Running Mean")

    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude (dBm)")
    plt.legend(loc="upper right")

    plt.show()

def plotAllSubcarriers(reader):

    scaled_csi = reader.csi_trace

    no_frames = len(scaled_csi)
    no_subcarriers = scaled_csi[0]["csi"].shape[0]
    finalEntry = getCSI(scaled_csi)

    # y = finalEntry[15]
    # y2 = hampelData
    # y3 = smoothedData

    # x = list([x["timestamp"] for x in scaled_csi])

    # plt.plot(x, y, label="Raw")
    # plt.plot(x, y2, label="Hampel")
    # # plt.plot(x, stdev, label="Standard Deviation")
    # plt.plot(x, y3, "r", label="Hampel + Running Mean")

    for x in finalEntry:
        plt.plot(np.arange(no_frames)/20, x)

    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude (dBm)")
    plt.legend(loc="upper right")

    plt.show()

def varianceGraph(reader):

    scaled_csi = reader.csi_trace

    no_frames = len(scaled_csi)
    no_subcarriers = scaled_csi[1]["csi"].shape[0]

    y = []

    finalEntry = getCSI(scaled_csi)

    for x in range(no_subcarriers):
        hampelData = hampel(finalEntry[x], 10)
        smoothedData = running_mean(hampelData, 25)
        y.append(variance(smoothedData))

    plt.xlabel("Subcarrier Index")
    plt.ylabel("Variance")

    plt.plot(y)
    plt.show()

def heatmap(reader):

    scaled_csi = reader.csi_trace
    no_frames, no_subcarriers, finalEntry = getCSI(scaled_csi, metric="amplitude")

    x = list([x["timestamp"] for x in scaled_csi])
    tdelta = (x[-1] - x[0]) / len(x)
    print(1/tdelta)

    # Fs = 100

    # ylimit = scaled_csi[no_frames-1]["timestamp"]
    # ylimit = no_frames/Fs

    limits = [0, max(x), 1, no_subcarriers]

    # for x in range(no_subcarriers):
    #     hampelData = hampel(finalEntry[x], 5, 3)
    #     runningMeanData = running_mean(hampelData, 20)
    #     # smoothedData = dynamic_detrend(runningMeanData, 5, 3, 1.2, 10)
    #     # doubleHampel = hampel(smoothedData, 10, 3)

    #     finalEntry[x] = bandpass(9, 1, 2, Fs, runningMeanData)
    #     # for i in range(0, 140):
    #     #     finalEntry[x][i] = 0
        
    fig, ax = plt.subplots()
    im = ax.imshow(finalEntry, cmap="jet", extent=limits, aspect="auto")

    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Amplitude (dBm)")

    plt.xlabel("Time (s)")
    plt.ylabel("Subcarrier Index")

    plt.title(reader.filename.split("/")[-1])

    plt.show()
    
def rawHeatmap(reader, reader2):

    scaled_csi = reader.csi_trace
    no_frames, no_subcarriers, finalEntry = getCSI(scaled_csi, metric="amplitude")
    # finalEntry = finalEntry - finalEntry.mean(axis=1)

    x = list([x["timestamp"] for x in scaled_csi])
    tdelta = (x[-1] - x[0]) / len(x)
    print(1/tdelta)

    limits = [0, max(x), 1, no_subcarriers]
        
    plt.subplot(1, 2, 1)
    plt.imshow(finalEntry, cmap="jet", extent=limits, aspect="auto")

    plt.xlabel("Time (s)")
    plt.ylabel("Subcarrier Index")

    plt.title("May: " + reader.filename.split("/")[-1])

    scaled_csi2 = reader2.csi_trace
    no_frames2, no_subcarriers2, finalEntry2 = getCSI(scaled_csi2, metric="amplitude")
    # finalEntry2 = finalEntry2 - finalEntry2.mean(axis=1)

    x2 = list([x["timestamp"] for x in scaled_csi2])
    tdelta2 = (x2[-1] - x2[0]) / len(x2)
    print(1/tdelta2)

    limits2 = [0, max(x2), 1, no_subcarriers2]
        
    plt.subplot(1, 2, 2)
    plt.imshow(finalEntry2, cmap="jet", extent=limits2, aspect="auto")
    # cbar2 = ax2.figure.colorbar(im2, ax=ax2)
    # cbar2.ax.set_ylabel("Amplitude (dBm)")

    plt.xlabel("Time (s)")
    plt.ylabel("Subcarrier Index")
    plt.colorbar()
    

    plt.title("August: " + reader2.filename.split("/")[-1])

    plt.show()

def main():
    partialPath = "./data/intel/activity/may/washingdishes_1590160990.dat"
    reader = BeamformReader(partialPath)

    partialPath2 = "./data/intel/activity/august/washingdishes_1597160719.dat"
    reader2 = BeamformReader(partialPath2)

    rawHeatmap(reader, reader2)
    # plotAllSubcarriers(reader)
    # prepostfilter(reader)
    # print(beatsfilter(reader, 10))
    # print(specstabfilter(reader, 20))
    # varianceGraph(reader)
    # fft(reader)
    # shorttime(reader, 20)

def hrTestSuite():

    # {test filename} {sampling rate} {average heart rate}
    tests = [
        ["dtest1", 20, 75],
        ["dtest2", 20, 63],
        ["dtest3", 20, 77],
        ["dtest4", 20, 88],

        ["etest1", 20, 82],
        ["etest2", 20, 79],
        ["etest3", 20, 86],
        ["etest4", 20, 81],

        ["gtest1", 20, 72],
        ["gtest2", 20, 55],
        ["gtest3", 20, 71],
        ["gtest4", 20, 80],

        ["htest1", 20, 67],
        ["htest2", 20, 67],
        ["htest3", 20, 81],
        ["htest4", 20, 79],

        # ["hometest1", 20, 86],
        # ["hometest2", 20, 81],
        # ["hometest3", 20, 80],
        # ["hometest4", 20, 75],
        # ["hometest5", 20, 85],
        # ["hometest6", 20, 87],
        # ["hometest7", 20, 95],
        # ["hometest8", 20, 90],
        # ["hometest9", 20, 88],
        # ["hometest10", 20, 93],
    ]

    estimationDiffs = []

    for [filename, Fs, bpm] in tests:
        # partialPath = "../sample_data/{}.dat".format(test[0])
        path = r"E:\\DataLab PhD Albyn 2018\\Code\\sample_data\\{}.dat".format(filename)

        # reader = BeamformReader(getPath(partialPath), x_antenna=0, y_antenna=0)
        reader = BeamformReader(path, x_antenna=0, y_antenna=0)
        # hrEstimation = specstabfilter(reader, Fs)
        hrEstimation = beatsfilter(reader, Fs)
        estErr = np.abs(hrEstimation-bpm)
        print("{0} result: {1:.2f}bpm".format(filename, hrEstimation))
        print("{0} estimation error: {1:.2f}bpm".format(filename, estErr))
        estimationDiffs.append(estErr)

    mean = np.nanmean(estimationDiffs)
    print("Mean Estimation Error: %2.f" % mean)

    median = np.nanmedian(estimationDiffs)
    print("Median Estimation Error: %2.f" % median)


if __name__ == "__main__":
    main()
    # hrTestSuite()