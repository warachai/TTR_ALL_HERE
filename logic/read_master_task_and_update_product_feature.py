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
    product_feature_path = config.PRODUCT_FEATURE_FILE_PATH

    # Load the task master data
    df_task_master = pd.read_csv(task_master_path, usecols=['Program', 'Task_ID', 'Task_Name'])

    # Prepare a list to store updated rows for product feature
    updated_rows = []

    # Iterate through each row in task master
    for _, row in df_task_master.iterrows():
        task_id_value = row['Task_ID']
        if pd.isna(task_id_value):
            continue  # Skip rows where Task_ID is NaN
        task_ids = str(task_id_value).split(',')  # Ensure Task_ID is treated as a string and split if it contains multiple IDs
        for task_id in task_ids:
            updated_row = {
                'Program': row['Program'],
                'Task_ID': task_id.strip(),
                'Task_Name': row['Task_Name']
            }
            updated_rows.append(updated_row)

    # Create a DataFrame for updated rows
    df_updated = pd.DataFrame(updated_rows)

    # Save the updated rows to product feature file
    df_updated.to_csv(product_feature_path, index=False)

    print(f"Updated product feature data saved to {product_feature_path}")

if __name__ == '__main__':
    exit(main())
