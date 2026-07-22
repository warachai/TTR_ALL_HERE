#!/usr/bin/env python3
"""
CSV Merge Utility

This script merges jira_issues.csv and WW2619.csv files by selecting specific columns
and adding a source identifier column to track the origin of each row.
"""

import csv
import os
import pandas as pd
from datetime import datetime
import config


def read_excel_file(excel_file, sheet_name, column_map, source_name, start_row=1, program_name=''):
    """
    Read an Excel file and convert it to the merged CSV format.
    
    Args:
        excel_file (str): Path to the Excel file
        sheet_name (str): Name of the sheet to read from
        column_map (dict): Dictionary mapping Excel column letters/names to output column names
                          Example: {'A': 'Program', 'B': 'Task_ID'} or {'Project': 'Program'}
        source_name (str): Identifier for the source (e.g., 'excel_import')
        start_row (int): Row number to start reading data from (1-indexed). Default is 1.
        program_name (str): Program name to set for all rows. If not provided, will use mapped column value.
    
    Returns:
        list: List of dictionaries with merged data format
    
    Example 1 - Using column letters:
        column_map = {
            'A': 'Program',           # Excel column A -> Output 'Program'
            'B': 'Task_ID',           # Excel column B -> Output 'Task_ID'
            'C': 'Status',            # Excel column C -> Output 'Status'
            'D': 'User_Name',         # Excel column D -> Output 'User_Name'
            'E': 'Date_Time',         # Excel column E -> Output 'Date_Time'
            'F': 'Task_Name',         # Excel column F -> Output 'Task_Name'
            'G': 'Improvement_Type'   # Excel column G -> Output 'Improvement_Type'
        }
        start_row = 10  # Start reading from row 10
    
    Example 2 - Using column names:
        column_map = {
            'Project': 'Program',           # Excel 'Project' -> Output 'Program'
            'Key': 'Task_ID',               # Excel 'Key' -> Output 'Task_ID'
            'Status': 'Status',             # Excel 'Status' -> Output 'Status'
            'Assignee': 'User_Name',        # Excel 'Assignee' -> Output 'User_Name'
            'Created': 'Date_Time',         # Excel 'Created' -> Output 'Date_Time'
            'Summary': 'Task_Name',         # Excel 'Summary' -> Output 'Task_Name'
            'Improvement Type': 'Improvement_Type'
        }
        start_row = 1  # Start from first row
    """
    print(f"Reading Excel file: {excel_file}, Sheet: {sheet_name}, Starting from row: {start_row}...")
    
    try:
        # Get current date in ISO format
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Read Excel file without headers first to handle custom start row
        df_raw = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
        
        # Adjust for 0-indexed (start_row is 1-indexed)
        skip_rows = start_row - 1
        
        # Read the actual data starting from the specified row
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, skiprows=skip_rows)
        print(f"  Found {len(df)} rows in sheet '{sheet_name}' (starting from row {start_row})")
        
        # Define output fieldnames
        output_fieldnames = ['Source', 'Program', 'Task_ID', 'Status', 'User_Name', 
                           'Date_Time', 'Task_Name', 'Improvement_Type', 'GAIN', 'FixVersions']
        
        merged_data = []
        
        for idx, row in df.iterrows():
            # Create a new row with mapped columns
            new_row = {'Source': source_name}
            
            # Map Excel columns to output columns
            for excel_col, output_col in column_map.items():
                value = ''
                
                # Check if it's a column letter (A, B, C, etc.) or column name
                if len(excel_col) <= 3 and excel_col.isalpha():
                    # Convert column letter to index (A=0, B=1, C=2, etc.)
                    col_index = 0
                    for i, char in enumerate(reversed(excel_col.upper())):
                        col_index += (ord(char) - ord('A') + 1) * (26 ** i)
                    col_index -= 1  # Convert to 0-indexed
                    
                    # Get value from the column index
                    if col_index < len(df.columns):
                        value = row.iloc[col_index] if col_index < len(row) else ''
                    else:
                        print(f"  Warning: Column '{excel_col}' (index {col_index}) is out of range")
                else:
                    # Assume it's a column name - try to find it in the dataframe
                    if excel_col in df.columns:
                        value = row.get(excel_col, '')
                    else:
                        print(f"  Warning: Column '{excel_col}' not found in Excel sheet")
                
                # Convert NaN to empty string
                if pd.isna(value):
                    value = ''
                
                new_row[output_col] = str(value)
            
            # Fill in any missing output columns with empty strings
            for field in output_fieldnames:
                if field not in new_row:
                    new_row[field] = ''
            
            # Set default values for specific fields
            # Improvement_Type always set to 'TTR'
            new_row['Improvement_Type'] = 'TTR'
            
            # Program set to parameter value if provided
            if program_name:
                new_row['Program'] = program_name
            
            # Date_Time set to current date
            new_row['Date_Time'] = current_date
            
            # Skip rows where Task_Name is empty
            if new_row.get('Task_Name', '').strip():
                merged_data.append(new_row)
        
        print(f"  Successfully processed {len(merged_data)} rows from Excel")
        return merged_data
        
    except FileNotFoundError:
        print(f"Error: Excel file '{excel_file}' not found!")
        return []
    except ValueError as e:
        print(f"Error: Sheet '{sheet_name}' not found in Excel file! ({e})")
        return []
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        import traceback
        traceback.print_exc()
        return []


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
    # Source, Program, Task_ID, Status, User_Name, Date_Time, Task_Name, Improvement_Type, GAIN
    fieldnames = ['Source', 'Program', 'Task_ID', 'Status', 'User_Name', 'Date_Time', 'Task_Name', 'Improvement_Type', 'GAIN', 'FixVersions']
    
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
                'Improvement_Type': row.get('Improvement Type', ''),
                'FixVersions': row.get('FixVersions', '')
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
                'Improvement_Type': row.get('improvement_type', ''),
                'FixVersions': row.get('fixversions', '')
            })
            ww_count += 1
        print(f"  Found {ww_count} rows from WW2619.csv")
    
    # Write merged data to output file
    print(f"\nWriting merged data to {output_file}...")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"  Created output directory: {output_dir}")
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_data)
    
    print(f"Successfully merged {len(merged_data)} rows ({jira_count} from jira_issues, {ww_count} from WW2619)")
    print(f"Output saved to: {output_file}")


