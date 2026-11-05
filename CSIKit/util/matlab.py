import numpy as np

def dbinv(x: float) -> float:
    return np.power(10, x/10)

def db(x: float, metric: str="voltage") -> float:
    # Zero magnitudes (e.g. null subcarriers) give -inf; that's expected, so don't warn,
    # but only here rather than changing NumPy's error state for the whole process.
    with np.errstate(divide="ignore"):
        if metric == "voltage":
            return 20 * np.log10(x)
        elif metric == "pow":
            return 10 * np.log10(x)

def sqtwolog(x: float) -> float:
    return np.sqrt(2*np.log(len(x)))