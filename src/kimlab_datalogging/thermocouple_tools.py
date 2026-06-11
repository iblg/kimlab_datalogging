from scipy.stats import zscore
import pandas as pd
import numpy as np


def remove_channel_outlier_by_zscore(data: pd.Series, threshold: float = 3, diff:bool=True) -> pd.Series:
    if diff:
        crit = data.diff()
    else:
        crit = data.copy()

    data = data[np.abs(zscore(crit)) < threshold]
    return data

def remove_outliers_from_channels_by_zscore(data: pd.Series, names: tuple[str], threshold: float = 3, diff:bool=True) -> pd.Series:
    for name in names:
        print(
            'Removing outliers from channels by zscore for channel {}'.format(
                name))

        print(data[name].dropna())
        data[name] = remove_channel_outlier_by_zscore(data[name], threshold=threshold, diff=diff)
        print(data[name].dropna())
    return data

def smooth_channel(data: pd.Series, window: int = 5) -> pd.Series:
    data = data.ewm(span=window).mean()
    return data

def smooth_channels(data: pd.Series, names: tuple[str], window: int = 5,) -> pd.Series:
    for name in names:
        data[name] = smooth_channel(data[name], window=window)
    return data

