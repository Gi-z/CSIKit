from math import log10
import numpy as np

def dbinv(x):
    return np.power(10, x/10)

def db(x, metric="voltage"):
    if metric == "voltage":
        return 10 * np.log10(x)
    elif metric == "pow":
        return 20 * np.log10(x)

def variance(samples):
    overallMean = np.mean(samples)
    return sum(list(map(lambda x: (x-overallMean)**2, samples))) / (len(samples)-1)