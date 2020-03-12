from filters import hampel, running_mean, running_stdev, dynamic_detrend
from read_bfee import BeamformReader
from matlab import db
from pathlib import Path
from scipy import fftpack, signal, stats

import matplotlib.pyplot as plt
import numpy as np
import os

def variance(samples):
    overallMean = np.mean(samples)
    return sum(list(map(lambda x: (x-overallMean)**2, samples))) / (len(samples)-1)

def getCSI(scaled_csi, metric="phasediff"):
    no_frames = len(scaled_csi)
    no_subcarriers = np.array(scaled_csi[0]["csi"]).shape[0]

    finalEntries = [np.zeros((no_frames, 1)) for x in range(no_subcarriers)]

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
                finalEntries[y][x] = db(abs(scaled_entry[y][1][0]))

    return finalEntries

def fft(reader):

    scaled_csi = reader.csi_trace

    no_frames = len(scaled_csi)
    no_subcarriers = scaled_csi[1]["csi"].shape[0]

    finalEntry = getCSI(scaled_csi)

    hampelData = hampel(finalEntry, 20)
    smoothedData = running_mean(hampelData, 30)
    y = smoothedData.flatten()
    y -= np.mean(y)

    x = list([x["timestamp"] for x in scaled_csi])
    tdelta = (x[-1] - x[0]) / len(x)

    Fs = 1/tdelta
    n = no_frames

    #rfft is a real Fast Fourier Transform, as we aren't interested in the imaginary parts.
    #as half of the points lie in the imaginary/negative domain, we get an n/2 point FFT.

    #rfftfreq produces a list of frequency bins, which requires calculation to produce
    #interpretable frequencies for BPM tracking. by plotting calculated bpm values,
    #the graph can be more easily read.

    #despite rfft producing an n/2 point fft, the calculation still uses n,
    #because the point spacing is still based on n points.

    # ((binNumber*samplingRate)/n)*60 produces a per minute rate.

    ffty = np.fft.rfft(y, len(y))
    freq = np.fft.rfftfreq(len(y), tdelta)
    freqX = [((i*Fs)/n)*60 for i in range(len(freq))]

    plt.subplot(211)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude (Hz)")

    plt.plot(x, y)

    plt.subplot(212)
    plt.xlabel("Breaths Per Minute (BPM)")
    plt.ylabel("Amplitude (dB/Hz)")

    axes = plt.gca()
    axes.set_xlim([0, 30])

    plt.plot(freqX, np.abs(ffty))

    plt.show()

def shorttime(reader, subcarrier):

    scaled_csi = reader.csi_trace

    no_frames = len(scaled_csi)
    no_subcarriers = scaled_csi[0]["csi"].shape[0]

    finalEntry = np.zeros((no_frames, 1))
    hampelData = np.zeros((no_frames, 1))
    smoothedData = np.zeros((no_frames, 1))

    #Replace complex CSI with amplitude.

    finalEntry = [db(abs(scaled_csi[x]["csi"][subcarrier][reader.x_antenna][reader.y_antenna])) for x in range(no_frames)]

    hampelData = hampel(finalEntry, 30)
    smoothedData = running_mean(hampelData, 20)
    y = smoothedData

    #Sampling at 100Hz.
    tdelta = 0.01
    x = list([x*tdelta for x in range(0, no_frames)])

    # Fs = 1/tdelta
    Fs = 100
    n = no_frames

    fmin = 0.7
    fmax = 2.3

    # y = y*10000

    b, a = signal.butter(3, [fmin/(Fs/2), fmax/(Fs/2)], "bandpass")
    y = signal.lfilter(b, a, y)

    f, t, Zxx = signal.stft(y, Fs, nperseg=2000, noverlap=1750)

    #bin indices for the observed amplitude peak in each segment.
    Zxx = np.abs(Zxx)
    maxAx = np.argmax(Zxx, axis=0)
    # for x in range(0, len(maxAx)):
    #     maxSpot = maxAx[x]
    #     Zxx[maxSpot][x] = 1

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

    no_subcarriers = np.array(scaled_csi[0]["csi"]).shape[0]
    finalEntries = getCSI(scaled_csi)

    stabilities = []

    for x in range(no_subcarriers):
        finalEntry = finalEntries[x].flatten()
        hampelData = hampel(finalEntry, 10, 0.4)
        detrended = dynamic_detrend(hampelData, 5, 3, 1.2, Fs)
        rehampeledData = hampel(detrended, 10, 0.1)

        b, a = signal.butter(6, [1/(Fs/2), 2/(Fs/2)], "bandpass")
        filtData = signal.lfilter(b, a, rehampeledData)

        # plt.plot(smoothedData, label="Smoothed")

        # plt.plot(finalEntry, label="Unfiltered")
        # plt.plot(hampelData, label="Hampeled")
        # plt.legend(loc="upper right")
        # plt.show()

        # plt.plot(hampelData, label="Hampeled")
        # plt.plot(detrended, label="Detrended")
        # plt.legend(loc="upper right")
        # plt.show()

        # plt.plot(detrended, label="Detrended")
        # plt.plot(rehampeledData, label="Rehampeled")
        # plt.legend(loc="upper right")
        # plt.show()

        # plt.plot(filtData, label="Filtered Data")
        # plt.plot(rehampeledData, label="Rehampeled")
        # plt.legend(loc="upper right")
        # plt.show()

        stabilities.append(filtData)

    pxxs = []
    for data in stabilities:
        f, Pxx_den = signal.welch(data, Fs)
        pxxs.append(Pxx_den)

    meanPsd = np.mean(pxxs, axis=0)
    return f[np.argmax(meanPsd)]*60

