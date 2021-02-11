import math
from math import pi
import statistics
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np





class Graph:
    @classmethod
    def show(cls, axes, values_per_measurement):
        raise Exception("Not implemented function show")


class TupleGraph:
    pass


class PlotBox(Graph):
    @classmethod
    def show(cls, axes, values_per_measurement):

        data = list(values_per_measurement.values())
        labels = list(values_per_measurement.keys())

        if all(isinstance(k, int) for k in labels):  # if name is metric
            width = max(list(values_per_measurement.keys())) / \
                (2*len(list(values_per_measurement.keys())))
            axes.boxplot(data, positions=labels, labels=labels,  widths=width)

        else:
            width = 0.5
            axes.boxplot(data, labels=labels, widths=width)

            ind = np.arange(1, len(values_per_measurement)+1)
            axes.set_xticks(ind)
            axes.set_xticklabels(
                tuple(values_per_measurement.keys()), rotation=45, ha="right")
        mini = min({min(ar) for ar in data})
        maxi = max({max(ar) for ar in data})
        if maxi > 0 and mini > 0:
            axes.set_ylim(bottom=0)

        elif maxi < 0 and mini < 0:
            axes.set_ylim(top=0)


class PlotCandle(Graph):
    def __init__(self):
        super().__init__()
        self.plot_wick = True

    @classmethod
    def _calc_average(_cls, values_per_measurement):
        averages = {}
        for mes_name in values_per_measurement.copy():
            values = values_per_measurement[mes_name]
            averages[mes_name] = (sum(values)/len(values))
        return averages

    @classmethod
    def _calc_std_errs(cls, values_per_measurement):
        """returns standard diviation of each measurement """
        val_per_meas = values_per_measurement.copy()
        std_errs = {}
        for name in val_per_meas:
            std_errs[name] = statistics.stdev(val_per_meas[name])

        return std_errs

    @classmethod
    def _calc_confidence_diff(cls, variance, interval=0.95):
        """ Retruns the  +- confidenz delta of the meassrements"""
        INTERVALS = {
            0.90: 1.645,
            0.95: 1.96,
            0.98: 2.326,
            0.99: 2.576
        }
        if not interval in INTERVALS:
            raise Exception(f"invalid intervall {interval}")

        confidenz_errors = {}
        for name in variance:
            std_err = math.sqrt(variance[name])
            confidenz = INTERVALS[interval] * \
                (std_err / math.sqrt(len(variance[name])))
            confidenz_errors[name] = confidenz
        return confidenz_errors

    @classmethod
    def show(cls, axes, values_per_measurement, plot_wick=True):

        if all(isinstance(k, int) for k in values_per_measurement.keys()):  # if name is metric
            width = max(list(values_per_measurement.keys())) / \
                (2*len(list(values_per_measurement.keys())))
            #width = 4
            # for name in self._values_per_measurement: # for each measurement
            cls._plot_candle(axes, values_per_measurement,
                             width, plot_wick=plot_wick)

        else:  # else plot by name
            width = 0.4
            cls._plot_candle(axes, values_per_measurement,
                             width, plot_wick=plot_wick)
            ind = np.arange(len(values_per_measurement))
            # plot unique text at the center of each candle
            axes.set_xticks(ind)
            axes.set_xticklabels(
                tuple(values_per_measurement.keys()), rotation=45, ha="right")

    @classmethod
    def _plot_candle(cls, axes, values_per_measurement, width=4, color="#008000", x_offset=0, plot_wick=True):
        averages = cls._calc_average(values_per_measurement)
        if len(values_per_measurement) == 1:
            plot_wick = False
        if plot_wick:
            std_errors = cls._calc_std_errs(values_per_measurement)
        # confidences = cls._calc_confidence_diff(self._values_per_measurement)
        wick_width = 4

        if all(isinstance(k, int) for k in values_per_measurement.keys()):  # if name is metric

            # for name in self._values_per_measurement: # for each measurement
            x_arr = values_per_measurement.keys()

            if x_offset != 0:
                x_arr = [i+x_offset for i in x_arr]  # add offset to x plot
            if plot_wick:
                axes.bar(x_arr, averages.values(), width=width, yerr=std_errors.values(
                ), error_kw=dict(linewidth=wick_width), color=color)
            else:
                axes.bar(x_arr, averages.values(), width=width,
                         error_kw=dict(linewidth=wick_width), color=color)
        else:  # else plot by name
            ind = np.arange(len(values_per_measurement))
            ind = [i+x_offset for i in ind]  # add offset to x plot

            if plot_wick:
                axes.bar(ind, averages.values(), width=width, yerr=std_errors.values(
                ), error_kw=dict(linewidth=wick_width), color=color)
            else:
                axes.bar(ind, averages.values(), width=width,
                         error_kw=dict(linewidth=wick_width), color=color)


