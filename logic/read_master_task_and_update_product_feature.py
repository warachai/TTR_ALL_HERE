#!/usr/bin/env python3

import os
import sys

# Dynamically add the parent directory to the system path to locate config.py
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import config
import pandas as pd  # Ensure pandas is imported
import re


JIRA_PROJECTS = {'SUMMIT':'SUMMIT', 'MARLIN': 'MARLINCT', 'MARLIN BP': 'MBP', 'DORADO': 'DORADO', 'TSR':'TSR'}
def getProjectNameFromProgram(Program):
    if Program in JIRA_PROJECTS.values():
        return JIRA_PROJECTS[Program]
    else:
        return Program
   

TASK_ID_PATTERN = re.compile(r'[A-Za-z]+-\d+')  # Pattern: PREFIX-DIGITS e.g. FWSD-6603
TASK_ID_PATTERN_DIGIT = re.compile(r'\d+')  # Pattern: PREFIX-DIGITS e.g. FWSD-6603
TASK_ID_PATTERN_DISC_DIGIT = re.compile(r'CR\d+')  # Pattern: PREFIX-DIGITS e.g. FWSD-6603

def convertTaskID(program: str, task_id_value: str) -> str:
    """Normalize a raw task id string into the pattern PREFIX-DIGITS.

    - Uppercases input
    - Strips trailing punctuation (/,;.)
    - Extracts first matching substring like FWSD-6603
    - Returns empty string if no match (caller can skip)
    """
    task_id_value = task_id_value.upper().strip()
    task_id_final = task_id_value
    if task_id_value is None:
        return ""
    raw = str(task_id_value)
    # Remove common trailing separators
    raw = raw.rstrip('/;.,')
    m = TASK_ID_PATTERN.search(raw)
    if m:
        task_id_final = m.group(0)  # fixed incorrect indexing, use group(0)

    else:
        m = TASK_ID_PATTERN_DISC_DIGIT.search(raw)
        if m:
            task_id_final = m.group(0)
        else:
            m = TASK_ID_PATTERN_DIGIT.search(raw)
            if m:
                prefix = getProjectNameFromProgram(program)
                task_id_final = f"{prefix}-{m.group(0)}"     
    
    print(f"Converted raw Task ID '{task_id_value}' to normalized Task ID '{task_id_final}'")
    return task_id_final

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

        # Normalize Task_ID field: it may contain multiple IDs separated by commas, spaces or newlines.
        # If the value is already a list/tuple, iterate it directly; otherwise split with regex.
        if isinstance(task_id_value, (list, tuple)):
            raw_ids = [str(x) for x in task_id_value]
        else:
            raw_ids = re.split(r'[\n,]+', str(task_id_value).strip())  # split on any whitespace or comma

        # Filter out empty strings
        task_ids = [tid for tid in raw_ids if tid]

        for task_id in task_ids:
            updated_row = {
                'Program': row['Program'],
                'Task_ID': task_id.strip(),
                'Task_ID_NRM': convertTaskID(row['Program'], task_id.strip()),
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
