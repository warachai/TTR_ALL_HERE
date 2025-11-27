#!/usr/bin/env python3
"""
Configuration File for TTR Data Processing

This file contains all constant values and configuration settings used across the TTR project.
"""

import os

# ==============================================================================
# DIRECTORY PATHS
# ==============================================================================
# Base directory (automatically determined from this file's location)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Raw data directories
RAW_DIR = os.path.join(BASE_DIR, 'RAW')
RAW_DISC_DIR = os.path.join(RAW_DIR, 'DISC')
RAW_JIRA_DIR = os.path.join(RAW_DIR, 'JIRA')
RAW_EXCEL_DIR = os.path.join(RAW_DIR, 'EXCEL')



# Output directories
OUTPUT_RAW_DIR = RAW_DIR
OUTPUT_MASTER_DIR = os.path.join(BASE_DIR, 'MASTER')


# ==============================================================================
# FILE NAMES
# ==============================================================================
JIRA_FILE_NAME = 'jira_issues.csv'
MERGED_OUTPUT_FILE_NAME = 'merged_issues.csv'
EXCEL_FILE_NAME = "TTR list review Q1'26 (8).xlsx"

STAGING_FILE_NAME = 'task_staging.csv'
LATEST_FILE_NAME = 'task_latest.csv'
TTR_ITEM_MASTER_FILE_NAME = 'ttr_item_master.csv'
# ==============================================================================
# FULL FILE PATHS
# ==============================================================================
JIRA_FILE_PATH = os.path.join(RAW_JIRA_DIR, JIRA_FILE_NAME)
MERGED_OUTPUT_PATH = os.path.join(OUTPUT_RAW_DIR, MERGED_OUTPUT_FILE_NAME)
EXCEL_FILE_PATH = os.path.join(RAW_EXCEL_DIR, EXCEL_FILE_NAME)

# Base Jira URL (used to construct clickable links to individual issues)
JIRA_BASE_URL = "https://jira.seagate.com/jira/browse/"
# Base DISC (Korat request) URL for CR-based task IDs (e.g., CR13599 -> request/13599/)
DISC_REQUEST_BASE_URL = "https://disc.sing.seagate.com/korat/request"
#Site access log file (captures page hits by user)
ACCESS_LOG_FILE = os.path.join(BASE_DIR, 'access_log.csv')



TASK_CURRENT_FILE_PATH = MERGED_OUTPUT_PATH
STAGING_FILE_PATH = os.path.join(OUTPUT_RAW_DIR, STAGING_FILE_NAME)
LATEST_FILE_PATH = os.path.join(OUTPUT_RAW_DIR, LATEST_FILE_NAME)
TTR_ITEM_MASTER_FILE_PATH = os.path.join(OUTPUT_MASTER_DIR, TTR_ITEM_MASTER_FILE_NAME)
# ==============================================================================
# PROGRAM NAME MAPPING
# ==============================================================================
# Maps program names from source data to standardized names
PROGRAM_NAME_MAP = {
    'MBP': 'MARLIN BP',
    'MARLINCT': 'MARLIN',
    'SUMMIT': 'SUMMIT',
    'DORADO': 'DORADO'
}


# ==============================================================================
# EXCEL SHEET CONFIGURATIONS
# ==============================================================================
# Configuration for each Excel sheet to import
EXCEL_SHEETS_CONFIG = [
    {
        'sheet': 'MarlinBP FW2620 working',
        'column_map': {
            'G': 'Task_ID',
            'H': 'Status',
            'D': 'User_Name',
            'C': 'Task_Name',
            'E': 'GAIN',
        },
        'source_name': 'excel_import',
        'program_name': 'MBP',
        'start_row': 78
    },
    {
        'sheet': 'Marlin WW21',
        'column_map': {
            'H': 'Task_ID',
            'I': 'Status',
            'F': 'User_Name',
            'D': 'Task_Name',
            'L': 'GAIN',            
        },
        'source_name': 'excel_import',
        'program_name': 'MARLIN',
        'start_row': 66
    },
    {
        'sheet': 'Summit FW2614-20',
        'column_map': {
            'J': 'Task_ID',
            'K': 'Status',
            'I': 'User_Name',
            'D': 'Task_Name',
            'H': 'GAIN',            
        },
        'source_name': 'excel_import',
        'program_name': 'SUMMIT',
        'start_row': 39
    },
    {
        'sheet': 'Dorado WW18 Working',
        'column_map': {
            'E': 'Task_ID',
            'F': 'Status',
            'C': 'User_Name',
            'B': 'Task_Name',
            'I': 'GAIN',            
        },
        'source_name': 'excel_import',
        'program_name': 'DORADO',
        'start_row': 47
    }
]


