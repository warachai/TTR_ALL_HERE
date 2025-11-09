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


# ==============================================================================
# CONSTANTS - FTP CONFIGURATION
# ==============================================================================
FTP_HOST = '10.19.67.204'
FTP_PATH = '/var/merlin/cfgs/Siyarat/DISC'
FTP_USERNAME = 'merlin'
FTP_PASSWORD = 'merlin'
FTP_LOCAL_DIR = r'D:\i\warachai\MY_RESOURCE\MY_SCRIPT\TTR_Feature_Input\DISC_downloads'


# ==============================================================================
# CONSTANTS - JIRA CONFIGURATION
# ==============================================================================
JIRA_BASE_URL = 'https://jira.seagate.com'
JIRA_API_ENDPOINT = '/jira/rest/api/2/search'
JIRA_PROJECTS = ['SUMMIT', 'MARLINCT', 'MBP', 'DORADO']
JIRA_FIELDS = 'key,summary,status,assignee,created,customfield_35600'
JIRA_MAX_RESULTS = 50
JIRA_OUTPUT_FILE = r'D:/i/warachai/MY_RESOURCE/MY_SCRIPT/TTR_Feature_Input/jira_issues.csv'


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
    'Assignee',
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
    if os.path.exists(local_dir) and os.listdir(local_dir):
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
def construct_jira_url(base_url, endpoint, project):
    """
    Constructs a Jira REST API URL with the given base URL, endpoint, and project.

    Args:
        base_url (str): The base URL of the Jira instance.
        endpoint (str): The API endpoint.
        project (str): The project name for JQL query.

    Returns:
        str: The constructed URL.
    """
    jql_query = f"project={project} ORDER BY created DESC"
    
    query_params = {
        "jql": jql_query,
        "fields": JIRA_FIELDS,
        "maxResults": JIRA_MAX_RESULTS
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
    """
    Handles the REST API result fetched via Selenium by processing 
    the JSON response and saving it to a CSV file.

    Args:
        project (str): The project name being processed.
        driver (webdriver): The Selenium WebDriver instance.
    """
    try:
        # Get the page source (JSON response)
        page_source = driver.find_element("tag name", "pre").text

        # Parse the JSON response
        data = json.loads(page_source)
        print(f"Total issues for {project}: {data.get('total')}\n")

        # Prepare data for CSV
        csv_data = []

        for issue in data.get("issues", []):
            try:
                key = issue["key"]
                fields = issue["fields"]
                summary = fields.get("summary", "No Summary")
                status = fields.get("status", {}).get("name", "No Status")
                assignee = fields.get("assignee", {}).get("displayName", "Unassigned")
                created = fields.get("created", "No Created Date")
                custom_field_value = fields.get("customfield_35600", [{}])[0].get("value", "Others") if fields.get("customfield_35600") else "Others"

                csv_data.append([project, key, status, assignee, created, summary, custom_field_value])
            except Exception as e:
                print(f"Error processing issue: {e}")

        # Determine write mode (create or append)
        write_headers = not os.path.exists(JIRA_OUTPUT_FILE)

        # Write or append data to CSV
        with open(JIRA_OUTPUT_FILE, "a" if not write_headers else "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            if write_headers:
                writer.writerow(CSV_HEADERS)
            writer.writerows(csv_data)

        print(f"Data for {project} saved to {JIRA_OUTPUT_FILE}\n")
    except Exception as e:
        print(f"Error handling REST API result for {project}: {e}")


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


def scrape_jira_issues():
    """
    Scrape Jira issues for all configured projects and save to CSV.
    """
    driver = setup_chrome_driver()
    
    try:
        # First, load the base domain to set cookies
        print(f"Accessing base domain: {JIRA_BASE_URL}")
        driver.get(JIRA_BASE_URL)
        time.sleep(10)
        
        # Process each project
        for project in JIRA_PROJECTS:
            print(f"Processing project: {project}")
            query_url = construct_jira_url(JIRA_BASE_URL, JIRA_API_ENDPOINT, project)
            driver.get(query_url)
            time.sleep(10)
            handle_rest_api_result(project, driver)
            time.sleep(5)
    
    finally:
        driver.quit()
        print("Jira scraping completed.")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
def main():
    """
    Main function to orchestrate FTP download and Jira scraping.
    """
    print("=" * 80)
    print("TTR Data Processor - Starting")
    print("=" * 80)
    
    # Step 1: Download FTP files
    print("\n[1/2] Downloading DISC files from FTP...")
    try:
        download_ftp_files()
        print("FTP download completed successfully.")
    except Exception as e:
        print(f"Error during FTP download: {e}")
    
    # Step 2: Scrape Jira issues
    print("\n[2/2] Scraping Jira issues...")
    try:
        scrape_jira_issues()
        print("Jira scraping completed successfully.")
    except Exception as e:
        print(f"Error during Jira scraping: {e}")
    
    print("\n" + "=" * 80)
    print("TTR Data Processor - Completed")
    print("=" * 80)


if __name__ == "__main__":
    main()
