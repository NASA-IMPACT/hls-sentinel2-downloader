from multiprocessing import Process, Queue, Lock
from itertools import islice

from helpers.copernicus import Copernicus
from helpers.downloader import Downloader
from upload_worker import upload_worker


class Workflow:
    def __init__(self,
                 start_date, end_date,
                 max_downloads=None, max_upload_workers=20):
        self.max_downloads = max_downloads
        self.total_downloads = 0

        self.upload_queue = Queue()
        self.lock = Lock()

        # Downloader that handles asynchronous downloads.
        self.downloader = Downloader(
            on_download_error=self._on_download_error,
            on_download_complete=self._on_download_complete,
            callback_args=(self.lock,)
        )

        # Copernicus Search API
        self.copernicus = Copernicus(start_date=start_date, end_date=end_date)

        # Upload workers
        self.upload_processes = [
            Process(target=upload_worker, args=(self.upload_queue, i))
            for i in range(max_upload_workers)
        ]

    def start(self):
        [upload_process.start() for upload_process in self.upload_processes]

        # Let's read in each url and download them.
        count = 0
        for product in islice(self.copernicus.read_feed(), self.max_downloads):
            url = product.get_download_link()
            print(f'Downloading: {url}')
            self.downloader.start_download(product)
            count += 1

        self.lock.acquire()
        if self.max_downloads is None:
            self.max_downloads = count
        if self.total_downloads == self.max_downloads:
            self.upload_queue.put('DONE')
        self.lock.release()

        [upload_process.join() for upload_process in self.upload_processes]
        self.downloader.stop_listening()

    def _on_download_error(self, downloader, gid, lock):
        print('Error downloading: ', *downloader.get_download_error(gid))

        lock.acquire()
        self.total_downloads += 1
        if self.total_downloads == self.max_downloads:
            self.upload_queue.put('DONE')
        lock.release()

    # After each file downloads, we want to upload it to S3 bucket.
    def _on_download_complete(self, downloader, gid, lock):
        # checksum_valid = downloader.check_checksum(gid)
        filename = downloader.get_download_filename(gid)
        print(f'Download complete: {filename}')
        self.upload_queue.put(filename)

        lock.acquire()
        self.total_downloads += 1
        if self.total_downloads == self.max_downloads:
            self.upload_queue.put('DONE')
        lock.release()
