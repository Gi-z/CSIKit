import matplotlib.pyplot as plt
import numpy as np
from filters import hampel, running_mean, running_stdev, bandpass
from matlab import db, variance
from read_bfee import BeamformReader
from scipy import fftpack, signal


class RealtimeGraph:

    def __init__(self, graphType="default"):
        plt.ion()
        self.fig, self.ax = plt.subplots()
        self.all_data = []
        self.graphType = graphType

        if graphType == "default":
            self.plotHampel, = plt.plot([], [], label="Hampel")
            #self.plotStd, = plt.plot([], [], label="Standard Deviation")
            self.plotAll, = plt.plot([], [], "r",label="Hampel + Running Mean")
            plt.legend(loc="upper right")

            plt.xlabel("Time (s)")
            plt.ylabel("Amplitude (dBm)")
        elif graphType == "livebutt":
            self.plotButt, = plt.plot([], [])
            
            plt.xlabel("Time (s)")
            plt.ylabel("Amplitude (dBm)")  
        elif graphType == "butter":
            self.plotButt, = plt.plot([], [])
            self.ax.set_xlim([30, 200])

            plt.xlabel("Beats Per Minute (BPM)")
            plt.ylabel("Amplitude (dBm/Hz)")
        elif graphType == "breath":
            self.plotBreath, = plt.plot([], [])
            self.ax.set_xlim([0, 40])

            plt.xlabel("Beats Per Minute (BPM)")
            plt.ylabel("Amplitude (dBm/Hz)")
        elif graphType == "heat":
            plt.xlabel("Time (s)")
            plt.ylabel("Subcarrier Index")
        elif graphType == "variance":
            self.plot, = plt.plot([], [], label="Variance")

            plt.xlabel("Subcarrier Index")
            plt.ylabel("Variance")

    def update(self, data):
        if self.graphType == "default":
            self.updateContents(data)
        elif self.graphType == "butter":
            self.updateButterworth(data)
        elif self.graphType == "breath":
            self.updateBreath(data)
        elif self.graphType == "livebutt":
            self.updateButterLive(data)
        elif self.graphType == "heat":
            self.updateHeat2(data)
        elif self.graphType == "variance":
            self.updateVariance(data)
        elif self.graphType == "justbeats":
            self.beatsfilter(data)

    def updateTimestamps(self):
        csi_trace = self.all_data
        time = [x["timestamp_low"] for x in csi_trace]

        timediff = (np.diff(time))*10e-7
        time_stamp = np.cumsum(timediff)

        csi_trace[0]["timestamp"] = 0
        for x in csi_trace[1:]:
            x["timestamp"] = time_stamp[csi_trace.index(x)-1]
      
        return True

    def getCSI(self, scaled_csi, metric="phasediff"):
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
                    finalEntries[y][x] = db(abs(scaled_entry[y][1][0]))

        return finalEntries

    def updateButterLive(self, data):
        self.all_data.append(data)
        self.updateTimestamps()

        if not self.updateTimestamps():
            self.all_data = self.all_data[:-1]
            return None
        scaled_csi = self.all_data

        no_frames = len(scaled_csi)
        no_subcarriers = scaled_csi[0]["csi"].shape[0]

        if no_frames < 50:
            return None

        #Replace complex CSI with amplitude.
        finalEntry = [db(abs(scaled_csi[x]["csi"][28][0][0])) for x in range(no_frames)]

        hampelData = hampel(finalEntry, 10)
        smoothedData = running_mean(hampelData, 30)
        y = smoothedData

        x = list([x["timestamp"] for x in scaled_csi])
        tdelta = (x[-1] - x[0]) / len(x)

        Fs = 1/tdelta
        y = bandpass(5, 1.0, 1.3, Fs, y)

        self.plotButt.set_xdata(x)
        self.plotButt.set_ydata(np.abs(y))

        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def updateButterworth(self, data):
        self.all_data.append(data)
        self.updateTimestamps()

        if not self.updateTimestamps():
            self.all_data = self.all_data[:-1]
            return None
        scaled_csi = self.all_data

        no_frames = len(scaled_csi)
        no_subcarriers = scaled_csi[0]["csi"].shape[0]

        if no_frames < 50:
            return None

        #Replace complex CSI with amplitude.
        finalEntry = [db(abs(scaled_csi[x]["csi"][15][0][0])) for x in range(no_frames)]

        hampelData = hampel(finalEntry, 10)
        smoothedData = running_mean(hampelData, 30)
        y = smoothedData

        x = list([x["timestamp"] for x in scaled_csi])
        tdelta = (x[-1] - x[0]) / len(x)

        Fs = 1/tdelta
        n = no_frames

        y = bandpass(5, 1.0, 1.3, Fs, y)

        ffty = np.fft.rfft(y, len(y))
        freq = np.fft.rfftfreq(len(y), tdelta)
        freqX = [((i*Fs)/n)*60 for i in range(len(freq))]

        self.plotButt.set_xdata(freqX)
        self.plotButt.set_ydata(np.abs(ffty))

        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def updateBreath(self, data):
        self.all_data.append(data)

        if not self.updateTimestamps():
            self.all_data = self.all_data[:-1]
            return None

        scaled_csi = self.all_data

        no_frames = len(scaled_csi)
        no_subcarriers = scaled_csi[0]["csi"].shape[0]

        if no_frames < 50:
            return None

        #Replace complex CSI with amplitude.
        finalEntry = [db(abs(scaled_csi[x]["csi"][15][1][0])) for x in range(no_frames)]

        hampelData = hampel(finalEntry, 10)
        smoothedData = running_mean(hampelData, 30)
        y = smoothedData

        y -= np.mean(y)
        x = list([x["timestamp"] for x in scaled_csi])
        tdelta = (x[-1] - x[0]) / len(x)

        Fs = 1/tdelta
        n = no_frames

        ffty = np.fft.rfft(y, len(y))
        freq = np.fft.rfftfreq(len(y), tdelta)
        freqX = [((i*Fs)/n)*60 for i in range(len(freq))]

        self.plotBreath.set_xdata(freqX)
        self.plotBreath.set_ydata(np.abs(ffty))

        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def updateContents(self, data):
        self.all_data.append(data)
        if not self.updateTimestamps():
            self.all_data = self.all_data[:-1]
            return None

        scaled_csi = self.all_data

        no_frames = len(scaled_csi)
        no_subcarriers = 30

        finalEntry = [db(abs(scaled_csi[x]["csi"][14][1][0])) for x in range(no_frames)] 

        x = list([x["timestamp"] for x in scaled_csi])
 
        #self.plotStand.set_xdata(x)
        #self.plotStand.set_ydata(finalEntry)

        hampelData = hampel(finalEntry, 20)
        #smoothedData = running_mean(hampelData.copy(), 15)

        self.plotHampel.set_xdata(x)
        self.plotHampel.set_ydata(hampelData)

        #self.plotAll.set_xdata(x)
        #self.plotAll.set_ydata(smoothedData)

        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def updateVariance(self, data):

        self.all_data.append(data)
        if not self.updateTimestamps():
            self.all_data = self.all_data[:-1]
            return None
        scaled_csi = self.all_data

        no_frames = len(scaled_csi)
        no_subcarriers = scaled_csi[0]["csi"].shape[0]

        y = []

        finalEntry = np.zeros((no_subcarriers, no_frames))
        hampelData = np.zeros((no_subcarriers, no_frames))
        smoothedData = np.zeros((no_subcarriers, no_frames))

        for x in range(no_subcarriers):
            finalEntry[x] = [db(abs(scaled_csi[y]["csi"][x][0][0])) for y in range(no_frames)]
            #hampelData = hampel(finalEntry[x].flatten(), 10)
            #smoothedData = running_mean(hampelData, 25)
            y.append(variance(finalEntry[x]))

        x = list(range(1, 31))

        self.plot.set_xdata(x)
        self.plot.set_ydata(y)

        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    # def updateHeat2(self, data):
    #     self.all_data.append(data)
    #     if not self.updateTimestamps():
    #         self.all_data = self.all_data[:-1]
    #         return None
    #     scaled_csi = self.all_data

    #     no_frames = len(scaled_csi)
    #     no_subcarriers = scaled_csi[0]["csi"].shape[0]
    #     ylimit = scaled_csi[no_frames-1]["timestamp"]

    #     if no_frames < 100:
    #         return None

    #     limits = [1, no_subcarriers, 0, ylimit]

    #     finalEntry = np.zeros((no_frames, no_subcarriers))

    #     #Replace complex CSI with amplitude.
    #     for y in range(no_subcarriers):
    #         for x in range(no_frames):
    #             scaled_entry = scaled_csi[x]["csi"]
    #             finalEntry[y][x] = db(abs(scaled_entry[y][0][0]))


    #     for j in range(no_subcarriers):
       
    #         sig = finalEntry[j] 
    #         #hampelData = hampel(sig, 10)
    #         #smoothedData = running_mean(sig, 30)
        
    #         y = sig.flatten()
    #         x = list([x["timestamp"] for x in scaled_csi])
    #         tdelta = (x[-1] - x[0]) / len(x)

    #         Fs = 1/tdelta
    #         n = no_frames
    #         y = bandpass(5, 1.0, 1.3, Fs, y)

    #         for x in range(70):
    #             y[x] = 0

    #         finalEntry[j] = y

    #     #x = subcarrier index
    #     #y = time (s)
    #     #z = amplitude (cBm)

    #     im = self.ax.imshow(finalEntry, cmap=plt.cm.gist_rainbow_r, extent=limits, aspect="auto")

    #     cbar = self.ax.figure.colorbar(im, ax=self.ax)
    #     cbar.ax.set_ylabel("Amplitude (dBm)", rotation=-90, va="bottom")

    #     self.ax.relim()
    #     self.ax.autoscale_view()
    #     self.fig.canvas.draw()
    #     self.fig.canvas.flush_events()

    def beatsfilter(self, data):
        self.all_data.append(data)
        scaled_csi = self.all_data
        no_frames = len(scaled_csi)

        if no_frames < 256:
            return None

        Fs = 10 

        no_subcarriers = scaled_csi[0]["csi"].shape[0]
        finalEntries = self.getCSI(scaled_csi)

        sigs = []

        for x in range(no_subcarriers):
            finalEntry = finalEntries[x].flatten()
            filtData = bandpass(7, 1, 1.5, Fs, finalEntry)
            
            for i in range(0, 70):
                filtData[i] = 0

            sigs.append(filtData)

        pxxs = []

        for data in sigs:
            f, Pxx_den = signal.welch(data, Fs)
            pxxs.append(Pxx_den)

        meanPsd = np.mean(pxxs, axis=0)
        print("Beats: %.2f" % float(f[np.argmax(meanPsd)]*60))
        self.all_data = []

    def updateHeat2(self, data):
        self.all_data.append(data)
        if not self.updateTimestamps():
            self.all_data = self.all_data[:-1]
            return None
        scaled_csi = self.all_data

        no_frames = len(scaled_csi)
        no_subcarriers = scaled_csi[0]["csi"].shape[0]
        ylimit = scaled_csi[no_frames-1]["timestamp"]

        if no_frames < 80:
            return None

        # limits = [1, no_subcarriers, 0, ylimit]
        limits = [0, ylimit, 1, no_subcarriers]

        finalEntry = np.zeros((no_subcarriers, no_frames))

        #Replace complex CSI with amplitude.
        for y in range(no_subcarriers):
            for x in range(no_frames):
                scaled_entry = scaled_csi[x]["csi"]
                finalEntry[y][x] = db(abs(scaled_entry[y][0][0]))

        for j in range(no_subcarriers):
            sig = finalEntry[j] 
            #hampelData = hampel(sig, 10)
            #smoothedData = running_mean(sig, 30)
        
            y = sig.flatten()
            y = bandpass(5, 1.0, 1.3, 20, y)

            for x in range(70):
                y[x] = 0

            finalEntry[j] = y

        #x = subcarrier index
        #y = time (s)
        #z = amplitude (cBm)

        if not hasattr(self, "im"):
            self.im = self.ax.imshow(finalEntry, cmap="jet", extent=limits, aspect="auto")
            cbar = self.ax.figure.colorbar(self.im, ax=self.ax)
            cbar.ax.set_ylabel("Amplitude (dBm)", rotation=-91, va="bottom") 
        else:
            self.im.set_array(finalEntry)
            self.im.set_extent(limits)

        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def updateHeat(self, data):
        self.all_data.append(data)
        if not self.updateTimestamps():
            self.all_data = self.all_data[:-1]
            return None
        scaled_csi = self.all_data

        no_frames = len(scaled_csi)
        no_subcarriers = scaled_csi[0]["csi"].shape[0]
        ylimit = scaled_csi[no_frames-1]["timestamp"]

        if no_frames < 10:
            return None

        limits = [1, no_subcarriers, 0, ylimit]

        finalEntry = np.zeros((no_frames, no_subcarriers))

        #Replace complex CSI with amplitude.
        for y in range(no_subcarriers):
            for x in range(no_frames):
                scaled_entry = scaled_csi[x]["csi"]
                finalEntry[x][y] = db(abs(scaled_entry[y][0][0]))

        #x = subcarrier index
        #y = time (s)
        #z = amplitude (cBm)

        finalEntry = finalEntry[::-1] 

        if not hasattr(self, "im"):
            self.im = self.ax.imshow(finalEntry, cmap=plt.cm.gist_rainbow_r, extent=limits, aspect="auto")
            cbar = self.ax.figure.colorbar(self.im, ax=self.ax)
            cbar.ax.set_ylabel("Amplitude (dBm)", rotation=-91, va="bottom") 
        else:
            self.im.set_array(finalEntry)
            self.im.set_extent(limits)

        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
