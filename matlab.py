from math import log10
import numpy as np

def dbinv(x, metric="pow"):
    return np.power(10, x/10)

def db(x, metric="pow"):
    return 10 * np.log10(x)

def variance(samples):
    overallMean = np.mean(samples)
    return sum(list(map(lambda x: (x-overallMean)**2, samples))) / (len(samples)-1)