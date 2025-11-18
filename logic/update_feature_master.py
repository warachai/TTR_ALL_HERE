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
    feature_master_path = config.FEATURE_MASTER_FILE_PATH
    issue_path = config.MERGED_OUTPUT_FILE_NAME


    # Check if task_master_path exists
    try:
        df_feature_master = pd.read_csv(feature_master_path)
    except FileNotFoundError:
        print(f"Error: {feature_master_path} does not exist. Creating an empty DataFrame.")
        df_feature_master = pd.DataFrame()  # Create an empty DataFrame

    # Load the raw TTR item data
    df_raw_issue = pd.read_csv(issue_path)

    # Rename column 'Task_Name' to 'Feature_Name'
    df_raw_issue.rename(columns={'Task_Name': 'Feature_Name'}, inplace=True)


    # Select only the required columns from raw_ttr_item_path
    required_columns = ['Source', 'Program', 'Task_ID', 'Status', 'User_Name', 'Date_Time', 'Feature_Name', 'Improvement_Type']
    df_raw_issue = df_raw_issue[required_columns]
    

    # Merge the DataFrames on 'Program' and 'Feature_Name'
    if df_feature_master.empty:
        merged_df = df_raw_issue  # If task_master is empty, use raw_ttr_item directly
    else:
        merged_df = pd.merge(df_feature_master, df_raw_issue, on=['Program', 'Task_ID','Feature_Name'], how='left', suffixes=('', '_new'))

        # Check and update Merge_Action column
        def determine_merge_action(row):
            for col in required_columns:
                if col in ['Program', 'Task_ID','Feature_Name']:
                    continue  # Skip key columns
                if row[col] != row.get(f'{col}_new', row[col]):
                    return 'modified'
            return 'same'

        # Drop temporary columns
        merged_df.drop(columns=[f'{col}_new' for col in required_columns if f'{col}_new' in merged_df.columns], inplace=True)

    # Remove duplicate rows based on 'Program' and 'Task_Name', keeping the first occurrence
    merged_df = merged_df.drop_duplicates(subset=['Program', 'Task_ID','Feature_Name'], keep='last')

    

    # Save the merged DataFrame back to the task master file
    merged_df.to_csv(feature_master_path, index=False)
    print(f"Merged data saved to {feature_master_path}")

if __name__ == '__main__':
    exit(main())


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
    raw_ttr_item_path = config.TTR_ITEM_MASTER_FILE_PATH
    task_master_path = config.TASK_MASTER_FILE_PATH
    product_feature_path = config.PRODUCT_FEATURE_FILE_PATH

    df_product_feature = pd.read_csv(product_feature_path, usecols=['Program', 'Task_ID', 'Task_Name'])


    # Check if task_master_path exists
    try:
        df_task_master = pd.read_csv(task_master_path)
    except FileNotFoundError:
        print(f"Error: {task_master_path} does not exist. Creating an empty DataFrame.")
        df_task_master = pd.DataFrame()  # Create an empty DataFrame

    # Load the raw TTR item data
    df_raw_ttr_item = pd.read_csv(raw_ttr_item_path)

    # Select only the required columns from raw_ttr_item_path
    required_columns = ['Program', 'Task_ID', 'Status', 'User_Name', 'Date_Time', 'Task_Name', 'Improvement_Type', 'GAIN']
    df_raw_ttr_item = df_raw_ttr_item[required_columns]
    df_raw_ttr_item.rename(columns={'Task_Name': 'Feature_Name'}, inplace=True)

    # Merge the DataFrames on 'Program' and 'Task_Name'
    merged_df = pd.merge(df_task_master, df_raw_ttr_item, on=['Program', 'Task_ID'], how='left', suffixes=('', '_new'))

    # Drop temporary columns
    merged_df.drop(columns=[f'{col}_new' for col in required_columns if f'{col}_new' in merged_df.columns], inplace=True)

    # Remove duplicate rows based on 'Program' and 'Task_Name', keeping the first occurrence
    merged_df = merged_df.drop_duplicates(subset=['Program', 'Task_ID'], keep='first')

    merged_df =  pd.merge(merged_df,df_product_feature, on=['Program', 'Task_ID'], how='left', suffixes=('', '_new'))
    merged_df.drop(columns=[f'{col}_new' for col in required_columns if f'{col}_new' in merged_df.columns], inplace=True)

  # Save the merged DataFrame back to the task master file
    merged_df.to_csv(task_master_path, index=False)

    print(f"Merged data saved to {task_master_path}")

if __name__ == '__main__':
    exit(main())
