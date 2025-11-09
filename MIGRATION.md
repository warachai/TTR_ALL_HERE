# Migration Guide: From Separate Scripts to ttr_data_processor.py

## Overview
This document explains the changes made when merging `DISC_ttr_pulling.py` and `jira_web_access.py` into `ttr_data_processor.py`.

## What Changed

### Old Structure (2 separate files)

**DISC_ttr_pulling.py:**
- FTP download functionality
- Hardcoded values mixed with code
- Single purpose script
- ~41 lines

**jira_web_access.py:**
- Jira scraping functionality
- Hardcoded configuration
- Global chrome_options variable
- ~121 lines

**Total:** 2 files, ~162 lines, scattered configuration

### New Structure (1 unified file)

**ttr_data_processor.py:**
- Combined FTP and Jira functionality
- All constants organized at the top in clearly labeled sections
- Modular function design
- Main orchestration function
- Comprehensive docstrings
- ~280 lines (including comments and organization)

## Key Improvements

### 1. Constants Organization
**Before:** Configuration values scattered throughout the code

**After:** All constants grouped at the top in clear sections:
```python
# FTP CONFIGURATION
FTP_HOST = '10.19.67.204'
FTP_PATH = '/var/merlin/cfgs/Siyarat/DISC'
...

# JIRA CONFIGURATION
JIRA_BASE_URL = 'https://jira.seagate.com'
JIRA_PROJECTS = ['SUMMIT', 'MARLINCT', 'MBP', 'DORADO']
...

# SELENIUM CONFIGURATION
CHROME_OPTIONS_LIST = [...]
CSV_HEADERS = [...]
```

### 2. Code Organization
**Before:** 
- Global variables (e.g., `chrome_options`)
- Mixed configuration and logic
- No clear entry point

**After:**
- Clear section dividers with comment headers
- Separated FTP and Jira functions
- Main function as clear entry point
- No global state

### 3. Documentation
**Before:** Minimal docstrings, some functions undocumented

**After:**
- Module-level docstring
- Comprehensive function docstrings
- README.md with full documentation
- Clear parameter descriptions

### 4. Error Handling
**Before:** Basic error handling in some places

**After:**
- Consistent try-except blocks
- Informative error messages
- Graceful degradation

### 5. Maintainability
**Before:**
- Need to run 2 separate scripts
- Duplicate imports
- Inconsistent style

**After:**
- Single script to run both operations
- Organized imports at the top
- Consistent coding style
- Easy to modify configuration

## Function Mapping

### FTP Functions
| Old (DISC_ttr_pulling.py) | New (ttr_data_processor.py) |
|---------------------------|----------------------------|
| `download_ftp_files()`    | `download_ftp_files()`    |
| N/A | `main()` (orchestration) |

### Jira Functions
| Old (jira_web_access.py) | New (ttr_data_processor.py) |
|--------------------------|----------------------------|
| `construct_jira_url()`   | `construct_jira_url()`    |
| `find_keys()`            | `find_keys()`             |
| `handle_rest_api_result()`| `handle_rest_api_result()`|
| Global driver setup      | `setup_chrome_driver()`   |
| Main execution block     | `scrape_jira_issues()`    |
| N/A                      | `main()` (orchestration)  |

## Usage Comparison

### Before (Running Both Scripts)
```bash
# Step 1: Download FTP files
python DISC_ttr_pulling.py

# Step 2: Scrape Jira issues
python jira_web_access.py
```

### After (Single Script)
```bash
# Run everything
python ttr_data_processor.py
```

## Configuration Changes

### Before
To change configuration, you had to:
1. Edit multiple files
2. Find the hardcoded values in the code
3. Be careful not to break logic

### After
To change configuration:
1. Edit the constants section at the top of `ttr_data_processor.py`
2. All configuration is clearly labeled
3. Configuration is separate from logic

## Migration Steps

If you were using the old scripts:

1. **Update imports**: If you were importing functions from the old scripts, update to:
   ```python
   from ttr_data_processor import download_ftp_files, scrape_jira_issues
   ```

2. **Update configuration**: Review and update the constants at the top of `ttr_data_processor.py`

3. **Test**: Run `python ttr_data_processor.py` to verify everything works

4. **Optional**: Archive or delete the old scripts:
   - `DISC_ttr_pulling.py`
   - `jira_web_access.py`

## Benefits Summary

✅ **Single script** instead of two
✅ **Clear constant definitions** at the top
✅ **Better organization** with section dividers
✅ **Improved documentation** with docstrings and README
✅ **Consistent error handling**
✅ **Easier to maintain** and modify
✅ **More professional** code structure
✅ **No security vulnerabilities** (CodeQL verified)

## Files Overview

### New Files Created
- `ttr_data_processor.py` - Main unified script
- `README.md` - Documentation
- `.gitignore` - Python artifacts exclusion
- `MIGRATION.md` - This file

### Legacy Files (Can be archived)
- `DISC_ttr_pulling.py` - Superseded by ttr_data_processor.py
- `jira_web_access.py` - Superseded by ttr_data_processor.py

### Data Files (Unchanged)
- `WW2612.csv`
- `WW2613.csv`
- `jira_issues.csv` (generated)
