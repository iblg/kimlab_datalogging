import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_thermocouple_and_flow(data,
                               thermocouple_channel_names:list[str],
                               flow_channel_names: list[str],
                               thermocouple_function = None,
                               flow_function = None,
                               save_to_path: Path = None,
                               show_flag: bool = False,):
    """
    data: pd.DataFrame, the data to be plotted
    thermocouple_channel_names: list[str]
    By default, should be listed as 'T_thermocouple_AIN1', 'T_thermocouple_AIN2', etc.

    flow_channel_names: list[str]
    By default is probably something like 'AIN3', 'AIN4', etc
    """

    fig, ax = plt.subplots(nrows=2, sharex=True)
    for channel in thermocouple_channel_names:
        x = data['time']
        y = data[channel]
        y = thermocouple_function(y) if thermocouple_function is not None else y
        ax[0].plot(x, y, label=channel)

    for channel in flow_channel_names:
        x = data['time']
        y = data[channel]
        y = flow_function(y) if flow_function is not None else y
        ax[1].plot(x, y, label=channel)

    [axis.legend() for axis in ax]
    ax[1].set_xticks([data['time'].min(), data['time'].max()])

    if save_to_path is None:
        pass
    else:
        plt.savefig(save_to_path, bbox_inches='tight',
                    pad_inches=0.1, dpi=200)

    if show_flag:
        plt.show()
    return

def trim_thermocouple_temps(data: pd.DataFrame,
                            channels: tuple[str] = ('T_thermocouple_AIN0'),
                            min: float = 0, max: float = 100):
    """Should trim one data series or several"""
    for channel in channels:
        data[channel] = data[channel].where(data[channel] > min)
        data[channel] = data[channel].where(data[channel] < max)
    return data

def main():
    path = Path('/Users/ianbillinge/Documents/kimlab/projects/vuv/xanthydrol/'
                'measurements/2025_10_02/lab_nb/data/2025_10_02_lab_nb.csv')
    save_to_path = path.parent.parent / 'plots'
    save_to_path.mkdir(parents=True, exist_ok=True)
    save_to_path = save_to_path / 'thermocouple_and_flow.pdf'
    data = pd.read_csv(path)
    tcouple_channels = ('T_thermocouple_AIN0', 'T_thermocouple_AIN2')
    data = trim_thermocouple_temps(data, channels =tcouple_channels,
                                   min=0., max=100.)
    data = data.iloc[500:]
    plot_thermocouple_and_flow(data,
                               thermocouple_channel_names = tcouple_channels,
                               flow_channel_names = [],
                               save_to_path = save_to_path,)

    return


if __name__ == "__main__":
    main()
