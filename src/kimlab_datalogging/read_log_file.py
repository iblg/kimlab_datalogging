import pandas as pd
from pathlib import Path
from datetime import datetime


def get_rows_with_messages(data):
    rwm = data.dropna(axis='rows', subset=['message'])
    return rwm


def read_log_files_from_parent_dir(
        parent_dir: Path,
        exclude_files_with_substrings=None,
        rglob=False,
        time_format: str = '%Y/%m/%d, %H:%M:%S.%f',
        save_to_path: Path = None) -> pd.DataFrame:
    if rglob:
        files = list(parent_dir.rglob("*.csv"))
    else:
        files = list(parent_dir.glob("*.csv"))

    if exclude_files_with_substrings is None:
        pass
    else:
        files = [file for file in files if search_string not in file.name
                 for search_string in exclude_files_with_substrings]

    data = [read_log_file(file) for file in files]
    data = pd.concat(data, axis='rows')

    data['time'] = pd.to_datetime(data['time'], format=time_format)
    data = data.sort_values('time')
    data = data.reset_index()

    data['dt'] = data['time'] - data['time'].min()
    data['dt'] = data['dt'].dt.total_seconds()
    # Note: the data.dt has nothing to do with the 'dt' column.
    # Just a coincidence of Pandas's notation.
    if save_to_path is None:
        pass
    else:
        save_to_path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(save_to_path, index=False)

    return data


def read_log_file(log_file_path):
    data = pd.read_csv(log_file_path)
    return data


def verboseprint(df, max_rows=None, max_cols=None, cols=None):
    with pd.option_context('display.max_rows', max_rows,
                           'display.max_columns', max_cols
                           ):
        if cols is None:
            print(df)
        else:
            print(df.loc[:, cols])


def main():
    p = ('/Users/ianbillinge/Documents/kimlab/projects/vuv/xanthydrol/'
         'measurements/2025_10_02/lab_nb/from_import')
    path = Path(p)
    path_out = path.parent / 'data' / '2025_10_02_lab_nb.csv'
    data = read_log_files_from_parent_dir(parent_dir=path, rglob=True,
                                          save_to_path=path_out)
    # print(data)
    print(path_out)
    rwm = get_rows_with_messages(data)
    verboseprint(rwm, max_rows=100, cols=['message', 'time', 'dt'])
    return


if __name__ == "__main__":
    main()
