"""
s3_uploader.py
Created On: Jan 28, 2020
Created By: Bibek Dahal
"""
from os import path
from boto3 import client, s3


class S3Uploader:
    """
    Uploader for a S3 bucket.
    """
    def __init__(self, bucket):
        """
        bucket: Bucket name in S3 to upload files to.
        """
        self.bucket = bucket
        if self.bucket is None:
            return
        self.client = client('s3')
        self.transfer_config = s3.transfer.TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True,
        )

    def upload_file(self, filename, key=None):
        """
        Start uploading to a file. This method is synchronous.

        filename: Local path of the file to upload.
        key: S3 key (path).
             If None, key will be same as the basename of the local file.
        """
        if self.bucket is None:
            return

        if key is None:
            key = path.basename(filename)
        self.client.upload_file(filename, self.bucket, key,
                                Config=self.transfer_config)
