import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from kimlab_datalogging.processing_utils import ewma_fb
from iblg_matplotlib_tools.generate_figax import generate_figax
from iblg_matplotlib_tools.ib_cell_stylesheet import use_cell_style

use_cell_style()
def generate_and_format_figure(date):
    fig, ax, gs = generate_figax(figsize=(10, 8), nrows=3, ncols=1,
                                 sharex=True)

    [label.set_visible(False) for label in ax[0].get_xticklabels()]
    [label.set_visible(False) for label in ax[1].get_xticklabels()]
    myFmt = mdates.DateFormatter('%H:%M:%S')
    ax[-1].xaxis.set_major_formatter(myFmt) # comment this out to see fine detail in x axis
    ax[-1].text(0.95, 0.05, date, ha='right', va='bottom',
                transform=ax[-1].transAxes)

    return fig, ax, gs


def plot_temperature(df, T_bounds=(0, 100), fig=None, ax=None, gs=None,
                     x='datetime',
                     ylabel = 'Temperature (C)',
                     show_flag=False, plot_orionstar=False):
    if fig is None and ax is None and gs is None:
        fig, ax, gs = generate_figax()

    cols = [col for col in df.columns if col.startswith("T_thermocouple_AIN")]
    for col in cols:
        y = df[col].where(df[col] < T_bounds[1]).where(df[col] > T_bounds[0])
        if 'AIN0' in col:
            label = 'Reactor outlet'
            cc = '#85B09A'
        elif 'AIN2' in col:
            label = 'Lamp surface'
            cc = 'black'
        xx = df[x]
        yy = y
        common_plot_kwargs = dict(marker='.', linestyle='', color=cc)
        ax.plot(xx, yy, label=label, alpha=0.1, markeredgewidth=0.05, **common_plot_kwargs)
        ax.plot(xx, ewma_fb(yy, span=30), label=label + ' smoothed', **common_plot_kwargs)

    if plot_orionstar:
        ax.plot(df[x], df['T_orionstar'], label='T_orionstar')
    ax.set_ylabel(ylabel)
    ax.legend()
    if show_flag:
        plt.show()

def plot_DO(df, T_bounds=(0, 100), fig=None, ax=None, gs=None,
            show_flag=False,
            ylabel='Dissolved oxygen (mg/L)', ylim=(0,10)):
    if fig is None and ax is None and gs is None:
        fig, ax, gs = generate_figax()

    y = df['DO']
    ax.plot(df['datetime'], y)
    # ax.legend()
    ax.set_ylabel(ylabel)
    ax.set_ylim(*ylim)
    if show_flag:
        plt.show()
    return fig, ax, gs

def plot_flow_rate(df,
                   fig=None, ax=None, gs=None,
                   y_col = 'weight_smoothed',
                   ylabel='Flow Rate (mL/min)',
                   y_range=None,
    show_flag=False):
    if fig is None and ax is None and gs is None:
        fig, ax, gs = generate_figax()

    y = df[y_col]
    ax.plot(df['datetime'], y)
    # ax.legend()
    ax.set_ylabel(ylabel)
    if y_range is not None:
        ax.set_ylim(y_range)

    if show_flag:
        plt.show()
    return fig, ax, gs


