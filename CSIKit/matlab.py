import numpy as np

def dbinv(x):
    return np.power(10, x/10)

def db(x, metric="voltage"):
    if x == 0:
        return -np.inf

    if metric == "voltage":
        return 20 * np.log10(x)
    elif metric == "pow":
        return 10 * np.log10(x)