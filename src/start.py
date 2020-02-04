from itertools import islice
from os import environ, remove
from time import time
from multiprocessing import Process, Queue, Lock

from copernicus import Copernicus
from s3_uploader import S3Uploader
from downloader import Downloader


def upload_worker(queue):
    # Uploader to the S3 bucket.
    uploader = S3Uploader(bucket=environ['UPLOAD_BUCKET'])
    while True:
        message = queue.get()
        if message == 'DONE':
            break

        filename = message
        uploader.upload_file(filename)
        remove(filename)


max_downloads = 30
total_downloads = 0


def main():
    upload_queue = Queue()
    lock = Lock()

    def on_download_error(downloader, gid, lock):
        print('Error downloading: ', *downloader.get_download_error(gid))

        lock.acquire()
        global total_downloads
        total_downloads += 1
        lock.release()
        if total_downloads == max_downloads:
            upload_queue.put('DONE')

    # After each file downloads, we want to upload it to S3 bucket.
    def on_download_complete(downloader, gid, lock):
        filename = downloader.get_download_filename(gid)
        print(f'Download complete: {filename}')
        upload_queue.put(filename)

        lock.acquire()
        global total_downloads
        total_downloads += 1
        lock.release()
        if total_downloads == max_downloads:
            upload_queue.put('DONE')

    # Downloader that handles asynchronous downloads.
    downloader = Downloader(
        on_download_error=on_download_error,
        on_download_complete=on_download_complete,
        callback_args=(lock,)
    )

    # Copernicus Search API
    copernicus = Copernicus(
        start_date='2020-01-28T00:00:00.000Z',
        end_date='2020-01-29T00:00:00.000Z'
    )

    upload_process = Process(target=upload_worker, args=(upload_queue,))
    upload_process.start()

    start_time = time()
    print('Starting downloads', start_time, flush=True)
    # Let's read in each url and download them.
    for entry in islice(copernicus.read_feed(), max_downloads):
        url = entry['link'][0]['href']
        print(f'Downloading: {url}')
        downloader.start_download(url)

    upload_process.join()
    downloader.stop_listening()

    end_time = time()
    print('Finishing downloads', end_time, flush=True)
    print('Total time', end_time - start_time, flush=True)


if __name__ == '__main__':
    main()
