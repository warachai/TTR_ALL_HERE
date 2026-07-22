"""
TTR Data Processor
===================
This script combines FTP file downloading and Jira web scraping functionality.
It downloads DISC configuration files from FTP and scrapes Jira issues data.

Author: TTR Team
"""

# ==============================================================================
# IMPORTS
# ==============================================================================
import requests
import json
import os
import time
import csv
from ftplib import FTP
from urllib.parse import urlencode

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import pandas as pd


# ==============================================================================
FTP_HOST = '10.19.67.204'
FTP_PATH = '/var/merlin/cfgs/Siyarat/DISC'
FTP_USERNAME = 'merlin'
FTP_PASSWORD = 'merlin'
FTP_LOCAL_DIR = r'D:\work\project\project\Github\TTR_ALL_HERE\RAW\DISC'


# ==============================================================================
# CONSTANTS - JIRA CONFIGURATION
# ==============================================================================
JIRA_BASE_URL = 'https://jira.seagate.com'
JIRA_API_ENDPOINT = '/jira/rest/api/2/search'
#JIRA_PROJECTS = ['SUMMIT', 'MARLINCT', 'MBP', 'DORADO', 'TSR']
JIRA_PROJECTS = ['DORADO',]

JIRA_FIELDS = 'key,summary,status,reporter,created,customfield_35600'
JIRA_MAX_RESULTS = 50
JIRA_OUTPUT_FILE = r'D:\work\project\project\Github\TTR_ALL_HERE\RAW\JIRA\jira_issues.csv'


# ==============================================================================
# CONSTANTS - SELENIUM CONFIGURATION
# ==============================================================================
CHROME_OPTIONS_LIST = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--window-size=1920,1080'
]

# CSV Headers for Jira output
CSV_HEADERS = [
    'Project',
    'Key',
    'Status',
    'Reporter',
    'Created',
    'Summary',
    'Improvement Type'
]


# ==============================================================================
# FTP FUNCTIONS
# ==============================================================================
def download_ftp_files(ftp_host=FTP_HOST, ftp_path=FTP_PATH, 
                       local_dir=FTP_LOCAL_DIR, username=FTP_USERNAME, 
                       password=FTP_PASSWORD):
    """
    Download all files from a specified FTP directory to a local directory 
    if the directory does not already exist.

    Args:
        ftp_host (str): FTP server address.
        ftp_path (str): Path on the FTP server to download files from.
        local_dir (str): Local directory to save downloaded files.
        username (str): FTP username (default: 'merlin').
        password (str): FTP password (default: 'merlin').
    """
    if not os.path.exists(local_dir) :
        print(f"Local directory already exists and is not empty: {local_dir}")
        return

    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    with FTP(ftp_host) as ftp:
        ftp.login(user=username, passwd=password)
        ftp.cwd(ftp_path)
        files = ftp.nlst()
        print(f"Files found: {files}")
        for filename in files:
            local_file = os.path.join(local_dir, filename)
            with open(local_file, 'wb') as f:
                ftp.retrbinary(f'RETR {filename}', f.write)
            print(f"Downloaded: {filename}")


# ==============================================================================
# JIRA FUNCTIONS
# ==============================================================================
def construct_jira_url(base_url, endpoint, project, start_at=0,batch_size = JIRA_MAX_RESULTS):
    """
    Constructs a Jira REST API URL with the given base URL, endpoint, and project.

    Args:
        base_url (str): The base URL of the Jira instance.
        endpoint (str): The API endpoint.
        project (str): The project name for JQL query.

    Returns:
        str: The constructed URL.
    """
    jql_query = f"project={project} ORDER BY created ASC"
    
    query_params = {
        "jql": jql_query,
        "startAt": start_at,
        "fields": JIRA_FIELDS,
        "maxResults": batch_size
    }
    return f"{base_url}{endpoint}?{urlencode(query_params)}"


def find_keys(d, target):
    """
    Recursively find keys in a dictionary that have specific target values.

    Args:
        d (dict): Dictionary to search.
        target: Target value to find.

    Returns:
        list: List of keys that have the target value.
    """
    keys = []
    for k, v in d.items():
        if isinstance(v, dict):
            keys.extend(find_keys(v, target))
        elif v in target:
            keys.append(k)
    return keys



