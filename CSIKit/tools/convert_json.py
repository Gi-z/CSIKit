import json

from CSIKit.util.csitools import get_CSI
from CSIKit.reader import get_reader

def generate_json(path: str, metric: str="amplitude") -> str:
    """
        This function converts a csi_trace into the json format. It works for single entry or the whole trace.

        Parameters:
            path (str): Path to CSI file location.
    """
    def default(prop):
        if "complex" in str(type(prop)):
            return str(prop)
        if "numpy" in str(type(prop)):
            return prop.tolist()
        if "__dict__" in dir(prop):
            return prop.__dict__
        else:
            print("Prop has no __dict__ {}: \n {}".format(type(prop), prop))

    reader = get_reader(path)
    csi_data = reader.read_file(path)
    csi_matrix, no_frames, no_subcarriers = get_CSI(csi_data, metric)

    print("CSI Shape: {}".format(csi_matrix.shape))
    print("Number of Frames: {}".format(no_frames))
    print("Generating CSI {}...".format(metric))

    json_str = json.dumps(csi_matrix, default=default, indent=True)
    return json_str