class PlotCandleTuple(TupleGraph, PlotCandle):
    """
    Abstract class to plot group of bars by datatype tuple
    """

    def __init__(self):
        super().__init__()
        self._values_per_measurement: Dict[str, Tuple] = {}
    COLORS = ['#008000', 'red',  'blue']

    @classmethod
    def show(cls, axes, values_per_measurement, plot_wick=True):
        axes.set_autoscalex_on(True)
        # gets the size of the contained tuple
        tuple_size = len(list(values_per_measurement.values())[0][0])

        if all(isinstance(k, int) for k in values_per_measurement.keys()):  # if name is metric
            width = (max(list(values_per_measurement.keys())) /
                     (2*len(list(values_per_measurement.keys()))))/tuple_size
            # for name in self._values_per_measurement: # for each measurement

            for tuple_i in range(tuple_size):
                cls._plot_candle(axes, cls._get_measurement_by_tuple_index(values_per_measurement, tuple_i), width, x_offset=(
                    tuple_i-1)*width, color=cls.COLORS[tuple_i], plot_wick=plot_wick)

        else:  # else plot by name
            width = 0.8 / tuple_size

            # plot each bar of group per tuple
            for tuple_i in range(tuple_size):
                cls._plot_candle(axes, cls._get_measurement_by_tuple_index(values_per_measurement, tuple_i), width, x_offset=(
                    tuple_i-1)*width, color=cls.COLORS[tuple_i], plot_wick=plot_wick)
            # unique label per candle group
            ind = np.arange(len(values_per_measurement))
            axes.set_xticks(ind)
            axes.set_xticklabels(
                tuple(values_per_measurement.keys()), rotation=45, ha="right")

    @classmethod
    def _get_measurement_by_tuple_index(cls, values_per_measurement, tuple_index):
        """
        this function returns a "normal" measurement dict like used at CandlePlot to reuse the CandlePlot._plot_candle()
        returns Dict[str, list[int]]
        """
        measurements = values_per_measurement.copy()
        result = {}
        for name in measurements:
            measurement = measurements[name]
            result[name] = [i[tuple_index] for i in measurement]

        return result


class PlotCandleTuple_Phase(PlotCandleTuple):
    @classmethod
    def show(cls, axes, values_per_measurement, plot_wick=False):  # set wick false
        super().show(axes, values_per_measurement, plot_wick=plot_wick)
        axes._axes.set_ylim((0, pi))


class ColorMap(Graph):
    @classmethod
    def show(cls, axes, values_per_measurement):
        
        for measur_name in values_per_measurement:
            axes = plt.subplot()
            measur_data = values_per_measurement[measur_name]
            
            amplitude_per_sub = []
            for csi_matrix in  measur_data: # plot first 30 csi entrys
                amplitudes = [abs(sub[0]) for sub in csi_matrix]
                amplitude_per_sub.append(amplitudes)
            print(np.shape(amplitude_per_sub))
            amplitude_per_sub = np.matrix(np.array(amplitude_per_sub))
            print(np.shape(amplitude_per_sub))
            axes.pcolormesh(amplitude_per_sub, cmap=plt.cm.gist_rainbow_r, rasterized=True)
            #plt.show()
            #axes = plt.subplot()