def merge_csv_with_excel(jira_file, ww_file, excel_files, output_file, program_name_map=None):
    """
    Merge CSV files and Excel files into a single output file.
    
    Args:
        jira_file (str): Path to the jira_issues.csv file
        ww_file (str): Path to the WW2619.csv file
        excel_files (list): List of dictionaries containing Excel file configurations
                           Each dict should have: 'file', 'sheet', 'column_map', 'source_name'
        output_file (str): Path to the output merged CSV file
        program_name_map (dict): Dictionary to map program names to standardized values
                                Example: {'MBP': 'MarlinBP', 'MARLINCT': 'MARLIN'}
    
    Example:
        excel_files = [
            {
                'file': 'data.xlsx',
                'sheet': 'Sheet1',
                'column_map': {
                    'A': 'Program',
                    'B': 'Task_ID',
                    'C': 'Status',
                    'D': 'User_Name',
                    'E': 'Date_Time',
                    'F': 'Task_Name',
                    'G': 'Improvement_Type'
                },
                'source_name': 'excel_import'
                'start_row': 10
            }
        ]
        
        program_name_map = {
            'MBP': 'MarlinBP',
            'MARLINCT': 'MARLIN'
        }
    """
    merged_data = []
    
    # Initialize program name map if not provided
    if program_name_map is None:
        program_name_map = {}
    
    # Define output columns (unified schema)
    fieldnames = ['Source', 'Program', 'Task_ID', 'Status', 'User_Name', 'Date_Time', 'Task_Name', 'Improvement_Type', 'GAIN', 'FixVersions']
    
    # Read from jira_issues.csv
    if os.path.exists(jira_file):
        print(f"Reading {jira_file}...")
        with open(jira_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            jira_count = 0
            for row in reader:
                program_name = row.get('Project', '')
                # Apply program name mapping
                program_name = program_name_map.get(program_name, program_name)

                if row.get('Key', '') == 'MARLINCT-2337':
                    print(f"Processing JIRA row: Program='{program_name}', Key='{row.get('Key', '')}', FixVersions='{row.get('Fix Version', '')}'")
                
                merged_data.append({
                    'Source': 'jira_issues',
                    'Program': program_name,
                    'Task_ID': row.get('Key', ''),
                    'Status': row.get('Status', ''),
                    'User_Name': row.get('Assignee', ''),
                    'Date_Time': row.get('Created', ''),
                    'Task_Name': row.get('Summary', ''),
                    'Improvement_Type': row.get('Improvement Type', ''),
                    'FixVersions': row.get('Fix Version', '')
                })
                jira_count += 1
            print(f"  Found {jira_count} rows from jira_issues.csv")
    else:
        print(f"Skipping {jira_file} (not found)")
        jira_count = 0
    
    # Read latest DISC from WW CSV file
    if os.path.exists(ww_file):
        print(f"Reading {ww_file}...")
        with open(ww_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            ww_count = 0
            for row in reader:
                program_name = row.get('program', '')
                # Apply program name mapping
                program_name = program_name_map.get(program_name, program_name)
                
                merged_data.append({
                    'Source': 'DISC',
                    'Program': program_name,
                    'Task_ID': row.get('task_id', ''),
                    'Status': row.get('status_name', ''),
                    'User_Name': row.get('user_name', ''),
                    'Date_Time': row.get('date_time_req', ''),
                    'Task_Name': row.get('task_name', ''),
                    'Improvement_Type': row.get('improvement_type', ''),
                    'FixVersions': row.get('FixVersions', '')                    
                })
                ww_count += 1
            print(f"  Found {ww_count} rows from {ww_file}")
    else:
        print(f"Skipping {ww_file} (not found)")
        ww_count = 0
    
    # Read from Excel files
    excel_count = 0
    if excel_files:
        for excel_config in excel_files:
            excel_data = read_excel_file(
                excel_file=excel_files[excel_config][0].get('file'),
                sheet_name=excel_files[excel_config][0].get('sheet'),
                column_map=excel_files[excel_config][0].get('column_map', {}),
                source_name=excel_files[excel_config][0].get('source_name', 'excel'),
                start_row=excel_files[excel_config][0].get('start_row', 1),
                program_name=excel_files[excel_config][0].get('program_name', '')
            )
            
            # Apply program name mapping to Excel data
            for data_row in excel_data:
                original_program = data_row.get('Program', '')
                data_row['Program'] = program_name_map.get(original_program, original_program)
            
            merged_data.extend(excel_data)
            excel_count += len(excel_data)
    
    # Write merged data to output file
    print(f"\nWriting merged data to {output_file}...")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"  Created output directory: {output_dir}")
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_data)
    
    print(f"Successfully merged {len(merged_data)} rows")
    print(f"  - {jira_count} from jira_issues")
    print(f"  - {ww_count} from WW2619")
    print(f"  - {excel_count} from Excel files")
    print(f"Output saved to: {output_file}")


