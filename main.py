import argparse

from batch_graph import BatchGraph
from get_info import display_info

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSIKit: Parse and interpret CSI data.")

    parser.add_argument("--info", "-i", action="store_true", default=True, help="Display structural information about a given CSI file.")
    
    
    parser.add_argument("--graph", "-g", action="store_true", default=False, help="Visualise CSI data in a matplotlib graph.")
    
    
    parser.add_argument("--csv", "-c", action="store_true", default=False, help="Process CSI data into CSV format.")
    
    parser.add_argument("file", type=str, help="Path to CSI file.")

    args = parser.parse_args()
    # print(args)

    if args.graph:
        bg = BatchGraph(args.file)
        bg.heatmap()
    elif args.csv:
        print()
    elif args.info:
        display_info(args.file)