from os import environ, remove
from datetime import datetime
from helpers.s3_uploader import S3Uploader

from setup_db import setup_db
from models.granule import granule, DownloadStatus
from serializer import Serializer


def upload_worker(queue, worker_id):
    # Uploader to the S3 bucket.
    uploader = S3Uploader(bucket=environ['UPLOAD_BUCKET'])
    db_engine = setup_db()
    db_connection = db_engine.connect()
    granule_serializer = Serializer(db_connection, granule)

    while True:
        message = queue.get()
        if message == 'DONE':
            # Put in back for other workers.
            queue.put('DONE')
            break

        product_id, filename = message

        # Download status = SUCCESS
        granule_serializer.put(product_id, {
            'download_status': DownloadStatus.SUCCESS,
            'downloaded_at': datetime.now(),
        })

        print(f'Uploading: {filename} by #{worker_id}')
        uploader.upload_file(filename)
        remove(filename)
        print(f'Uploaded: {filename}')
