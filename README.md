# TTR Data Processor

This repository contains scripts for processing TTR (Time to Resolution) data from multiple sources.

## Overview

The `ttr_data_processor.py` script is a unified solution that combines two main functionalities:

1. **FTP File Download**: Downloads DISC configuration files from an FTP server
2. **Jira Issue Scraping**: Scrapes Jira issues data and exports to CSV

This script replaces the previous separate scripts:
- `DISC_ttr_pulling.py` (FTP functionality)
- `jira_web_access.py` (Jira scraping functionality)

## Features

### FTP Download
- Downloads files from DISC directory on FTP server
- Skips download if local directory already exists and contains files
- Configurable connection parameters

### Jira Scraping
- Scrapes issues from multiple Jira projects (SUMMIT, MARLINCT, MBP, DORADO)
- Exports data to CSV format
- Captures key fields: Project, Key, Status, Assignee, Created, Summary, Improvement Type
- Handles pagination and custom fields

## Configuration

All configuration constants are defined at the top of `ttr_data_processor.py`:

### FTP Configuration
```python
FTP_HOST = '10.19.67.204'
FTP_PATH = '/var/merlin/cfgs/Siyarat/DISC'
FTP_USERNAME = 'merlin'
FTP_PASSWORD = 'merlin'
FTP_LOCAL_DIR = r'D:\i\warachai\MY_RESOURCE\MY_SCRIPT\TTR_Feature_Input\DISC_downloads'
```

### Jira Configuration
```python
JIRA_BASE_URL = 'https://jira.seagate.com'
JIRA_PROJECTS = ['SUMMIT', 'MARLINCT', 'MBP', 'DORADO']
JIRA_OUTPUT_FILE = r'D:/i/warachai/MY_RESOURCE/MY_SCRIPT/TTR_Feature_Input/jira_issues.csv'
```

## Requirements

```
selenium
webdriver-manager
requests
```

Install dependencies:
```bash
pip install selenium webdriver-manager requests
```

## Usage

Run the complete data processing pipeline:
```bash
python ttr_data_processor.py
```

This will:
1. Download DISC files from FTP (if not already downloaded)
2. Scrape Jira issues and save to `jira_issues.csv`

## File Structure

```
.
├── ttr_data_processor.py    # Main unified script
├── DISC_ttr_pulling.py      # Legacy FTP script (deprecated)
├── jira_web_access.py       # Legacy Jira script (deprecated)
├── WW2612.csv               # Sample CSV data
├── WW2613.csv               # Sample CSV data
└── jira_issues.csv          # Output from Jira scraping
```

## Code Organization

The script is organized into clear sections:

1. **Imports**: All required libraries
2. **Constants**: Configuration parameters grouped by functionality
   - FTP Configuration
   - Jira Configuration
   - Selenium Configuration
3. **FTP Functions**: Functions for FTP operations
4. **Jira Functions**: Functions for Jira scraping
5. **Main Execution**: Orchestrates the complete workflow

## Legacy Scripts

The following scripts have been merged into `ttr_data_processor.py`:
- `DISC_ttr_pulling.py` - Contained FTP download logic
- `jira_web_access.py` - Contained Jira scraping logic

These files are kept for reference but are no longer needed for regular operation.

## Output

### Jira CSV Output
The Jira scraping generates a CSV file with the following columns:
- Project
- Key
- Status
- Assignee
- Created
- Summary
- Improvement Type

## Notes

- Chrome WebDriver is automatically managed by `webdriver-manager`
- The script includes proper error handling for both FTP and Jira operations
- Paths are currently configured for Windows (adjust as needed for Linux/Mac)
