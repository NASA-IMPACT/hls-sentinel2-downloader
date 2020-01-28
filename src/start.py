from itertools import islice
from os import environ

from copernicus import Copernicus
from s3_uploader import S3Uploader
from downloader import Downloader


# Uploader to the S3 bucket.
uploader = S3Uploader(bucket=environ['UPLOAD_BUCKET'])


total_downloads = 0


def on_download_error(downloader, gid):
    print('ERRRRRRRRORRRR')

    global total_downloads
    total_downloads += 1
    if total_downloads == 50:
        downloader.stop_listening()


# After each file downloads, we want to upload it to S3 bucket.
def on_download_complete(downloader, gid):
    filename = downloader.get_download_filename(gid)
    print(f'Download complete: {filename}')
    uploader.upload_file(filename)
    print(f'Upload complete: {filename}')

    global total_downloads
    total_downloads += 1
    if total_downloads == 50:
        downloader.stop_listening()


# Downloader that handles asynchronous downloads.
downloader = Downloader(
    on_download_error=on_download_error,
    on_download_complete=on_download_complete
)


# Copernicus Search API
copernicus = Copernicus(
    start_date='2020-01-19T00:00:00.000Z',
    end_date='2020-01-20T00:00:00.000Z'
)


# Let's read in each url and download them.
for entry in islice(copernicus.read_feed(), 50):
    url = entry['link'][0]['href']
    print(f'Downloading: {url}')
    downloader.start_download(url)
