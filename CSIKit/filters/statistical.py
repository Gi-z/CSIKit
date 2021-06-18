import numpy as np
import pandas as pd

def running_mean(x: np.array, N: int) -> np.array:
    return pd.Series(x).rolling(window=N, min_periods=1, center=True).mean().to_numpy()

def running_stdev(x: np.array, N: int) -> np.array:
    return pd.Series(x).rolling(window=N, min_periods=1, center=True).std().to_numpy()

def running_variance(x: np.array, N: int) -> np.array:
    return pd.Series(x).rolling(window=N, min_periods=1, center=True).var().to_numpy()
