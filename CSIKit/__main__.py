import argparse

from .batch_graph import BatchGraph
from .convert_csv import generate_csv
from .get_info import display_info

def main():
    parser = argparse.ArgumentParser(description="CSIKit: Parse and interpret CSI data.")

    parser.add_argument("--info", "-i", action="store_true", default=True, help="Display structural information about a given CSI file.")
    
    parser.add_argument("--graph", "-g", action="store_true", default=False, help="Visualise CSI data in a matplotlib graph.")
    parser.add_argument("--graph_type", dest="graph_type", default="heatmap", help="Select the graph type for visualisation: [heatmap, subcarrier_filter, all_subcarriers]. (Default: heatmap)")
    
    parser.add_argument("--csv", "-c", action="store_true", default=False, help="Process CSI data into CSV format.")
    parser.add_argument("--csv_dest", dest="dest", default="output.csv", help="Choose a destination for the output CSV file. (Default: output.csv)")

    parser.add_argument("file", type=str, help="Path to CSI file.")

    args = parser.parse_args()

    if args.graph:
        bg = BatchGraph(args.file)
        if args.graph_type == "heatmap":
            bg.heatmap()
        elif args.graph_type == "all_subcarriers":
            bg.plotAllSubcarriers()
        elif args.graph_type == "subcarrier_filter":
            bg.prepostfilter()
        else:
            print("Graph type '{}' not supported.".format(args.graph_type))
    elif args.csv:
        generate_csv(args.file, args.dest)
    elif args.info:
        display_info(args.file)

if __name__ == "__main__":
    main()