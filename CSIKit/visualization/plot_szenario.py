"""
Classes to Plot a szenario belog different measurements
"""

from cmath import phase
from typing import Dict, List, Tuple
import os

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

from CSIKit.csi import IWLCSIFrame as CsiEntry
from CSIKit.visualization.graph import Graph, TupleGraph
from CSIKit.visualization.metric import Metric, TupleMetric
from CSIKit.reader.readers.read_bfee import IWLBeamformReader


class PlotableCSI():
    """
    to plot csiEntrys
    """

    def __init__(self, metric, graph):
        self._axes = None
        self._values_per_measurement: Dict[str, List] = {}
        self._curr_measurement = None
        self.metric = metric()
        self.graph = graph()

    def add_measurement(self, measurement_name: str):
        """ Mark the moment, if the next plots are of a different measurement"""
        self._curr_measurement = []
        self._values_per_measurement[measurement_name] = self._curr_measurement

    def notice(self, entry: CsiEntry):
        if self._curr_measurement is None:
            print(self._curr_measurement)
            raise Exception(
                "No measurement started yet. call self.add_measurement")
        self._curr_measurement.append(self.metric.notice(entry))

    def show(self):
        self.axes = plt.subplot()
        axes = self.axes
        self.graph.show(axes, self._values_per_measurement)
        axes.set_ylabel(f"{self.metric.get_name()}[{self.metric.get_unit()}]")
        axes.set_xlabel('measurement')


class SzenarioPlotter():
    """
    Plots different metrics of one szenario with multible measurements
    """

    def __init__(self, szenario_name: str,
                 plot_impls: List):
        self.szenario_name = szenario_name
        self.__measurements: Dict = {}
        self.__plot_implementations: List[PlotableCSI] = [
            PlotableCSI(metric, graph) for metric, graph in plot_impls]
        plt.rcParams.update(
            {'font.size': 22, 'font.family': "Liberation Serif"})

    def add_plot(self, metric: Metric, graph: Graph):
        """
        Adds PlotableCSI and give him all measurements of this szenario
        """
        plotable = PlotableCSI(metric, graph)
        for measurement_name in self.__measurements:
            plotable.add_measurement(measurement_name)
            entries = self.__measurements[measurement_name]

            for entry in entries:
                plotable.notice(entry)

        self.__plot_implementations.append(plotable)

    def add_measurement(self, name, data):
        """
        add new measurement and notice all plotables about the new data
        """
        if not isinstance(name, (str, int, float)):
            raise Exception(f"invalid input for name")
        if data and not isinstance(data[0], CsiEntry):
            raise Exception(f"invalid input for data. It is {type(data)}")
        self.__measurements[name] = data
        for plot_impl in self.__plot_implementations:
            plot_impl.add_measurement(name)
        for entry in data:
            if not isinstance(entry, CsiEntry):
                raise Exception(
                    f"unclean CSI Entrys. Should be type CsiEntry, but it is {type(isinstance(entry, CsiEntry))}")

            for plot_impl in self.__plot_implementations:
                plot_impl.notice(entry)

    def add_measurements(self, measurements: dict):
        """
        add measurements by passing a dict of name to entries:list
        """
        for measurement_name in measurements:
            data = measurements[measurement_name]
            self.add_measurement(measurement_name, data)

    @classmethod
    def _read_file(cls, path, filter_n_rx=True):
        """
        reads .dat file and returns csiEntries
        @filter_n_rx : default=True if to filter frames n_rx !=3
        retruns csiEntries:list
        """
        my_reader = IWLBeamformReader()
        csi_data = my_reader.read_file(path)

        # maybe you have to filter your entrys if not all rx are used
        csi_entrys = []
        if filter_n_rx:
            csi_entrys = [
                frame for frame in csi_data.frames if frame.n_rx == 3]
        else:
            csi_entrys = csi_data.frames
        return csi_entrys

    def add_measurement_file(self, name, path: str):
        """
        adds measurement by file
        """
        if not isinstance(name, (str, int, float)):
            raise Exception(f"invalid input for name")
        if not path and not os.path.exists(path):
            raise Exception(f"path {path} not exists")
        entries = self._read_file(path)
        self.add_measurement(name, entries)

    def add_measurements_files(self, name_path: dict):
        """
        adds measurements by passing a dict of name to path
        """
        if not name_path or not len(name_path):
            raise Exception("Nothing to add in dict")
        for name in name_path:
            path = name_path[name]
            self.add_measurement_file(name, path)

    def show(self, title=""):
        """
        shows the results of the plt of the different metrics
        """
        def mat_show(plot_impl: PlotableCSI):
            if len(title) > 0:
                plot_impl.axes.set_title(title)
            plt.show()

        self._plot(mat_show)

    def save(self,folder="./images"):
        """
        saves pdf of the plot at this szenarios
        It maight be happend that if you use this within ipynb of yupiter it show also.
        """
        def save_pdf(plot_impl: PlotableCSI):
            if not os.path.exists(folder):
                os.makedirs(folder)
            file_name = f"{plot_impl.metric.__class__.__name__}_{plot_impl.graph.__class__.__name__}"
            with PdfPages(f"./{folder}/{self.szenario_name}-{file_name}.pdf") as pdf:
                pdf.savefig(bbox_inches='tight')

        self._plot(save_pdf)

    def _plot(self, callback):
        """
        plots into a matplotlib axes
        """
        # if no plots spezified
        if not len(self.__plot_implementations) > 0:
            raise Exception("define PlotableCSI before show szenario")
        # if __measurements empty
        if not len(self.__measurements) > 0:
            raise Exception("define meassurments before show szenario")
        if not isinstance(self.__measurements, dict):
            raise Exception(
                f"__measurements should be type dict but it is {type(self.__measurements)}")

        for plot_impl in self.__plot_implementations:
            plt.figure(figsize=(5, 5))
            plot_impl.show()

            callback(plot_impl)
