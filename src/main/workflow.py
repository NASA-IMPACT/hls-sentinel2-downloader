from multiprocessing import Process, Queue, Lock
from datetime import datetime, timedelta
from time import sleep

from helpers.copernicus import Copernicus
from helpers.downloader import Downloader
from upload_worker import upload_worker

from serializer import Serializer
from models.job import job, JobStatus
from models.granule import granule, DownloadStatus


class Workflow:
    def __init__(self,
                 db_connection, logger,
                 date,
                 max_downloads=None, max_upload_workers=20,
                 allow_repeat=False):
        self.max_downloads = max_downloads
        self.max_upload_workers = max_upload_workers
        self.total_downloads = 0
        self.upload_queue = Queue()
        self.lock = Lock()
        self.allow_repeat = allow_repeat

        # Setup the database connection
        self.db_connection = db_connection
        self.job_serializer = Serializer(self.db_connection, job)
        self.granule_serializer = Serializer(self.db_connection, granule)
        self.logger = logger
        self.date = date

        self.logger.info('Creating a workflow')

        # Downloader that handles asynchronous downloads.
        self.logger.info('Creating aria2 downloader client')
        self.downloader = Downloader(
            on_download_error=self._on_download_error,
            on_download_complete=self._on_download_complete,
            callback_args=(self.lock,)
        )

        # Copernicus Search API
        self.logger.info('Creating copernicus API connector')
        end_date = (self.date + timedelta(days=1))
        start_date = self.date  # self._get_start_date(self.date, end_date)

        self.copernicus = Copernicus(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            rows_per_query=30,
        )

    def start(self, parent_state):
        # Start a new job in the database.
        self.job_id = self.job_serializer.post({
            'job_name': 'Sentinel-2 Downloader',
            'start_time': datetime.now(),
            'date_handled': self.date,
            'status': JobStatus.STARTED,
        })

        self.logger.set_job_id(self.job_id)
        self.logger.info('Starting workflow')

        # Upload workers
        self.logger.info('Creating S3 upload processes')
        self.upload_processes = [
            Process(target=upload_worker,
                    args=(self.upload_queue, self.job_id, i))
            for i in range(self.max_upload_workers)
        ]

        parent_state.job_id = self.job_id
        self.at_least_one_failed_download = False

        # Start processes responsible for uploading downloaded files to S3
        # in a concurrent fashion.
        self.logger.info('S3 upload processes started')
        [upload_process.start() for upload_process in self.upload_processes]

        # Let's read in each url and download them.
        count = 0
        self.logger.info('Fetching granules info from Copernicus',
                         f'Reading for date: {self.date.isoformat()}')

        for product in self.copernicus.read_feed():
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
            elif not self.allow_repeat and \
                    existing['download_status'] not in ['ERROR', 'INVALID']:
                # If it was not a failed download, just skip.
                continue

            # And start the download.
            url = product.get_download_link()
            self.logger.info(f'Starting granule download {product.id}',
                             f'URL: {url}')

            self.downloader.start_download(product)
            self.granule_serializer.put(product.id, {
                'download_status': DownloadStatus.DOWNLOADING
            })

            count += 1
            if self.max_downloads is not None and count >= self.max_downloads:
                break

            while count - self.total_downloads >= 30:
                sleep(5)

        # Set max_downloads to actual number of downloads triggered.
        # This is needed so that we can send an DONE message to S3 uploader
        # when all download completes.
        self.lock.acquire()
        self.max_downloads = count
        # Of course, if all downloads have already been completed at this
        # point, we need to handle that case as well.
        if self.total_downloads == self.max_downloads:
            self.upload_queue.put('DONE')
        self.lock.release()

        # Join the separately running upload processes.
        [upload_process.join() for upload_process in self.upload_processes]

        self.logger.info('All granules downloaded',
                         f'Total granules processed: {self.total_downloads}')
        parent_state.completed = True

        # At this point, we assume that all downloads and uploads have been
        # completed for this job.

        # Stop listening for any download notifications.
        self.downloader.stop_listening()

        # Set the job status to success.
        self.job_serializer.put(self.job_id, {
            'end_time': datetime.now(),
            'status': JobStatus.SUCCESS
        })

        self.logger.info('Stopping workflow')
        self.logger.set_job_id(None)

    def _on_download_error(self, downloader, gid, lock):
        product = downloader.get_download_product(gid)

        error_message, error_code = downloader.get_download_error(gid)
        self.logger.error(f'Download error {product.id}',
                          f'Error Code: {error_code}\n{error_message}')
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
        self.logger.info(f'Download complete {product.id}')

        # After each file downloads, we want to upload it to S3 bucket.
        filename = downloader.get_download_filename(gid)
        self.upload_queue.put((product.id, filename))

        # If these are all the downloads, trigger the upload processes to quit.
        lock.acquire()
        self.total_downloads += 1
        if self.total_downloads == self.max_downloads:
            self.upload_queue.put('DONE')
        lock.release()
