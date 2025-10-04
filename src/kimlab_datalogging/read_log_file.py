import pandas as pd
from pathlib import Path


def get_rows_with_messages(data):
    rwm = data.dropna(axis='rows', subset=['message'])
    return rwm


def read_log_files_from_parent_dir(parent_dir: Path,
                                   exclude_files_with_substrings=None,
                                   rglob=False) -> pd.DataFrame:
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
    data = data.sort_values('time').reset_index()
    return data


def read_log_file(log_file_path):
    data = pd.read_csv(log_file_path)
    return data


def verboseprint(df, max_rows=None, max_cols=None, cols=None):
    with pd.option_context('display.max_rows', max_rows,
                           'display.max_columns',max_cols
                           ):
        if cols is None:
            print(df)
        else:
            print(df.loc[:, cols])


def main():
    p = ('/Users/ianbillinge/Documents/kimlab/projects/vuv/xanthydrol/'
         'measurements/2025_10_02/lab_nb')
    path = Path(p)
    data = read_log_files_from_parent_dir(parent_dir=path, rglob=True)
    # print(data)

    rwm = get_rows_with_messages(data)
    verboseprint(rwm, cols=['message',
                            'time'])
    return


if __name__ == "__main__":
    main()
