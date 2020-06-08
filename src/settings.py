from configparser import ConfigParser
from os import path

parser = ConfigParser()

#read settings file
parser.read(f'{path.dirname(path.dirname(path.abspath(__file__)))}/settings.ini')

#extract settings
DEBUG = parser.getboolean('aws','debug')
MAX_CONCURRENT_INTHUB_LIMIT = parser.getint('aws', 'max_concurrent_inthub_limit')
FETCH_LINKS = parser.getboolean('aws', 'fetch_links')
DOWNLOAD_DAY = parser.get('aws', 'download_day')
if DOWNLOAD_DAY.strip() == '' or  DOWNLOAD_DAY.strip().lower() == 'none':
    DOWNLOAD_DAY = None
COPERNICUS_USERNAME = parser.get('aws', 'copernicus_username')
COPERNICUS_PASSWORD = parser.get('aws', 'copernicus_password')
LOCK_FILE = parser.get('aws', 'lock_file')
INCLUDE_TILES_FILE = parser.get('aws', 'include_tiles_file')
DOWNLOADS_PATH = parser.get('aws', 'downloads_path')
LOGS_PATH = parser.get('aws', 'logs_path')
S3_UPLOAD_BUCKET = parser.get('aws', 's3_upload_bucket')
S3_LOG_BUCKET = parser.get('aws', 's3_log_bucket')
DB_NAME = parser.get('aws', 'db_name')
DB_USER = parser.get('aws', 'db_user')
DB_PASS = parser.get('aws', 'db_pass')
DB_PORT = parser.getint('aws', 'db_port')
DB_HOST = parser.get('aws', 'db_host')

