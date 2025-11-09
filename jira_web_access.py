from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import os

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
    
def construct_jira_url(base_url, endpoint, project):
    """
    Constructs a Jira REST API URL with the given base URL, endpoint, and JQL query.

    Args:
        base_url (str): The base URL of the Jira instance.
        endpoint (str): The API endpoint.
        jql_query (str): The JQL query string.

    Returns:
        str: The constructed URL.
    """
    from urllib.parse import urlencode

    jql_query = f"project={project} ORDER BY created DESC"

    FIELDS = "key,summary,status,assignee,created,customfield_35600"
    PAGE = 50

    query_params = {
        "jql": jql_query,
        "fields": FIELDS,
        "maxResults": PAGE
    }
    return f"{base_url}{endpoint}?{urlencode(query_params)}"

def find_keys(d, target):
    keys = []
    for k, v in d.items():
        if isinstance(v, dict):
            keys.extend(find_keys(v, target))
        elif v in target:
            keys.append(k)
    return keys

# Modify the handle_rest_api_result function to create or append data to the CSV file
def handle_rest_api_result(project, driver):
    """
    Handles the REST API result fetched via Selenium by processing the JSON response and saving it to a CSV file.

    Args:
        driver (webdriver): The Selenium WebDriver instance.
    """
    try:
        # Get the page source (JSON response)
        page_source = driver.find_element("tag name", "pre").text

        # Parse the JSON response
        data = json.loads(page_source)
        print(f"Total issues: {data.get('total')}\n")

        # Prepare data for CSV
        csv_data = []
        csv_headers = ["Project", "Key", "Status", "Assignee", "Created", "Summary", "Improvement Type"]

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
        file_path = r"D:/i/warachai/MY_RESOURCE/MY_SCRIPT/TTR_Feature_Input/jira_issues.csv"
        write_headers = not os.path.exists(file_path)

        # Write or append data to CSV
        with open(file_path, "a" if not write_headers else "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            if write_headers:
                writer.writerow(csv_headers)
            writer.writerows(csv_data)

        print("Data saved to jira_issues.csv\n")
    except Exception as e:
        print(f"Error handling REST API result: {e}")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.implicitly_wait(10)
driver.set_page_load_timeout(30)  # Set page load timeout to 30 seconds

# First, load the base domain to set cookies
base_domain = "https://jira.seagate.com"
print(f"Accessing base domain: {base_domain}")
driver.get(base_domain)
time.sleep(10)
# Update the JQL query to filter issues with the tag 'TTR/YIP'
for project in ["SUMMIT", "MARLINCT", "MBP", "DORADO"]:
    query = construct_jira_url(base_domain, "/jira/rest/api/2/search", project)
    driver.get(query)
    time.sleep(10)
    handle_rest_api_result(project, driver)
    time.sleep(5)

driver.quit()
pass