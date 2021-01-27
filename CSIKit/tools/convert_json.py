from CSIKit import csi
import json

from ..reader import reader_selector

def generate_json(path):
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

    reader = reader_selector.get_reader(path)
    csi_data = reader.read_file(path)
    csi_frames = csi_data.frames

    json_str = json.dumps(csi_frames, default=default, indent=True)
    return json_str