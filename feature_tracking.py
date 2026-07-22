#!/usr/bin/env python3
"""
CSV Merge Utility

This script merges jira_issues.csv and WW2619.csv files by selecting specific columns
and adding a source identifier column to track the origin of each row.
"""

import csv
import os


def merge_csv_files(jira_file, ww_file, output_file):
    """
    Merge two CSV files by selecting specific columns and adding a source identifier.
    
    Args:
        jira_file (str): Path to the jira_issues.csv file
        ww_file (str): Path to the WW2619.csv file
        output_file (str): Path to the output merged CSV file
    """
    merged_data = []
    
    # Define output columns (unified schema)
    # Source, Program, Task_ID, Status, User_Name, Date_Time, Task_Name, Improvement_Type
    fieldnames = ['Source', 'Program', 'Task_ID', 'Status', 'User_Name', 'Date_Time', 'Task_Name', 'Improvement_Type']
    
    # Read from jira_issues.csv
    # Columns: Project, Key, Status, Assignee, Created, Summary, Improvement Type
    print(f"Reading {jira_file}...")
    with open(jira_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        jira_count = 0
        for row in reader:
            merged_data.append({
                'Source': 'jira_issues',
                'Program': row.get('Project', ''),
                'Task_ID': row.get('Key', ''),
                'Status': row.get('Status', ''),
                'User_Name': row.get('Assignee', ''),
                'Date_Time': row.get('Created', ''),
                'Task_Name': row.get('Summary', ''),
                'Improvement_Type': row.get('Improvement Type', '')
            })
            jira_count += 1
        print(f"  Found {jira_count} rows from jira_issues.csv")
    
    # Read from WW2619.csv
    # Columns: program, task_id, status_name, user_name, date_time_req, task_name, improvement_type
    print(f"Reading {ww_file}...")
    with open(ww_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        ww_count = 0
        for row in reader:
            merged_data.append({
                'Source': 'WW2619',
                'Program': row.get('program', ''),
                'Task_ID': row.get('task_id', ''),
                'Status': row.get('status_name', ''),
                'User_Name': row.get('user_name', ''),
                'Date_Time': row.get('date_time_req', ''),
                'Task_Name': row.get('task_name', ''),
                'Improvement_Type': row.get('improvement_type', '')
            })
            ww_count += 1
        print(f"  Found {ww_count} rows from WW2619.csv")
    
    # Write merged data to output file
    print(f"\nWriting merged data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_data)
    
    print(f"Successfully merged {len(merged_data)} rows ({jira_count} from jira_issues, {ww_count} from WW2619)")
    print(f"Output saved to: {output_file}")


def main():
    """Main function to execute the CSV merge."""
    # Define file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    jira_file = os.path.join(script_dir, 'jira_issues.csv')
    ww_file = os.path.join(script_dir, 'WW2619.csv')
    output_file = os.path.join(script_dir, 'merged_issues.csv')
    
    # Check if input files exist
    if not os.path.exists(jira_file):
        print(f"Error: {jira_file} not found!")
        return 1
    
    if not os.path.exists(ww_file):
        print(f"Error: {ww_file} not found!")
        return 1
    
    # Perform the merge
    try:
        merge_csv_files(jira_file, ww_file, output_file)
        return 0
    except Exception as e:
        print(f"Error during merge: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