def handle_rest_api_result(project, driver):
    """Process the REST API JSON response and append to Jira CSV using pandas.

    Duplicates (by Key) within the current fetched batch are dropped keeping the latest
    representation (last occurrence). This does not de-duplicate existing rows already
    written to disk; it only cleans the in-memory batch before appending.

    Args:
        project: Jira project key
        driver: Selenium WebDriver instance
    Returns:
        int: Number of issues processed after de-duplication
    """
    total_issues = 0
    try:
        page_source = driver.find_element("tag name", "pre").text
        data = json.loads(page_source)
        raw_issues = data.get("issues", [])
        total_issues = len(raw_issues)
        print(f"Total issues returned for {project}: {data.get('total')} (raw count {len(raw_issues)})\n")

        # Build list of dict rows
        rows = []
        for issue in raw_issues:
            try:
                fields = issue.get("fields", {})
                rows.append({
                    "Project": project,
                    "Key": issue.get("key"),
                    "Status": fields.get("status", {}).get("name", "No Status"),
                    "Reporter": fields.get("assignee", {}).get("displayName", "Unassigned"),
                    "Created": fields.get("created", "No Created Date"),
                    "Summary": fields.get("summary", "No Summary"),
                    "Improvement Type": (fields.get("customfield_35600", [{}])[0].get("value", "Others")
                                          if fields.get("customfield_35600") else "Others")
                })
            except Exception as e:
                print(f"Error processing issue: {e}")

        # Convert to DataFrame and drop intra-batch duplicates by Key (keep last)
        batch_df = pd.DataFrame(rows, columns=CSV_HEADERS)
        intra_before = len(batch_df)
        if not batch_df.empty:
            batch_df = batch_df.drop_duplicates(subset=["Key"], keep="last")
        intra_after = len(batch_df)
        if intra_before != intra_after:
            print(f"Dropped {intra_before - intra_after} duplicate rows inside current batch for project {project}.")

        # Combine with existing file (if present) and perform full dedupe
        if os.path.exists(JIRA_OUTPUT_FILE):
            try:
                existing_df = pd.read_csv(JIRA_OUTPUT_FILE, encoding="utf-8")
                # Ensure columns alignment
                missing_cols = [c for c in CSV_HEADERS if c not in existing_df.columns]
                if missing_cols:
                    for mc in missing_cols:
                        existing_df[mc] = None
                combined_df = pd.concat([existing_df[CSV_HEADERS], batch_df], ignore_index=True)
                full_before = len(combined_df)
                combined_df = combined_df.drop_duplicates(subset=["Key"], keep="last")
                full_after = len(combined_df)
                if full_before != full_after:
                    print(f"Dropped {full_before - full_after} duplicate rows after merging with existing file for project {project}.")
                combined_df.to_csv(JIRA_OUTPUT_FILE, index=False, encoding="utf-8")
                new_unique = full_after - len(existing_df.drop_duplicates(subset=["Key"], keep="last"))
                print(f"Data for {project} merged & saved to {JIRA_OUTPUT_FILE} (new unique rows added: {new_unique}, total rows: {full_after}).\n")

            except Exception as e:
                print(f"Failed reading existing Jira file, rewriting fresh. Reason: {e}")
                batch_df.to_csv(JIRA_OUTPUT_FILE, index=False, encoding="utf-8")
                print(f"Data for {project} saved fresh to {JIRA_OUTPUT_FILE} (rows written: {len(batch_df)})\n")

        else:
            # First write
            batch_df.to_csv(JIRA_OUTPUT_FILE, index=False, encoding="utf-8")
            print(f"Data for {project} saved to new file {JIRA_OUTPUT_FILE} (rows written: {len(batch_df)})\n")

    except Exception as e:
        print(f"Error handling REST API result for {project}: {e}")
        return 0
    
    return total_issues

def setup_chrome_driver():
    """
    Set up and return a configured Chrome WebDriver instance.

    Returns:
        webdriver: Configured Chrome WebDriver instance.
    """
    chrome_options = webdriver.ChromeOptions()
    for option in CHROME_OPTIONS_LIST:
        chrome_options.add_argument(option)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    driver.set_page_load_timeout(30)
    
    return driver


def get_jira_issues():
    """
    Scrape Jira issues for all configured projects and save to CSV.
    """
    driver = setup_chrome_driver()
    
    try:
        # First, load the base domain to set cookies
        print(f"Accessing base domain: {JIRA_BASE_URL}")
        driver.get(JIRA_BASE_URL + '/jira/browse/MARLINCT-2193')
        time.sleep(10)
        
        # Process each project
        start_index = 0
        batch_size = 100
        for project in JIRA_PROJECTS:
            print(f"Processing project: {project}")
            while True:
                query_url = construct_jira_url(JIRA_BASE_URL, JIRA_API_ENDPOINT, project,start_at=start_index,batch_size = batch_size)
                driver.get(query_url)
                time.sleep(10)
                total_issues = handle_rest_api_result(project, driver)
                if total_issues < batch_size:
                    break
                start_index += batch_size
                time.sleep(5)
    
    finally:
        driver.quit()
        print("Jira scraping completed.")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
def main():
    """
    Main function to get Jira scraping.
    """

    # Step 2: Scrape Jira issues
    print("\n Scraping Jira issues...")
    try:
        get_jira_issues()
        print("Jira scraping completed successfully.")
    except Exception as e:
        print(f"Error during Jira scraping: {e}")
    
    print("\n" + "=" * 80)
    print("TTR Data Processor - Completed")
    print("=" * 80)


if __name__ == "__main__":
    main()
