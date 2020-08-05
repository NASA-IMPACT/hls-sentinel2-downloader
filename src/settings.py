from configparser import ConfigParser
from os import path

parser = ConfigParser()

# read settings file
parser.read(
    f'{path.dirname(path.dirname(path.abspath(__file__)))}/settings.ini')

# extract settings
DEBUG = parser.getboolean('aws', 'debug')
MAX_CONCURRENT_INTHUB_LIMIT = parser.getint(
    'aws', 'max_concurrent_inthub_limit')
FETCH_LINKS = parser.getboolean('aws', 'fetch_links')
DOWNLOAD_DAY = parser.get('aws', 'download_day')
if DOWNLOAD_DAY.strip() == '' or DOWNLOAD_DAY.strip().lower() == 'none':
    DOWNLOAD_DAY = None
DOWNLOAD_BY_DAY = parser.getboolean('aws', 'download_by_day')
COPERNICUS_USERNAME = parser.get('aws', 'copernicus_username')
COPERNICUS_PASSWORD = parser.get('aws', 'copernicus_password')
SCIHUB_USERNAME = parser.get('aws', 'scihub_username')
SCIHUB_PASSWORD = parser.get('aws', 'scihub_password')
USE_SCIHUB_TO_FETCH_LINKS = parser.getboolean(
    'aws', 'use_scihub_to_fetch_links')
LOCK_FILE = parser.get('aws', 'lock_file')
INCLUDE_TILES_FILE = parser.get('aws', 'include_tiles_file')
DOWNLOADS_PATH = parser.get('aws', 'downloads_path')
LOGS_PATH = parser.get('aws', 'logs_path')
S3_UPLOAD_BUCKET = parser.get('aws', 's3_upload_bucket')
S3_LOG_BUCKET = parser.get('aws', 's3_log_bucket')
WGET_TIMEOUT = parser.get('aws', 'wget_timeout')
WGET_TRIES = parser.get('aws', 'wget_tries')
WGET_WAITRETRY = parser.get('aws', 'wget_waitretry')
DB_NAME = parser.get('aws', 'db_name')
DB_USER = parser.get('aws', 'db_user')
DB_PASS = parser.get('aws', 'db_pass')
DB_PORT = parser.getint('aws', 'db_port')
DB_HOST = parser.get('aws', 'db_host')