def main_():
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

def selectLastestWWFile(script_dir):
    """
    Select the latest WW CSV file in the current directory based on naming convention.
    
    Returns:
        str: Path to the latest WW CSV file or None if not found.
    """
    import re
    from datetime import datetime

    ww_files = [f for f in os.listdir(script_dir+r"\RAW\DISC") if re.match(r'WW\d{4}\.csv', f)]
    if not ww_files:
        return None

    # Sort files by the number in their name (assuming WWXXXX)
    ww_files.sort(key=lambda x: int(re.search(r'WW(\d{4})\.csv', x).group(1)), reverse=True)
    return ww_files[0]


def main():
    """
    Main function to execute the CSV merge with Excel file support.
    
    Uses configuration from config.py for all settings.
    """
    # Get file paths from config
    script_dir = config.BASE_DIR
    jira_file = config.JIRA_FILE_PATH
    ww_file = os.path.join(config.RAW_DISC_DIR, selectLastestWWFile(script_dir))
    output_file = config.MERGED_OUTPUT_PATH
    
    # Get program name mapping from config
    program_name_map = config.PROGRAM_NAME_MAP
    
    # Get Excel files configuration from config
    excel_files = config.get_excel_files_config()
    #excel_files = None

    # Perform the merge with Excel files
    try:
        merge_csv_with_excel(jira_file, ww_file, excel_files, output_file, program_name_map)
        return 0
    except Exception as e:
        print(f"Error during merge: {e}")
        import traceback
        traceback.print_exc()
        return 1



if __name__ == '__main__':
    main()
