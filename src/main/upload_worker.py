from os import environ, remove
from helpers.s3_uploader import S3Uploader


def upload_worker(queue, worker_id):
    # Uploader to the S3 bucket.
    uploader = S3Uploader(bucket=environ['UPLOAD_BUCKET'])
    while True:
        message = queue.get()
        if message == 'DONE':
            # Put in back for other workers.
            queue.put('DONE')
            break

        filename = message
        print(f'Uploading: {filename} by #{worker_id}')
        uploader.upload_file(filename)
        remove(filename)
        print(f'Uploaded: {filename}')
