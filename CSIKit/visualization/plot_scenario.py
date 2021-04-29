# Credit: tweigel-dev https://github.com/tweigel-dev

"""
Classes to Plot a scenario belong different measurements
"""
from typing import Dict, List
import os

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from CSIKit.csi import IWLCSIFrame as CsiEntry
from CSIKit.visualization.graph import Graph, TupleGraph, PlotColorMap
from CSIKit.visualization.metric import Metric, TupleMetric, MatrixMetric
from CSIKit.reader import IWLBeamformReader

class PlottableCSI():
    """
    to plot csiEntries
    """

    def __init__(self, metric, graph):
        # If metric and graph does not match : raise
        if  issubclass(metric, TupleMetric) ^ issubclass(graph,TupleGraph):
            raise Exception(
                f"""
                    both should have the same output, but only on is Tuple 
                    Metric:{metric.__name__} 
                    Graph:{graph.__name__}
                    isTuple: {issubclass(metric, TupleMetric)} ^ {issubclass(graph,TupleGraph)}
                """)
        if issubclass(metric, MatrixMetric) ^ issubclass(graph,PlotColorMap):
            raise Exception(
                f"""
                    both should have the same output, but only on is Graph 
                    Metric:{metric.__name__} 
                    Graph:{graph.__name__}
                    isTuple: {issubclass(metric, MatrixMetric)} ^ {issubclass(graph,PlotColorMap)}
                """)

        self._values_per_measurement: Dict[str, List] = {}
        self._curr_measurement = None
        self._figure = None
        self.metric = metric()
        self.graph = graph(self.metric)

    def add_measurement(self, measurement_name: str):
        """ Mark the moment, if the next noticed data are of a different measurement"""
        self._curr_measurement = []
        self._values_per_measurement[measurement_name] = self._curr_measurement

    def notice(self, entry: CsiEntry):
        if self._curr_measurement is None:
            print(self._curr_measurement)
            raise Exception(
                "No measurement started yet. call self.add_measurement")
        self._curr_measurement.append(self.metric.notice(entry))

    def _plot(self):
        self._figure = plt.figure()
        axes_list = self.graph.plot(self._values_per_measurement)
        #{self._figure.add_subplot(ax) for ax in axes_list}
        
    def show(self):
        self._plot()
        self._figure.show()

    def save(self, folder, prefix=""):
        self._plot()
        # prefix = f"{prefix}-"
        # if not os.path.exists(folder):
        #     os.makedirs(folder)
        # file_name = f"{self.metric.__class__.__name__}_{self.graph.__class__.__name__}"
        # path = f"./{folder}/{prefix}{file_name}.pdf".replace(" ","")
        # with PdfPages(path) as pdf:
        #     pdf.savefig(self._figure, bbox_inches='tight')

class ScenarioPlotter():
    """
    Plots different metrics of one scenario with multiple measurements
    """

    def __init__(self, scenario_name: str,
                 plot_impls: List):
        self.scenario_name = scenario_name
        self.__measurements: Dict = {}
        self.__plot_implementations: List[PlottableCSI] = [
            PlottableCSI(metric, graph) for metric, graph in plot_impls]
        plt.rcParams.update(
            {'font.size': 22, 'font.family': "Liberation Serif"})

    def add_plot(self, metric: Metric, graph: Graph):
        """
        Adds PlottableCSI and give him all measurements of this scenario
        """
        plottable = PlottableCSI(metric, graph)
        for measurement_name in self.__measurements:
            plottable.add_measurement(measurement_name)
            entries = self.__measurements[measurement_name]

            for entry in entries:
                plottable.notice(entry)

        self.__plot_implementations.append(plottable)

    def add_measurement(self, name, data):
        """
        add new measurement and notice all plottables about the new data
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
                    f"unclean CSI Entries. Should be type CsiEntry, but it is {type(isinstance(entry, CsiEntry))}")

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

        # maybe you have to filter your entries if not all rx are used
        csi_entries = []
        if filter_n_rx:
            csi_entries = [
                frame for frame in csi_data.frames if frame.n_rx == 3]
        else:
            csi_entries = csi_data.frames
        return csi_entries

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
        shows the results of the plot of the different metrics
        """
        self._is_scenario_vaild()
        {plottable.show() for  plottable in self.__plot_implementations}

    def save(self, folder="./images"):
        """
        saves pdf of the plot at this scenarios
        It might be happened that if you use this within ipynb of jupiter it show also.
        """
        self._is_scenario_vaild()
        {plottable.save(folder, prefix=self.scenario_name) for  plottable in self.__plot_implementations}

    def _is_scenario_vaild(self):
        """
        plots into a matplotlib axes
        """
        # if no plots specified
        if not len(self.__plot_implementations) > 0:
            raise Exception("define PlottableCSI before show scenario")
        # if __measurements empty
        if not len(self.__measurements) > 0:
            raise Exception("define measurements before show scenario")
        if not isinstance(self.__measurements, dict):
            raise Exception(
                f"__measurements should be type dict but it is {type(self.__measurements)}")

        return True