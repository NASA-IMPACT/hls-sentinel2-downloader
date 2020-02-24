from multiprocessing import Process, Queue, Lock
from itertools import islice
from datetime import datetime, timedelta

from helpers.copernicus import Copernicus
from helpers.downloader import Downloader
from upload_worker import upload_worker

from setup_db import setup_db
from serializer import Serializer
from models.job import job, JobStatus
from models.job_log import job_log
from models.granule import granule, DownloadStatus


class Workflow:
    def __init__(self,
                 date, review_number=0,
                 max_downloads=None, max_upload_workers=20):
        self.max_downloads = max_downloads
        self.total_downloads = 0
        self.review_number = review_number
        self.upload_queue = Queue()
        self.lock = Lock()

        # Setup the database connection
        self.db_engine = setup_db()
        self.db_connection = self.db_engine.connect()
        self.job_serializer = Serializer(self.db_connection, job)
        self.job_log_serializer = Serializer(self.db_connection, job_log)
        self.granule_serializer = Serializer(self.db_connection, granule)

        # Downloader that handles asynchronous downloads.
        self.downloader = Downloader(
            on_download_start=self._on_download_start,
            on_download_error=self._on_download_error,
            on_download_complete=self._on_download_complete,
            callback_args=(self.lock,)
        )

        # Copernicus Search API
        self.date = date
        end_date = (date + timedelta(days=1))
        start_date = self._get_start_date(date, end_date)

        self.copernicus = Copernicus(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

        # Upload workers
        self.upload_processes = [
            Process(target=upload_worker, args=(self.upload_queue, i))
            for i in range(max_upload_workers)
        ]

    def _get_start_date(self, default_start_date, end_date):
        last_granule = self.granule_serializer.first(
            params={
                'downloaded_at.gte': default_start_date,
                'downloaded_at.le': end_date,
            },
            order_by=[('copernicus_ingestion_date' 'desc')],
        )
        if last_granule is None:
            return default_start_date
        return last_granule['downloaded_at']

    def start(self, parent_state):
        # Start a new job in the database.
        self.job_id = self.job_serializer.post({
            'job_name': 'Sentinel-2 Downloader',
            'start_time': datetime.now(),
            'date_handled': self.date,
            'status': JobStatus.started,
            'needs_review': True,
            'review_number': self.review_number,
        })
        parent_state.job_id = self.job_id
        self.at_least_one_failed_download = False

        # Start processes responsible for uploading downloaded files to S3
        # in a concurrent fashion.
        [upload_process.start() for upload_process in self.upload_processes]

        # Let's read in each url and download them.
        count = 0
        for product in islice(self.copernicus.read_feed(), self.max_downloads):
            # Check if granule is already in the database.
            existing = self.granule_serializer.get(product.id)

            if existing is None:
                # If not, add it to the database.
                self.granule_serializer.post({
                    'uuid': product.id,
                    'title': product.title,
                    'copernicus_ingestion_date': product.ingestion_date,
                    'validated': False,
                    'downloader_job_id': self.job_id,
                    'download_status': DownloadStatus.NOT_STARTED,
                })
            elif existing['download_status'] not in ['ERROR', 'INVALID']:
                # If it was not a failed download, just skip.
                continue

            # And start the download.
            # url = product.get_download_link()
            # print(f'Downloading: {url}')
            self.downloader.start_download(product)
            count += 1

        # We need to set max_downloads, if it was not provided by the user.
        # This is needed so that we can send an DONE message to S3 uploader
        # when all download completes.
        self.lock.acquire()
        if self.max_downloads is None:
            self.max_downloads = count
        # Of course, if all downloads have already been completed at this
        # point, we need to handle that case as well.
        if self.total_downloads == self.max_downloads:
            self.upload_queue.put('DONE')
        self.lock.release()

        # Join the separately running upload processes.
        [upload_process.join() for upload_process in self.upload_processes]

        parent_state.completed = True

        # At this point, we assume that all downloads and uploads have been
        # completed for this job.

        # Stop listening for any download notifications.
        self.downloader.stop_listening()

        # Set the job status to success.
        self.job_serializer.put(self.job_id, {
            'end_time': datetime.now(),
            'needs_review': self.at_least_one_failed_download,
            'status': JobStatus.SUCCESS
        })

    def _on_download_start(self, downloader, gid, lock):
        product = downloader.get_download_product(gid)
        self.granule_serializer.put(product.id, {
            'download_status': DownloadStatus.DOWNLOADING
        })

    def _on_download_error(self, downloader, gid, lock):
        print('Error downloading: ', *downloader.get_download_error(gid))
        product = downloader.get_download_product(gid)

        self.at_least_one_failed_download = True

        # Download status = ERROR
        self.granule_serializer.put(product.id, {
            'download_status': DownloadStatus.ERROR
        })

        # If these are all the downloads, trigger the upload processes to quit.
        lock.acquire()
        self.total_downloads += 1
        if self.total_downloads == self.max_downloads:
            self.upload_queue.put('DONE')
        lock.release()

    def _on_download_complete(self, downloader, gid, lock):
        product = downloader.get_download_product(gid)

        # After each file downloads, we want to upload it to S3 bucket.
        filename = downloader.get_download_filename(gid)
        self.upload_queue.put((product.id, filename))

        # If these are all the downloads, trigger the upload processes to quit.
        lock.acquire()
        self.total_downloads += 1
        if self.total_downloads == self.max_downloads:
            self.upload_queue.put('DONE')
        lock.release()