# ==============================================================================
# CSV FIELD NAMES
# ==============================================================================
# Output CSV fieldnames for merged data
OUTPUT_FIELDNAMES = [
    'Source',
    'Program',
    'Task_ID',
    'Status',
    'User_Name',
    'Date_Time',
    'Task_Name',
    'Improvement_Type'
]

# JIRA CSV column mappings
JIRA_COLUMNS = {
    'Project': 'Program',
    'Key': 'Task_ID',
    'Status': 'Status',
    'Assignee': 'User_Name',
    'Created': 'Date_Time',
    'Summary': 'Task_Name',
    'Improvement Type': 'Improvement_Type'
}

# DISC/WW CSV column mappings
DISC_COLUMNS = {
    'program': 'Program',
    'task_id': 'Task_ID',
    'status_name': 'Status',
    'user_name': 'User_Name',
    'date_time_req': 'Date_Time',
    'task_name': 'Task_Name',
    'improvement_type': 'Improvement_Type'
}


# ==============================================================================
# DEFAULT VALUES
# ==============================================================================
DEFAULT_IMPROVEMENT_TYPE = 'TTR'
DEFAULT_SOURCE_NAME = 'excel_import'


# ==============================================================================
# REGULAR EXPRESSIONS
# ==============================================================================
# Pattern for matching WW files (e.g., WW2619.csv)
WW_FILE_PATTERN = r'WW\d{4}\.csv'


# ==============================================================================
# ENCODING
# ==============================================================================
FILE_ENCODING = 'utf-8'


# ==============================================================================
# SCHEDULING CONFIGURATION (Optional)
# ==============================================================================
# Default schedule settings
SCHEDULE_ENABLED = False
SCHEDULE_DAYS = ['monday', 'friday']  # Days of the week to run
SCHEDULE_TIME = '09:00'  # Time to run (HH:MM format)


# ==============================================================================
# LOGGING CONFIGURATION (Optional)
# ==============================================================================
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

MASTER_FILE_DIR = os.path.join(BASE_DIR, 'MASTER')
# ---- new master-level files ----
TASK_MASTER_FILE   = os.path.join(MASTER_FILE_DIR, "task_master.csv")
PLAN_MASTER_FILE   = os.path.join(MASTER_FILE_DIR, "plan_master.csv")
PRODUCT_MASTER_FILE = os.path.join(MASTER_FILE_DIR, "product_master.csv")
FEATURE_MASTER_FILE = os.path.join(MASTER_FILE_DIR, "feature_master.csv")
TASK_FEATURE_FILE   = os.path.join(MASTER_FILE_DIR, "task_feature.csv")
TASK_LATEST_FILE    = LATEST_FILE_PATH  # from previous code: data/task_latest.csv
TASK_MASTER_FILE_PATH   = os.path.join(MASTER_FILE_DIR, "task_master.csv")
FEATURE_MASTER_FILE_PATH   = os.path.join(MASTER_FILE_DIR, "feature_master.csv")
PRODUCT_FEATURE_FILE_PATH   = os.path.join(MASTER_FILE_DIR, "product_feature.csv")
# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def get_excel_files_config():
    """
    Get the complete Excel files configuration with file path.
    
    Returns:
        list: List of Excel file configurations
    """
    return [
        {
            'file': EXCEL_FILE_PATH,
            **config
        }
        for config in EXCEL_SHEETS_CONFIG
    ]


def create_directories():
    """
    Create all necessary directories if they don't exist.
    """
    directories = [
        RAW_DIR,
        RAW_DISC_DIR,
        RAW_JIRA_DIR,
        RAW_EXCEL_DIR,
        OUTPUT_RAW_DIR
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("All necessary directories have been created/verified.")


# ==============================================================================
# VALIDATION
# ==============================================================================
def validate_config():
    """
    Validate the configuration settings.
    
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    issues = []
    
    # Check if Excel file exists
    if not os.path.exists(EXCEL_FILE_PATH):
        issues.append(f"Excel file not found: {EXCEL_FILE_PATH}")
    
    # Check if JIRA directory exists
    if not os.path.exists(RAW_JIRA_DIR):
        issues.append(f"JIRA directory not found: {RAW_JIRA_DIR}")
    
    # Check if DISC directory exists
    if not os.path.exists(RAW_DISC_DIR):
        issues.append(f"DISC directory not found: {RAW_DISC_DIR}")
    
    if issues:
        print("Configuration validation issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("Configuration validated successfully.")
    return True


if __name__ == '__main__':
    # When run directly, create directories and validate configuration
    print("TTR Configuration")
    print("=" * 60)
    print(f"Base Directory: {BASE_DIR}")
    print(f"Raw Data Directory: {RAW_DIR}")
    print(f"Excel File: {EXCEL_FILE_PATH}")
    print(f"Output File: {MERGED_OUTPUT_PATH}")
    print("=" * 60)
    print()
    
    create_directories()
    print()
    validate_config()
