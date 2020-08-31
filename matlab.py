import numpy as np

def dbinv(x, metric="pow"):
    return np.power(10, x/10)

def db(x, metric="pow"):
    if metric == "voltage":
        return 20 * np.log10(x)
    elif metric == "pow":
        return 10 * np.log10(x)