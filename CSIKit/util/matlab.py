import numpy as np
np.seterr(divide="ignore")

def dbinv(x: float) -> float:
    return np.power(10, x/10)

def db(x: float, metric: str="voltage") -> float:
    if metric == "voltage":
        return 20 * np.log10(x)
    elif metric == "pow":
        return 10 * np.log10(x)

def sqtwolog(x: float) -> float:
    return np.sqrt(2*np.log(len(x)))