# import glob
# import os
# import sys
# import time
#
# from tqdm import tqdm
#
# from CSIKit.reader import IWLBeamformReader, NEXBeamformReader
# from CSIKit.util import csitools
#
# def run_iwl_test(directory):
#
#     if not os.path.exists(directory):
#         print("Test directory does not exist.")
#         exit(1)
#
#     start_time = time.time()
#
#     print("Starting performance test.")
#
#     file_data = []
#     processing_times = []
#
#     all_files = glob.glob(directory+"\*\*.dat", recursive=True)
#
#     print("{} files identified.".format(len(all_files)))
#
#     my_reader = IWLBeamformReader()
#
#     for file in tqdm(all_files):
#         file_start_time = time.time()
#
#         csi_data = my_reader.read_file(file)
#         if len(csi_data.frames) > 0:
#             csi_matrix, _, _ = csitools.get_CSI(csi_data)
#             file_data.append(csi_matrix)
#
#             file_end_time = time.time()
#             processing_times.append(file_end_time - file_start_time)
#
#     end_time = time.time()
#     total_time = int(end_time - start_time)
#
#     avg_file_time = round(sum(processing_times)/len(processing_times), 2)
#
#     print("Average file processing time: {}".format(avg_file_time))
#
# def run_nex_test(directory):
#
#     if not os.path.exists(directory):
#         print("Test directory does not exist.")
#         exit(1)
#
#     start_time = time.time()
#
#     print("Starting performance test.")
#
#     file_data = []
#     processing_times = []
#
#     all_files = glob.glob(directory+"\*.pcap", recursive=True)
#
#     print("{} files identified.".format(len(all_files)))
#
#     my_reader = NEXBeamformReader()
#
#     for file in tqdm(all_files):
#         file_start_time = time.time()
#
#         csi_data = my_reader.read_file(file)
#         if len(csi_data.frames) > 0:
#             csi_matrix, _, _ = csitools.get_CSI(csi_data)
#             file_data.append(csi_matrix)
#
#             file_end_time = time.time()
#             processing_times.append(file_end_time - file_start_time)
#
#     end_time = time.time()
#     total_time = int(end_time - start_time)
#
#     avg_file_time = round(sum(processing_times)/len(processing_times), 2)
#
#     print("Average file processing time: {}".format(avg_file_time))