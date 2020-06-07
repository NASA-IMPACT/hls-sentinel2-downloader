#import external packages
from os import path
from datetime import datetime
from boto3 import client, resource as boto_resource, s3
from botocore.exceptions import ClientError

#import internal functions
from settings import S3_UPLOAD_BUCKET, DEBUG
from log_manager import log
from thread_manager import lock, upload_queue
from models import status, db

s3_client = client('s3')

transfer_config = s3.transfer.TransferConfig(
    multipart_threshold=1024 * 25,
    max_concurrency=10,
    multipart_chunksize=1024 * 25,
    use_threads=True,
)

def get_key(file_path, date):
    '''
        construct s3 upload location
    '''
    key = f"{date.strftime('%m-%d-%Y')}/{path.basename(file_path)}"
    return key


def s3_file_exists(file_path, date):
    '''
        check if file already exists in S3
    '''
    key =  get_key(file_path,date)
    s3 = boto_resource('s3')

    try:
        s3.Object(S3_UPLOAD_BUCKET, key).load()
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
    
    return False


def s3_upload_file(file_path, date):
    '''
        upload a file to S3
    '''
    global transfer_config

    key =  get_key(file_path,date)

    try:
        if(DEBUG):
            print(f'{str(datetime.now())}, uploading file {file_path} to {S3_UPLOAD_BUCKET}/{key}')
        log(f'uploading file {file_path} to {S3_UPLOAD_BUCKET}/{key}','status')

        s3_client.upload_file(file_path, S3_UPLOAD_BUCKET, key, Config=transfer_config)
        lock.acquire()
        db.connect()
        last_file_uploaded_time = status.get(status.key_name == 'last_file_uploaded_time')
        last_file_uploaded_time.value = str(datetime.now())
        last_file_uploaded_time.save()
        db.close()
        lock.release()

        upload_queue.put({"file_path":file_path,"success":True})

    except Exception as e:
        if(DEBUG):
                print(f'{str(datetime.now())}, error during uploading file: {file_path} to {S3_UPLOAD_BUCKET} {str(e)}')
        log(f'error during uploading file: {file_path} to {S3_UPLOAD_BUCKET} {str(e)}','error')
        upload_queue.put({"file_path":file_path,"success":False})
