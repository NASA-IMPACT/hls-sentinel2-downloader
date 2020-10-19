# import external packages
from os import walk, path
from boto3 import client, s3
from logging import getLogger, handlers as log_handlers, DEBUG
from datetime import datetime, timedelta
from colorama import Fore

# import internal functions
from settings import LOGS_PATH, S3_LOG_BUCKET, DEBUG

s3_client = client('s3')


transfer_config = s3.transfer.TransferConfig(
    multipart_threshold=1024 * 25,
    max_concurrency=10,
    multipart_chunksize=1024 * 25,
    use_threads=True,
)

'''
    create loggers, rotate files per 1 MB, store upto 50 previous logs files
'''

status_logger = getLogger('StatusLogger')
status_logger.setLevel(DEBUG)
status_handler = log_handlers.RotatingFileHandler(
    f'{LOGS_PATH}/status_logs.out', maxBytes=1000000, backupCount=50)
status_logger.addHandler(status_handler)

links_logger = getLogger('LinksLogger')
links_logger.setLevel(DEBUG)
links_logger.addHandler(log_handlers.RotatingFileHandler(
    f'{LOGS_PATH}/links_logs.out', maxBytes=1000000, backupCount=50))

downloads_logger = getLogger('DownloadsLogger')
downloads_logger.setLevel(DEBUG)
downloads_logger.addHandler(log_handlers.RotatingFileHandler(
    f'{LOGS_PATH}/downloads_logs.out', maxBytes=1000000, backupCount=50))

metrics_logger = getLogger('MetricsLogger')
metrics_logger.setLevel(DEBUG)
metrics_logger.addHandler(log_handlers.RotatingFileHandler(
    f'{LOGS_PATH}/metrics_logs.out', maxBytes=1000000, backupCount=50))

error_logger = getLogger('ErrorLogger')
error_logger.setLevel(DEBUG)
error_logger.addHandler(log_handlers.RotatingFileHandler(
    f'{LOGS_PATH}/error_logs.out', maxBytes=1000000, backupCount=50))


def log(msg, type):
    '''
        based on type decide the log format
    '''

    if type == 'error':
        msg=f'Error:{msg}'

    log_msg = f'{str(datetime.now())}, {msg}'

    if type == 'status':
        status_logger.info(log_msg)
    elif type == 'links':
        links_logger.info(log_msg)
    elif type == 'downloads':
        downloads_logger.info(log_msg)
    elif type == 'metrics':
        metrics_logger.info(msg)
    elif type == 'error':
        # log error to both status and error loggers
        status_logger.info(log_msg)
        error_logger.info(log_msg)
    

    if DEBUG and type == 'status':
        print(log_msg)
    elif DEBUG and type == 'error':
        print(Fore.RED + log_msg)


def s3_upload_logs():
    '''
        upload logs to S3
    '''

    log(f'starting logs upload', 'status')
    global transfer_config

    now = datetime.now()
    for (root, dirs, files) in walk(LOGS_PATH):
        for item in files:

            # upload logs which were modifed in last 60 minutes
            modify_date = datetime.fromtimestamp(path.getmtime(f'{LOGS_PATH}/{item}'))
            modify_date_30minutes_ago = now + timedelta(minutes=-60)

            if modify_date >= modify_date_30minutes_ago:
                if 'status' in item:
                    key = f'status/{item}'
                elif 'links' in item:
                    key = f'links/{item}'
                elif 'downloads' in item:
                    key = f'downloads/{item}'
                elif 'metrics' in item:
                    key = f'metrics/{item}'
                elif 'error' in item:
                    key = f'error/{item}'

                try:
                    s3_client.upload_file(
                        f'{LOGS_PATH}/{item}', S3_LOG_BUCKET, key, Config=transfer_config)
                    log(f'{LOGS_PATH}/{item} uploaded', 'status')
                except Exception as e:
                    log(f'error during uploading logs: {str(e)}', 'error')

    log(f'finished logs upload', 'status')