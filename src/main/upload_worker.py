from os import environ, remove
from datetime import datetime
import hashlib

from helpers.s3_uploader import S3Uploader
from helpers.logger import Logger
from setup_db import setup_db
from models.granule import granule, DownloadStatus
from serializer import Serializer


def upload_worker(queue, job_id, worker_id):
    # Uploader to the S3 bucket.
    db_connection = setup_db().connect()
    logger = Logger(db_connection, job_id)
    bucket_name = environ.get('UPLOAD_BUCKET')

    try:
        logger.info(f'Creating S3 uploader #{worker_id}')
        uploader = S3Uploader(bucket=bucket_name)
        granule_serializer = Serializer(db_connection, granule)

        while True:
            message = queue.get()
            if message == 'DONE':
                # Put in back for other workers.
                queue.put('DONE')
                break

            product_id, filename = message

            try:
                checksum = hashlib.md5(
                    open(filename, 'rb').read()
                ).hexdigest().upper()

                # Download status = SUCCESS
                granule_serializer.put(product_id, {
                    'download_status': DownloadStatus.SUCCESS,
                    'downloaded_at': datetime.now(),
                    'validated': False,
                    'checksum': checksum,
                    's3_location': f'{bucket_name}/filename'
                })

                logger.info(f'Uploading {product_id} at #{worker_id}',
                            f'Filename: {filename}')
                uploader.upload_file(filename)
                remove(filename)

                logger.info(f'Uploaded {product_id} at #{worker_id}',
                            f'Filename: {filename}')
            except Exception:
                logger.exception()
    except Exception:
        logger.exception()
