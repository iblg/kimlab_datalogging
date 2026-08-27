import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import linregress
from pathlib import Path

def get_flow_rate_at_timestamp(
        df,
        time,
        span,
        plot_flag: bool = True,
        before_flag: bool = True
    ):
    df = filter_at_timestamp(df, time, span, before=True) # before flag mean
    df['dt'] = df['dt'].astype('float')
    ycol = df['weight_smoothed']
    fit_result = linregress(df['dt'], df['weight_smoothed'])

    if plot_flag:
        plot_param_at_timestamp(df['dt'], df['weight_smoothed'],
                                ylabel='Mass on scale (g)',
                                fitresult=fit_result)
        plt.show()
        plt.close()

    flow_rate = fit_result.slope
    d_flow_rate = fit_result.stderr


    return flow_rate, d_flow_rate

def get_DO_at_timestamp(df, time, span, plot_flag=True):

    df = filter_at_timestamp(df, time, span)
    DO = df['DO'].mean()
    d_DO = df['DO'].std()
    if plot_flag:
        plot_param_at_timestamp(df['datetime'], df['DO'],
                                ylabel='Dissolved oxygen (mg/L)')
        plt.show()
        plt.close()

    return DO, d_DO

def get_metadata_from_path(path: Path) -> dict:
    md = pd.read_csv(path)
    md = md.to_dict("list")
    return md

def process_all_from_date(date,
                          metadata: dict|Path,
                          data_dir = Path('/Users/ianbillinge/Library/'
                                          'CloudStorage/'
                                          'OneDrive-YaleUniversity/kimlab/vuv/'
                                          'datalogging/processing'),
                          t_span='00:05:00',
                          save_path=None,
                          plot_samples_flag=True,
                          print_messages_flag=True,
                          ):
    if isinstance(metadata, dict):
        pass
    elif isinstance(metadata, Path):
        print('We\'ve got a path!')
        metadata = get_metadata_from_path(metadata)
        print('Heres the metadata:')
        print(metadata)
    else:
        print('You passed metadata that was not a dict or path to a datasheet')
        raise TypeError

    times = metadata['timestamp']

    data = read_logs_from_date(data_dir, date)

    print(f'Data from {date}:')
    print(data.info())

    messages = data.where(~data['message'].isna())
    messages = messages.dropna(axis='index', how='all')

    if print_messages_flag:
        print('\nPrinting messages:')
        with(pd.option_context('display.max_rows', None)):
            print(messages[
                      ['datetime', 'message']
                  ])
    data = process_do_column(data)
    data = get_weight_from_scale(data)

    data = filter_unphysical_temps(data, threshold=-9000)

    if save_path is None:
        pass
    else:
        print(f'Writing to {save_path}')
        data.to_csv(save_path)
        messages_path = save_path.with_name(f'{date}_messages.csv')

        print('Writing messages to {}'.format(messages_path))
        messages.to_csv(messages_path)

    # GET INFO FROM TIMES
    if 'manual_flow_rates' in metadata:
        flow_rate = metadata['manual_flow_rates']
        d_flow_rate = metadata['d_manual_flow_rates']
    else:
        pairs = [
            get_flow_rate_at_timestamp(data, t, t_span,
                                       plot_flag=plot_samples_flag
                                       ) for t in times
        ]
        flow_rate, d_flow_rate = zip(*pairs)

    pairs = [get_DO_at_timestamp(data, t, t_span,
                                 plot_flag=plot_samples_flag) for t in times]
    DO, d_DO = zip(*pairs)

    pairs = [get_temp_at_timestamp(data, t, t_span, col='T_thermocouple_AIN0',
                                   plot_flag=plot_samples_flag) for t in times]
    T, d_T = zip(*pairs)
    pairs = [get_temp_at_timestamp(data, t, t_span, col='T_thermocouple_AIN2',
                                   plot_flag=plot_samples_flag) for t in times]
    T_lamp, d_T_lamp = zip(*pairs)

    sample_info = pd.DataFrame(
        {'timestamp': metadata['timestamp'], 'reactor': metadata['reactor'],
         'light': metadata['light'],
         'DO': DO, 'd_DO': d_DO,
         'flow_rate': flow_rate, 'd_flow_rate': d_flow_rate,
         'T_outlet': T, 'd_T_outlet': d_T,
         'T_lamp': T_lamp, 'd_T_lamp': d_T_lamp
         }, index=times)
    return data, sample_info


