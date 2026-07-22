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
    issue_path = config.MERGED_OUTPUT_PATH
    product_feature_path = config.PRODUCT_FEATURE_FILE_PATH

    df_product_feature = pd.read_csv(product_feature_path, usecols=['Program', 'Task_ID', 'Task_Name'])


    # Check if task_master_path exists
    try:
        df_feature_master = pd.read_csv(feature_master_path)
    except FileNotFoundError:
        print(f"Error: {feature_master_path} does not exist. Creating an empty DataFrame.")
        df_feature_master = pd.DataFrame()  # Create an empty DataFrame

    # Load the raw TTR item data
    df_raw_issue = pd.read_csv(issue_path)
    df_raw_issue = df_raw_issue[df_raw_issue["Source"].isin(["jira_issues", "DISC"])]

    # Rename column 'Task_Name' to 'Feature_Name'
    df_raw_issue.rename(columns={'Task_Name': 'Feature_Name'}, inplace=True)

    required_columns = ['Source', 'Program', 'Task_ID', 'Status', 'User_Name', 'Date_Time', 'Feature_Name', 'Improvement_Type', 'FixVersions']
    df_raw_issue = df_raw_issue[required_columns]

    update_cols = ['Status', 'User_Name', 'Feature_Name', 'FixVersions']

    keys = ['Program', 'Task_ID']

    merge_cols = keys + update_cols

    dest = df_feature_master.copy()
    dest = dest.merge(
        df_raw_issue[merge_cols],
        on=keys,
        how="left",
        suffixes=("", "_src"),
    )

    for col in update_cols:
        dest[col] = dest[f"{col}_src"].combine_first(dest[col])
        dest = dest.drop(columns=[f"{col}_src"])
    # Select only the required columns from raw_ttr_item_path

    key_df = dest[keys].drop_duplicates()
    new_rows = df_raw_issue.merge(
        key_df,
        on=keys,
        how="left",
        indicator=True
    )

    new_rows = new_rows[new_rows["_merge"] == "left_only"].drop(columns=["_merge"])

    # 3) CONCAT destination + new rows
    result = pd.concat([dest, new_rows], ignore_index=True)
 
    update_cols = ['Task_Name',]
    result =  pd.merge(result,df_product_feature, on=['Program', 'Task_ID'], how='left', suffixes=('', '_new'))
    for col in update_cols:
        result[col] = result[f"{col}_new"].combine_first(result[col])
        result = result.drop(columns=[f"{col}_new"])

    result = result.drop_duplicates(subset=['Program', 'Task_ID'], keep='last')
   

    # Save the merged DataFrame back to the task master file
    result.to_csv(feature_master_path, index=False)
    print(f"Merged data saved to {feature_master_path}")

if __name__ == '__main__':
    exit(main())

