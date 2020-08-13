# Based on findings from journeys_initial_exploration, this script takes the combined cycle journey data as input
# and exports a cleansed version of the file, having applied various data cleansing steps to the data
# it also cleans station_ids

import numpy as np
import pandas as pd
import pickle

from pathlib import Path

credentials_file = Path('tfl_api_logger/apiCredentials.txt')
input_csv = Path('data/cycle_journeys/JourneysDataCombined.csv')
output_csv = Path('data/cycle_journeys/JourneysDataCombined_CLEANSED.csv')
output_lookup_dir = Path('data/cycle_journeys')
cn_pickle_dir = Path('data/tfl_lookups/bikepointid_to_commonname.p')
tn_pickle_dir = Path('data/tfl_lookups/bikepointid_to_terminal_name.p')


def fix_station_id(given_id, bp_to_name, tn_to_bp):
    """Some bikepoint IDs in the dataset are inconsistent. Generally this is because the terminal name has been
    given instead of the bikepoint ID. There are also a small number of hopeless cases.
     This function, for a given value:
      1. leaves values as is, if they match a bikepoint id, or are null
      2. replaces with the corresponding bikepoint id if it matches a terminal id
      3. replaces with -1 if none of the above
      """
    try:
        given_id = int(given_id)
    except ValueError:
        return -1

    if given_id in bp_to_name:
        return given_id
    elif np.isnan(given_id):
        return np.nan
    elif given_id in tn_to_bp:
        return tn_to_bp[given_id]
    else:
        return -1


def correct_start_date_errors(df):
    """ Overwrites start_date in the dataframe.
    Dataset contains start dates in 1900. In such cases, the complimenting end date column appears
    to be correct, as well as the duration. This function attempts to fix the implausible start dates.
    """
    df['Start Date'].where(
        # If start date is after 2012 we can trust it. If end date is before 2012, the fix won't work
        (df['Start Date'] >= '2012') | (df['End Date'] < '2012')
        # else: correct start_date using end date
        , df['End Date'] - pd.to_timedelta(df['Duration'], unit='s')
        , axis=0
        , inplace=True
     )
    return df


def correct_0_end_date_stations(df):
    """ overwrites 'End Date' and 'EndStation Id' and 'Duration' columns in the dataframe.
    In 2012/2013, missing end dates and missing end stations are encoded as 1970-01-01 and 0, respectively.
    This function replaces those cases with NaT and NaN
    """

    # Replace 1970 End Dates with NaT
    df['End Date'].where(
        df['End Date'] >= '2012'
        , pd.NaT
        , axis=0
        , inplace=True
    )

    df['Duration'].where(
        (df['End Date'] >= '2012') & (df['Duration'] >= 0)
        , np.NaN
        , axis=0
        , inplace=True
    )

    df['EndStation Id'].where(
        df['EndStation Id'] != 0
        , np.NaN
        , inplace=True
    )

    return df


def correct_suspect_enddates(df, tolerance=60):
    """ overwrites 'End Date' column in the dataframe.

    There appears to be an issue where end-dates are inconsistent with duration, especially when a journey passes over
    midnight.
    This function updates End Date to be start date + duration, if end_date - start_date is more than 'tolerance'
    seconds out from the stated duration
    """
    duration_from_dates = (df['End Date'] - df['Start Date']) / np.timedelta64(1, 's')
    diff = duration_from_dates - df['Duration']

    # where dif
    df['End Date'].where(
        abs(diff) <= tolerance | df['End Date'].isna()
        , df['Start Date'] + pd.to_timedelta(df['Duration'], unit='s')
        , axis=0
        , inplace=True
    )

    return df


transformations = [correct_start_date_errors, correct_0_end_date_stations, correct_suspect_enddates]


def main():
    with open(cn_pickle_dir, 'rb') as f:
        bp_to_name = pickle.load(f)
    with open(tn_pickle_dir, 'rb') as f:
        tn_to_bp = pickle.load(f)

    df_iter = pd.read_csv(input_csv, header=0, sep=',', parse_dates=['Start Date', 'End Date']
                          , dayfirst=True, infer_datetime_format=True, chunksize=1000000)
    mode, header = 'w+', True  # for first chunk
    for df_chunk in df_iter:
        # apply date transformations
        for f in transformations:
            df_chunk = f(df_chunk)
        # station fixes
        df_chunk['StartStation Id'] = df_chunk['StartStation Id'].apply(fix_station_id, args=(bp_to_name, tn_to_bp))
        df_chunk['EndStation Id'] = df_chunk['EndStation Id'].apply(fix_station_id, args=(bp_to_name, tn_to_bp))
        # save chunk
        df_chunk.to_csv(output_csv, mode=mode, index=False, header=header)
        mode, header = 'a', False  # all subsequent chunks
    print("Done with cleansing!")
    print()


if __name__ == '__main__':
    main()