def get_temp_at_timestamp(df, time, span, col='T_thermocouple_AIN0',
                          plot_flag=True):

    df = filter_at_timestamp(df, time, span)
    try:
        T = df[col].mean()
        d_T = df[col].std()
    except KeyError as ke:
        print(ke)
        T, d_T = -9999, -9999

    if plot_flag:
        try:
            plot_param_at_timestamp(df['datetime'], df[col],
                                    ylabel='Temperature (C)')
            plt.show()
            plt.close()
        except KeyError as ke:
            pass
    return T, d_T

def filter_unphysical_temps(data, threshold=-273):
    try:
        data.loc[data['T_thermocouple_AIN0'] < threshold, 'T_thermocouple_AIN0'] = np.nan
        data.loc[data['T_thermocouple_AIN2'] < threshold, 'T_thermocouple_AIN2'] = np.nan
    except KeyError as ke:
        print(ke)
    return data

def plot_param_at_timestamp(x,y, ylabel=None, fitresult=None):
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(x,y)
    ax.set_ylabel(ylabel)
    if fitresult is not None:
        ax.plot(x, x*fitresult.slope + fitresult.intercept, color='r')
    return fig, ax

def process_do_column(data: pd.DataFrame) -> pd.DataFrame:

    DO = data['DO']
    DO = DO.str.strip('(')
    split_data = DO.str.split(',', expand=True)
    data['DO'] = split_data.iloc[:,0].astype(float)
    data['T_orionstar'] = split_data.iloc[:,3].astype(float)

    return data

def ewma_fb(df_column, span):
    ''' Apply forwards, backwards exponential weighted moving average (EWMA) to df_column. '''
    # Forwards EWMA.
    fwd = pd.Series.ewm(df_column, span=span).mean()
    # Backwards EWMA.
    bwd = pd.Series.ewm(df_column[::-1],span=10).mean()
    # Add and take the mean of the forwards and backwards EWMA.
    stacked_ewma = np.vstack(( fwd, bwd[::-1] ))
    fb_ewma = np.mean(stacked_ewma, axis=0)
    return fb_ewma

def filter_at_timestamp(df, time, span, before=False):
    date = df['datetime'].dt.date.iloc[0]
    time = pd.Timestamp(time).time()
    start_time = pd.Timestamp.combine(date, time)
    end_time = start_time + pd.Timedelta(span)

    if before:
        start_time = start_time - pd.Timedelta(span)
        end_time = end_time - pd.Timedelta(span)

    df = df.loc[df['datetime'] >= start_time]
    df = df.loc[df['datetime'] <= end_time]
    return df


def read_logs_from_date(
        root: Path,
        pattern: str, *,
        datetime_col_out="datetime",
        timestamp_candidates=("timestamp", "time")) -> pd.DataFrame:

    files = sorted(root.rglob(f"*{pattern}*.csv"))
    if not files:
        return pd.DataFrame()

    # Read all CSVs, create a single normalized datetime column, and drop the source time column.
    # This avoids keeping both "timestamp" and "time" (big file-size win).
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, low_memory=False)
            # pick whichever timestamp column exists in this file
            ts_col = next((c for c in timestamp_candidates if c in df.columns),
                          None)
            if ts_col is not None:
                dt = pd.to_datetime(df[ts_col], errors="coerce")
                df = df.drop(columns=[ts_col])
                df.insert(0, datetime_col_out, dt)

            dfs.append(df)
        except pd.errors.EmptyDataError:
            print(f"File {f} is empty. Skipping.")



    out = pd.concat(dfs, ignore_index=True, copy=False)

    return out



def get_weight_from_scale(df,
                          y_col='flow rate voltage',
                          t_col='datetime',
                          ):

    data = df
    data = data.where(data[y_col].notnull(), np.nan).dropna(axis='index',
                                                            how='all')
    df['t_flow_rate'] = data[t_col]
    df['weight'] = data[y_col]

    rolling_median = data[y_col].rolling(window=5, center=True).median()

    threshold = 10
    is_spike = (data[y_col] - rolling_median).abs() > threshold
    data[y_col] = data[y_col].where(~is_spike, np.nan)
    df['weight_smoothed'] = data[y_col]
    df['weight_smoothed'] = ewma_fb(df['weight_smoothed'], 12)
    return df

def flow_rate_2026_05_18(sett):
    fr = 0.02784978 * sett + -0.08641522
    d_fr = 0.00206699
    return fr, d_fr