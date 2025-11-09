#!/usr/bin/env python3
"""
CSV Merge Utility

This script merges jira_issues.csv and WW2613.csv files by selecting common columns
and adding a source identifier column to track the origin of each row.
"""

import csv
import os


def merge_csv_files(jira_file, ww_file, output_file):
    """
    Merge two CSV files by selecting common columns and adding a source identifier.
    
    Args:
        jira_file (str): Path to the jira_issues.csv file
        ww_file (str): Path to the WW2613.csv file
        output_file (str): Path to the output merged CSV file
    """
    merged_data = []
    
    # Define common column (case-insensitive match)
    common_column = 'summary'
    
    # Read from jira_issues.csv
    print(f"Reading {jira_file}...")
    with open(jira_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        jira_count = 0
        for row in reader:
            # Find the summary column (case-insensitive)
            summary_value = None
            for key in row.keys():
                if key.lower() == common_column:
                    summary_value = row[key]
                    break
            
            merged_data.append({
                'summary': summary_value if summary_value is not None else '',
                'source': 'jira_issues'
            })
            jira_count += 1
        print(f"  Found {jira_count} rows from jira_issues.csv")
    
    # Read from WW2613.csv
    print(f"Reading {ww_file}...")
    with open(ww_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        ww_count = 0
        for row in reader:
            # Find the summary column (case-insensitive)
            summary_value = None
            for key in row.keys():
                if key.lower() == common_column:
                    summary_value = row[key]
                    break
            
            merged_data.append({
                'summary': summary_value if summary_value is not None else '',
                'source': 'WW2613'
            })
            ww_count += 1
        print(f"  Found {ww_count} rows from WW2613.csv")
    
    # Write merged data to output file
    print(f"\nWriting merged data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['summary', 'source']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_data)
    
    print(f"Successfully merged {len(merged_data)} rows ({jira_count} from jira_issues, {ww_count} from WW2613)")
    print(f"Output saved to: {output_file}")


def main():
    """Main function to execute the CSV merge."""
    # Define file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    jira_file = os.path.join(script_dir, 'jira_issues.csv')
    ww_file = os.path.join(script_dir, 'WW2613.csv')
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
