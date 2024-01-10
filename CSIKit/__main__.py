import argparse

def main():
    parser = argparse.ArgumentParser(description="CSIKit: Parse and interpret CSI data.")

    parser.add_argument("--info", "-i", action="store_true", default=True, help="Display structural information about a given CSI file.")

    parser.add_argument("--scaled", dest="scaled", action="store_true", default=False, help="Apply rescaling to CSI based on established AGC reversal via gain or RSSI.")
    parser.add_argument("--filter_mac", dest="filter_mac", default=None, help="Filter a specific CSI stream for a given MAC address.")

    parser.add_argument("--graph", "-g", action="store_true", default=False, help="Visualise CSI data in a matplotlib graph.")
    parser.add_argument("--graph_type", dest="graph_type", default="heatmap", help="Select the graph type for visualisation: [heatmap, subcarrier_filter, all_subcarriers]. (Default: heatmap)")
    
    parser.add_argument("--csv", "-c", action="store_true", default=False, help="Process CSI data into CSV format.")
    parser.add_argument("--csv_dest", dest="csv_dest", default="output.csv", help="Choose a destination for the output CSV file. (Default: output.csv)")
    parser.add_argument("--csv_metric", dest="csv_metric", default="amplitude", help="Choose the extracted CSI metric: amplitude, phase (Default: amplitude)")

    parser.add_argument("--json", "-j", action="store_true", default=False, help="Process CSI data into JSON format.")
    parser.add_argument("--json_dest", dest="json_dest", default="output.json", help="Choose a destination for the output JSON file. (Default: output.json)")
    parser.add_argument("--json_metric", dest="json_metric", default="amplitude", help="Choose the extracted CSI metric: amplitude, phase (Default: amplitude)")

    parser.add_argument("--npz", action="store_true", default=False, help="Process CSI data into npz format.")
    parser.add_argument("--npz_dest", dest="npz_dest", default="output.npz", help="Choose a destination for the output npz file. (Default: output.npz)")
    parser.add_argument("--npz_metric", dest="npz_metric", default="amplitude", help="Choose the extracted CSI metric: amplitude, phase (Default: amplitude)")

    parser.add_argument("file", type=str, help="Path to CSI file.")

    args = parser.parse_args()

    if args.graph:
        from CSIKit.tools.batch_graph import BatchGraph

        bg = BatchGraph(args.file, args.scaled, args.filter_mac)
        if args.graph_type == "heatmap":
            bg.heatmap()
        elif args.graph_type == "sumsqrssi":
            bg.sumsqrssi()
        elif args.graph_type == "all_subcarriers":
            bg.plotAllSubcarriers()
        elif args.graph_type == "subcarrier_filter":
            bg.prepostfilter()
        else:
            print("Graph type '{}' not supported.".format(args.graph_type))
    elif args.csv:
        from CSIKit.tools.convert_csv import generate_csv

        generate_csv(args.file, args.csv_dest, args.csv_metric)
    elif args.json:
        from CSIKit.tools.convert_json import generate_json

        json_str = generate_json(args.file, args.json_metric)
        with open(args.json_dest, "w+") as file:
            file.write(json_str)
        print("File written to: {}".format(args.json_dest))
    elif args.npz:
        from CSIKit.tools.convert_npz import generate_npz
        
        generate_npz(args.file, args.npz_dest, args.npz_metric)
    elif args.info:
        from CSIKit.tools.get_info import display_info

        display_info(args.file, args.scaled, args.filter_mac)
    

if __name__ == "__main__":
    main()