#Attempts to recreate the Spectral Stability subcarrier selection metric from CardioFi.

def specstabfilter(reader, Fs):

    scaled_csi = reader.csi_trace

    no_subcarriers = np.array(scaled_csi[0]["csi"]).shape[0]
    finalEntries = getCSI(scaled_csi)

    #Using CSI phase difference data.

    stabilities = []

    for x in range(no_subcarriers):
        finalEntry = finalEntries[x].flatten()

        #CardioFi paper uses 100Hz uniformly sampled data, which may mean we need to use different
        #filter parameters. For now, we will copy them verbatim.
        #Currently the initial hampel filter is run using T1=0.5s t1=0.4
        #              dynamic_detrending is run with c=5 l=3 alpha=1.2 Fs=Fs
        #          the second hampel filter is run using T1=0.5s t1=0.1
        #          the bandpass filter is run at 5th order with a range of 1-2Hz.

        hampelData = hampel(finalEntry, 10, 0.4)
        detrended = dynamic_detrend(hampelData, 5, 3, 1.2, Fs)
        rehampeledData = hampel(detrended, 10, 0.1)

        b, a = signal.butter(5, [1/(Fs/2), 1.3/(Fs/2)], "bandpass")
        filtData = signal.lfilter(b, a, rehampeledData)
        # filtData = filtData[100:]

        # plt.plot(finalEntry, label="Unfiltered")
        # plt.plot(hampelData, label="Hampeled")
        # plt.legend(loc="upper right")
        # plt.show()

        # plt.plot(hampelData, label="Hampeled")
        # plt.plot(detrended, label="Detrended")
        # plt.legend(loc="upper right")
        # plt.show()

        # plt.plot(detrended, label="Detrended")
        # plt.plot(rehampeledData, label="Rehampeled")
        # plt.legend(loc="upper right")
        # plt.show()

        # plt.plot(filtData, label="Filtered Data")
        # plt.plot(rehampeledData, label="Rehampeled")
        # plt.legend(loc="upper right")
        # plt.show()

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
        dataLength = 10*Fs
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

    #So far the error rate is not consistent, but is usually above +/-5bpm.

    meanPsd = np.mean(pxxs, axis=0)
    return f[np.argmax(meanPsd)]*60

def prepostfilter(reader):

    scaled_csi = reader.csi_trace

    no_frames = len(scaled_csi)
    no_subcarriers = scaled_csi[0]["csi"].shape[0]
    finalEntry = getCSI(scaled_csi)[15]

    stdev = running_stdev(finalEntry.flatten(), 2)
    hampelData = hampel(finalEntry.flatten(), 30)
    smoothedData = running_mean(hampelData.copy(), 30)

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
        hampelData = hampel(finalEntry[x].flatten(), 10)
        smoothedData = running_mean(hampelData, 25)
        y.append(variance(smoothedData))

    x = list(range(1, 31))

    plt.xlabel("Subcarrier Index")
    plt.ylabel("Variance")

    plt.plot(y)
    plt.show()

def heatmap(reader):

    scaled_csi = reader.csi_trace

    Fs = 20

    no_subcarriers = scaled_csi[0]["csi"].shape[0]
    no_frames = len(scaled_csi)
    # ylimit = scaled_csi[no_frames-1]["timestamp"]
    # print(ylimit)
    ylimit = no_frames/Fs

    limits = [0, ylimit, 1, no_subcarriers]

    finalEntry = getCSI(scaled_csi, metric="amplitude")

    #x = subcarrier index
    #y = time (s)
    #z = amplitude (dBm)

    # for x in range(no_subcarriers):
    #     hampelData = hampel(finalEntry[x].flatten(), 20, 0.4)
    #     runningMeanData = running_mean(hampelData, 20)
    #     # smoothedData = dynamic_detrend(hampelData, 5, 3, 1.2, 20)
    #     # doubleHampel = hampel(smoothedData, 10, 0.4)
    #     # finalEntry[x] = hampel(finalEntry[x].flatten(), 10)

    #     b, a = signal.butter(5, [1/10, 1.3/10], btype="band")
    #     finalEntry[x] = signal.lfilter(b, a, runningMeanData)

    #     for i in range(0, 400):
    #         finalEntry[x][i] = 0

    for x in range(no_subcarriers):
        hampelData = hampel(finalEntry[x].flatten(), 20, 0.4)
        smoothedData = dynamic_detrend(hampelData, 5, 3, 1.2, 20)
        doubleHampel = hampel(smoothedData, 10, 0.4)

        b, a = signal.butter(5, [1/10, 1.3/10], btype="band")
        finalEntry[x] = signal.lfilter(b, a, doubleHampel)

        for i in range(160, no_frames):
            finalEntry[x][i] = 0

    fig, ax = plt.subplots()
    im = ax.imshow(finalEntry, cmap="jet", extent=limits, aspect="auto")

    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Amplitude (dBm)")

    plt.xlabel("Time (s)")
    plt.ylabel("Subcarrier Index")

    plt.show()

