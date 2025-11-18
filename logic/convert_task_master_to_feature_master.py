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
    task_master_path = config.TASK_MASTER_FILE_PATH
    feat

    # Check if task_master_path exists
    try:
        df_task_master = pd.read_csv(task_master_path)
    except FileNotFoundError:
        print(f"Error: {task_master_path} does not exist. Creating an empty DataFrame.")
        exit(1)

    # Load the raw TTR item data
    df_raw_ttr_item = pd.read_csv(raw_ttr_item_path)

    # Select only the required columns from raw_ttr_item_path
    required_columns = ['Program', 'Task_ID', 'Status', 'User_Name', 'Date_Time', 'Task_Name', 'Improvement_Type', 'GAIN']
    df_raw_ttr_item = df_raw_ttr_item[required_columns]

    # Merge the DataFrames on 'Program' and 'Task_Name'
    if df_task_master.empty:
        merged_df = df_raw_ttr_item  # If task_master is empty, use raw_ttr_item directly
        merged_df['Merge_Action'] = 'new'  # Add MergeAction column with 'new'
    else:
        merged_df = pd.merge(df_task_master, df_raw_ttr_item, on=['Program', 'Task_Name'], how='left', suffixes=('', '_new'))

        # Check and update Merge_Action column
        def determine_merge_action(row):
            for col in required_columns:
                if col in ['Program', 'Task_Name']:
                    continue  # Skip key columns
                if row[col] != row.get(f'{col}_new', row[col]):
                    return 'modified'
            return 'same'

        merged_df['Merge_Action'] = merged_df.apply(determine_merge_action, axis=1)

        # Drop temporary columns
        merged_df.drop(columns=[f'{col}_new' for col in required_columns if f'{col}_new' in merged_df.columns], inplace=True)

    # Remove duplicate rows based on 'Program' and 'Task_Name', keeping the first occurrence
    merged_df = merged_df.drop_duplicates(subset=['Program', 'Task_Name'], keep='first')

    # Save the merged DataFrame back to the task master file
    merged_df.to_csv(task_master_path, index=False)

    print(f"Merged data saved to {task_master_path}")

if __name__ == '__main__':
    exit(main())
