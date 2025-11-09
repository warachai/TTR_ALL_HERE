import requests
import json
from ftplib import FTP
import os

def download_ftp_files(ftp_host, ftp_path, local_dir, username='merlin', password='merlin'):
    """
    Download all files from a specified FTP directory to a local directory if the directory does not already exist.

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

# Example usage:
ftp_host = '10.19.67.204'
ftp_path = '/var/merlin/cfgs/Siyarat/DISC'
local_dir = r'D:\i\warachai\MY_RESOURCE\MY_SCRIPT\TTR_Feature_Input\DISC_downloads'

download_ftp_files(ftp_host, ftp_path, local_dir)