def getPath(partialPath):
    basePath = Path(__file__).parent
    return (basePath / partialPath).resolve()

def main():
    partialPath = "../sample_data/dtest4.dat"
    reader = BeamformReader(getPath(partialPath), x_antenna=0, y_antenna=0)

    scaled_csi = reader.csi_trace

    # heatmap(reader)
    plotAllSubcarriers(reader)
    # prepostfilter(reader)
    # beatsfilter(reader)
    # print(specstabfilter(reader, 20))
    # varianceGraph(reader)
    # fft(reader)
    # shorttime(reader)

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
    ]

    estimationDiffs = []

    for test in tests:
        partialPath = "../sample_data/{}.dat".format(test[0])
        reader = BeamformReader(getPath(partialPath), x_antenna=0, y_antenna=0)

        scaled_csi = reader.csi_trace
        hrEstimation = specstabfilter(reader, test[1])
        estErr = np.abs(hrEstimation-test[2])
        print("{} estimation error: {}bpm".format(test[0], estErr))
        estimationDiffs.append(estErr)

    median = np.nanmedian(estimationDiffs)
    print("Median Estimation Error: " + str(median))


if __name__ == "__main__":
    main()
    # hrTestSuite()

#Works for dtest1-4, etest1-4, ftest3.
# def oldbeatsfilter(reader, Fs):

#     scaled_csi = reader.csi_trace

#     #Grabbing the +128 subcarriers, under the assumption these
#     #are from the Rx antenna.

#     no_frames = len(scaled_csi)
#     no_subcarriers = np.array(scaled_csi[0]["csi"]).shape[0]
#     # no_subcarriers = 70
#     # x = list([x["timestamp"] for x in scaled_csi])
#     # tdelta = (x[-1] - x[0]) / len(x)

#     # Fs = 1/tdelta

#     finalEntries = [np.zeros((no_frames, 1)) for x in range(no_subcarriers)]

#     for x in range(no_frames):
#         scaled_entry = scaled_csi[x]["csi"]
#         for y in range(no_subcarriers):
#             finalEntries[y][x] = db(abs(scaled_entry[y][0][0]))

#     #We have finalEntries[subcarriers][frames].
#     #Now we want to find subcarrier variance and clip a threshold.

#     stabilities = []

#     for x in range(no_subcarriers):
#         finalEntry = finalEntries[x].flatten()
#         variation = stats.variation(finalEntry)

#         if not np.isnan(variation) and variation < 0.5:
#             hampelData = hampel(finalEntry, 20)
#             smoothedData = running_mean(hampelData, 20)

#             b, a = signal.butter(3, [1/(Fs/2), 2/(Fs/2)], "bandpass")
#             filtData = signal.lfilter(b, a, smoothedData.flatten())

#             #Removed the first 50 values to cut out the spike.
#             #Average HR should be 70.

#             wLength = 1*Fs
#             N = np.mod(len(filtData), wLength)
#             windows = np.array_split(filtData, N)

#             psds = []
#             for window in windows:
#                 f, Pxx_den = signal.welch(window, Fs)
#                 fMax = f[np.argmax(Pxx_den)]
#                 psds.append(fMax)

#             specStab = 1/np.var(psds)
#             print("Sub: {} has spectral stability: {}".format(x, specStab))
#             stabilities.append({"sub": x, "stability": specStab, "data": filtData})

#     stabilities.sort(key=lambda x: x["stability"], reverse=True)

#     bestStab = stabilities[0]["stability"]
#     news = [x for x in stabilities if x["stability"] >= (bestStab/100)*20]

#     print("Using {} subcarriers.".format(len(news)))
#     pxxs = []
#     for sub in news:
#         filtData = sub["data"]
#         f, Pxx_den = signal.welch(filtData, Fs)
#         pxxs.append(Pxx_den)

#     meanPsd = np.mean(pxxs, axis=0)
#     return f[np.argmax(meanPsd)]*60

#     # plt.plot(f*60, meanPsd, alpha=0.5)

#     # plt.xlabel("Estimated Heart Rate [bpm]")
#     # plt.ylabel("PSD [V**2/Hz]")
#     # plt.legend(loc="upper right")
#     # plt.show()