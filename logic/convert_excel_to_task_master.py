#!/usr/bin/env python3

import os
import sys

# Dynamically add the parent directory to the system path to locate config.py
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import config
import pandas as pd  # Ensure pandas is imported

def main():
    # Read the CSV files
    raw_ttr_item_path = config.MERGED_OUTPUT_PATH
    task_master_path = config.TASK_MASTER_FILE_PATH


    # Check if task_master_path exists
    try:
        df_task_master = pd.read_csv(task_master_path)
    except FileNotFoundError:
        print(f"Error: {task_master_path} does not exist. Creating an empty DataFrame.")
        df_task_master = pd.DataFrame()  # Create an empty DataFrame

    # Load the raw TTR item data
    df_raw_ttr_item = pd.read_csv(raw_ttr_item_path)
    df_raw_ttr_item = df_raw_ttr_item[df_raw_ttr_item['Source'].isin(['excel_import', ])]

    # Select only the required columns from raw_ttr_item_path
    required_columns = ['Source','Program', 'Task_ID', 'Status', 'User_Name', 'Date_Time', 'Task_Name', 'Improvement_Type', 'GAIN']
    df_raw_ttr_item = df_raw_ttr_item[required_columns]

    update_cols = ['Source', 'Task_ID', 'Status', 'User_Name', 'Date_Time', 'Improvement_Type', 'GAIN']

    keys = ['Program', 'Task_Name']

    merge_cols = keys + update_cols

    dest = df_task_master.copy()
    dest = dest.merge(
        df_raw_ttr_item[merge_cols],
        on=keys,
        how="left",
        suffixes=("", "_src"),
    )

    for col in update_cols:
        dest[col] = dest[f"{col}_src"].combine_first(dest[col])
        dest = dest.drop(columns=[f"{col}_src"])
    # Select only the required columns from raw_ttr_item_path

    key_df = dest[keys].drop_duplicates()
    new_rows = df_raw_ttr_item.merge(
        key_df,
        on=keys,
        how="left",
        indicator=True
    )
    new_rows = new_rows[new_rows["_merge"] == "left_only"].drop(columns=["_merge"])

    # 3) CONCAT destination + new rows
    result = pd.concat([dest, new_rows], ignore_index=True)

    result = result.drop_duplicates(subset=['Program', 'Task_Name'], keep='last')
    # Save the merged DataFrame back to the task master file
    result.to_csv(task_master_path, index=False)

    print(f"Merged data saved to {task_master_path}")

if __name__ == '__main__':
    exit(main())
