# import external packages
from time import sleep
from multiprocessing import Process
from os import path, listdir
from datetime import datetime, date, timedelta
from ntpath import basename
from sys import exit
from colorama import init as colorama_init, Fore, Back, Style
from termcolor import colored
from schedule import every, run_pending
from re import search
from peewee import OperationalError

# import custom functions
from models import status,  granule, db,  db_connect, db_close
from download_manager import add_download_url, get_active_urls, get_waiting_urls, pause_download, resume_download
from s3_uploader import s3_upload_file, s3_file_exists
from utils import get_checksum_local, kill_downloader, clean_up_downloads, get_memory_usage, file_is_locked, get_folder_size, remove_file, get_download_folder_size
from log_manager import log, s3_upload_logs
from links_manager import fetch_links
from metrics_collector import collect_metrics
from settings import DOWNLOADS_PATH, DEBUG, DOWNLOAD_DAY, DOWNLOAD_BY_DAY, LOCK_FILE, FETCH_LINKS, MAX_CONCURRENT_INTHUB_LIMIT, USE_SCIHUB_TO_FETCH_LINKS
import thread_manager


# required to print colors in both UNIX and Windows OS
colorama_init(autoreset=True)
fetch_links_worker = None
upload_orphan_downloads_worker = None
download_file_worker = None


def check_downloads_folder_size():
    '''
        check size of download folder and take action if it is filling up
    '''
    global upload_orphan_downloads_worker

    download_folder_size = get_download_folder_size()

    if upload_orphan_downloads_worker == None or upload_orphan_downloads_worker.isAlive() == False:
        if download_folder_size > 100:
            upload_orphan_downloads_worker = thread_manager.Thread(
                name="upload_orphan_downloads", target=upload_orphan_downloads, args=())
            upload_orphan_downloads_worker.start()

    if download_folder_size > 600:
        # download folder's size has reached above 500GB that means something must be terribly went wrong
        # it should never reach to this size under normal operating conditions
        # TODO: raise the alert

        log(f'download folder size reached above 600GB, cleaning up old downloads', 'error')
        clean_up_downloads()


def check_link_fetcher():
    '''
        check if the link fetcher is running or not, if not start it again
    '''
    if FETCH_LINKS == True and (fetch_links_worker is None or fetch_links_worker.isAlive() == False):
        thread_manager.Thread(name="start_links_fetch",
                              target=start_links_fetch, args=()).start()


def start_links_fetch():
    '''
        start fetching download links
    '''
    global fetch_links_worker

    fetch_day = date.today()

    try:

        # continue fetching links for the last 21 days
        while fetch_day >= date.today() + timedelta(days=-21):
            fetch_day = fetch_day + timedelta(days=-1)
            fetch_links_worker = thread_manager.Thread(
                name="fetch_links_worker", target=fetch_links, args=(fetch_day,))
            fetch_links_worker.start()
            if fetch_links_worker.isAlive() == False:
                sleep(3)
            fetch_links_worker.join()
    except RuntimeError as runtime_err:
        log(f'RuntimeError: {str(runtime_err)}', 'error')


def upload_file(file_path):
    '''
        upload given file to S3 and set flag in the database
    '''
    filename = basename(file_path)
    filename = filename.replace('zip', 'SAFE')

    if bool(search(r"[.][0-9][.]zip", file_path)) == True:
        # this happens when a file is downloaded twice S2A_MSIL1C_20200607T182921_N0209_R027_T23XML_20200607T221227.1.zip
        log(f'duplicate file downloaded {file_path}', 'error')
        remove_file(file_path)
        return

    try:
        thread_manager.lock.acquire()
        db_connect()
        query = granule.select().where(granule.filename == filename).limit(1).offset(0)
        granule_to_download = query.get()
        granule_to_download.downloaded = True
        granule_to_download.in_progress = False
        granule_to_download.download_failed = False
        granule_to_download.download_finished = datetime.now()
        granule_to_download.save()
        db_close()
        thread_manager.lock.release()

        granule_to_download_size = granule_to_download.size

        log(f'file downloaded {file_path}, {granule_to_download_size}', 'status')
        log(f'{filename},{granule_to_download_size}', 'downloads')

        # verify the checksum before uploading a file to S3
        granule_expected_checksum = granule_to_download.checksum
        granule_downloaded_checksum = get_checksum_local(file_path)

        if granule_downloaded_checksum.upper() == granule_expected_checksum.upper():
            s3_upload_worker = thread_manager.Thread(name=f'upload {filename}', target=s3_upload_file, args=(
                file_path, granule_to_download.beginposition,))
            s3_upload_worker.start()
        else:
            log(f'checksum did not match for {file_path}', 'error')
            thread_manager.upload_queue.put(
                {"file_path": file_path, "success": False})

        thread_manager.lock.acquire()
        db_connect()
        last_file_download_time = status.get(
            status.key_name == 'last_file_download_time')
        last_file_download_time.value = str(datetime.now())
        last_file_download_time.save()
        db_close()
        thread_manager.lock.release()

    except MemoryError as memory_err:
        log(f'Memory Error', 'error')
        remove_file(file_path)
    except UnicodeDecodeError as unicode_error:
        log(f'Unicode decode error during download of {file_path}', 'error')
        remove_file(file_path)
    except Exception as e:
        log(f'error during file_downloaded event: {str(e)}', 'error')
        remove_file(file_path)


def requeue_failed(DOWNLOAD_DAY=None, reset_all=False):
    '''
        requeue the failed downloads by resetting flags in the database
        reset_all resets all the files and should be used at the start of the downloader
    '''
    try:

        if not DOWNLOAD_DAY is None:
            start_date = str(DOWNLOAD_DAY) + " 00:00:00"  # MySQL format
            end_date = str(DOWNLOAD_DAY) + " 23:59:59"  # MySQL format

            thread_manager.lock.acquire()
            db_connect()

            query = granule.select().where(granule.download_failed == True).where(
                granule.beginposition.between(start_date, end_date))

            failed_count = query.count()

            if(failed_count > 0):

                # reset failed downloads
                granule.update(download_failed=False, downloaded=False, in_progress=False, uploaded=False).where(
                    granule.download_failed == True).where(granule.beginposition.between(start_date, end_date)).execute()  # .where(granule.retry < 5)

                # reset failed uploads
                granule.update(in_progress=False, downloaded=False, download_failed=False).where(
                    granule.uploaded == False).where(granule.beginposition.between(start_date, end_date)).execute()

                # reset all in progress flags
                granule.update(in_progress=False).where(
                    granule.beginposition.between(start_date, end_date)).execute()

                log(
                    f"resettting download failed flag for {DOWNLOAD_DAY}", "status")
                db_close()
                thread_manager.lock.release()
                return True
            else:
                db_close()
                thread_manager.lock.release()
                return False
        else:
            thread_manager.lock.acquire()
            db_connect()

            # reset failed downloads
            granule.update(in_progress=False, downloaded=False, download_failed=False,
                           uploaded=False).where(granule.download_failed == True).execute()

            if reset_all == True:

                # reset failed uploads
                granule.update(in_progress=False, downloaded=False, download_failed=False).where(
                    granule.uploaded == False).execute()

                # reset all in progress flags
                granule.update(in_progress=False).execute()

            log(f"resetting flags to download all remaining files", "status")
            db_close()
            thread_manager.lock.release()
            return True

    except OperationalError as ops_err:
        log(f'could not connect to the database: {str(ops_err)}', 'error')
        if thread_manager.lock.locked_lock() == True:
            thread_manager.lock.release()
        return False
    except Exception as e:
        log(f"failed resettting download failed flag", "error")
        return False

def expire_links(days=None):
    '''
        expire older links
    '''

    if days is None:
        days = -21  # default value

    last_day = date.today() + timedelta(days=days)

    thread_manager.lock.acquire()
    db_connect()

    try:
        # mark links as expired
        granule.update(expired=True).where(
            granule.beginposition <= last_day).execute()
    except OperationalError as ops_err:
        log(f'could not connect to the database: {str(ops_err)}', 'error')

    log(f"expiring links older than {days} days", "status")

    db_close()
    if thread_manager.lock.locked_lock() == True:
        thread_manager.lock.release()

def queue_files(file_limit=10000):

    try:
        # if there are more than 1000 waiting download, don't queue additional files
        if len(get_waiting_urls()) > 1000:
            return
    except Exception as e:
        log(f"failed getting waiting urls count", "error")
        return

    requeue_failed()

    '''
        put a file to download in aria2's queue by fetching a link from the database
    '''
    thread_manager.lock.acquire()
    db_connect()

    global DOWNLOAD_DAY  # should be in format Y-m-d

    try:
        query = (
            granule.select()
            .where(granule.ignore_file == False)
            .where(granule.downloaded == False)
            .where(granule.in_progress == False)
            .where(granule.uploaded == False)
            .where(granule.download_failed == False)
            .where(granule.expired == False)
            .where(granule.retry < 100) #give 100 tries to each file
            # .limit(file_limit)
        ).order_by(granule.beginposition.asc())  # download oldest available first
       

        pause_download()
        
        log(f"found {query.count()} from the database that can be downloaded", "status")
        log(f"attempting to add {file_limit} files in the download queue", "status")

        count = 0
        for grn in query:
            filename = grn.filename.replace("SAFE", "zip")
            # check if file is already uploaded to S3
            if not s3_file_exists(filename, grn.beginposition):
                grn.retry = grn.retry + 1
                grn.in_progress = True
                grn.download_started = datetime.now()
                grn.save()
                add_download_url(grn.download_url)
                count = count + 1
                if (count >= file_limit) == True:
                    break
            else:
                log(f"file was already uploaded = {filename}", "status")
                grn.uploaded = True
                grn.download_failed = False
                grn.save()

        log(f"{count} files added in the download queue", "status")
        resume_download()

    except OperationalError as ops_err:
        log(f'could not connect to the database: {str(ops_err)}', 'error')
        if thread_manager.lock.locked_lock() == True:
            thread_manager.lock.release()
        return
    except Exception as e:
        log(f"Error queueing files {str(e)}", "status")
        db_close()
        if thread_manager.lock.locked_lock() == True:
            thread_manager.lock.release()

        return

    db_close()
    if thread_manager.lock.locked_lock() == True:
        thread_manager.lock.release()

def is_active_url(url):
    '''
        check if already an active url in aria2's download queue
    '''
    active_urls = get_active_urls()
    for item in active_urls:
        for file in item['files']:
            for uri in file['uris']:
                if uri['uri'].lower() == url.lower():
                    return True

    return False

def upload_orphan_downloads():
    '''
        check downloads folder to upload files those were downloaded 2 hrs ago did not get not uploaded
        this shoudn't really happen but found that sometimes downloaded event from aria2 was missed and
        download folder was getting filled up pretty fast
    '''
    log('checking downloads folder for orphan files that were downloaded but not uploaded', 'status')

    all_zip_files = filter(lambda x: x.endswith('.zip'),
                           listdir(DOWNLOADS_PATH))

    now = datetime.now()
    for f in all_zip_files:
        file_path = f'{DOWNLOADS_PATH}/{f}'
        try:
            modify_date = datetime.fromtimestamp(path.getmtime(file_path))
            modify_date_2hr_ago = now + timedelta(hours=-2)
            if modify_date < modify_date_2hr_ago:
                log(f'uploading {file_path} with time {modify_date}', 'status')
                upload_file(file_path)
        except Exception as e:
            log(f'error during running orphan file checker {str(e)}', 'error')

def download_file():
    '''
        put a file to download in aria2's queue by fetching a link from the database
        Note: this function is currently NOT being used - it contains an older logic to download files
    '''
    thread_manager.lock.acquire()
    db_connect()

    global DOWNLOAD_DAY  # should be in format Y-m-d

    query = (
        granule.select()
        .where(granule.ignore_file == False)
        .where(granule.downloaded == False)
        .where(granule.in_progress == False)
        .where(granule.uploaded == False)
        .where(granule.download_failed == False)
        .where(granule.expired == False)
        .where(granule.retry < 160)
    )
    '''
            Note: if a failed granule is retried 160 times every 3 hours, we will keep retrying it for 21 days.
            However we need to be careful otherwise we may mark to ignore all files during the IntHub downtime
    '''

    if DOWNLOAD_BY_DAY and not DOWNLOAD_DAY is None:
        start_date = str(DOWNLOAD_DAY) + " 00:00:00"  # MySQL format
        end_date = str(DOWNLOAD_DAY) + " 23:59:59"  # MySQL format
        query = query.where(
            granule.beginposition.between(start_date, end_date))

    # download oldest available first
    query = query.order_by(granule.beginposition.asc())

    try:

        granule_to_download = query.get()
        granule_to_download_count = query.count()

        if DOWNLOAD_BY_DAY:
            if not DOWNLOAD_DAY == None:
                log(f'{granule_to_download_count} left to download for {DOWNLOAD_DAY}', "status")
            else:
                # when all the files for given day are downloaded, set download day to oldest available day
                granule_to_download_time = granule_to_download.beginposition.strftime(
                    "%Y-%m-%d")
                DOWNLOAD_DAY = granule_to_download_time
                log(
                    f"no other download day specified so setting download day to {DOWNLOAD_DAY}", "status")
                db_close()
                if thread_manager.lock.locked_lock() == True:
                    thread_manager.lock.release()
                return
        else:
            log(f'{granule_to_download_count} left to download', "status")

    except OperationalError as ops_err:
        log(f'could not connect to the database: {str(ops_err)}', 'error')
        if thread_manager.lock.locked_lock() == True:
            thread_manager.lock.release()
        return
    except Exception as e:
        log(f"No file to download found", "status")
        db_close()
        if thread_manager.lock.locked_lock() == True:
            thread_manager.lock.release()

        if requeue_failed(DOWNLOAD_DAY) == False:
            DOWNLOAD_DAY = None  # no files found for current day so resume downloading rest of the days

        return

    filename = granule_to_download.filename.replace("SAFE", "zip")
    file_path = f"{DOWNLOADS_PATH}/{filename}"

    if path.exists(file_path):
        remove_file(file_path)

    if is_active_url(granule_to_download.download_url):
        # file is already being downloaded
        log(f"file {granule_to_download.download_url} is already in download queue", "status")
        db_close()  # close if open
        if thread_manager.lock.locked_lock() == True:
            thread_manager.lock.release()
        return

    # check if file is already uploaded to S3
    if not s3_file_exists(filename, granule_to_download.beginposition):
        granule_to_download.retry = granule_to_download.retry + 1
        granule_to_download.in_progress = True
        granule_to_download.download_started = datetime.now()
        granule_to_download.save()

        download = add_download_url(granule_to_download.download_url)

        log(f"file added into the download queue = {filename}(retry = {granule_to_download.retry})  for day {str(granule_to_download.beginposition)}", "status",)

    else:
        log(f"file already uploaded = {filename}", "status")
        granule_to_download.uploaded = True
        granule_to_download.download_failed = False
        granule_to_download.save()

    db_close()
    if thread_manager.lock.locked_lock() == True:
        thread_manager.lock.release()

def do_downloads():
    '''
        if there are less than MAX_CONCURRENT_INTHUB_LIMIT downloads in progress, add one more to aria2 queue
        Note: this function is currently NOT being used - it contains an older logic to download files
    '''
    global download_file_worker

    # if link fetcher is running reduce maximum concurrent downloads by 1, max limit is 15
    if USE_SCIHUB_TO_FETCH_LINKS or (fetch_links_worker is None or fetch_links_worker.isAlive() == False):
        maximum_downloads = MAX_CONCURRENT_INTHUB_LIMIT
    else:
        maximum_downloads = MAX_CONCURRENT_INTHUB_LIMIT - 1

    if len(get_active_urls()) < maximum_downloads:
        try:
            if download_file_worker == None or download_file_worker.isAlive() == False:
                download_file_worker = thread_manager.Thread(
                    name="download_file_worker", target=download_file, args=())
                download_file_worker.start()
        except Exception as e:
            log(f"error during initiaing downloads:{str(e)}", "status")

def check_queues():
    '''
        check both downloaded or uploaded files queue, perform upload and clean up
    '''
    try:
        log(f"#threads = {thread_manager.active_count()}, #downloads in progress = {len(get_active_urls())}, #downloads waiting = {len(get_waiting_urls())}, Downloads Size = {get_download_folder_size()} GB", "status")
        log(f"{get_memory_usage()}", "status")
    except Exception as e:
        log(f"could not get status from aria2c", "error")

    # check download queue
    if not thread_manager.download_queue.empty():
        item = thread_manager.download_queue.get()

        # if item is successfully downloaded, attempt upload otherwise, mark as failed in the database
        if item['success'] == True:
            file_path = item['file_path']
            upload_file(file_path)
        elif item['success'] == False:
            failed_url = item['url']
            thread_manager.lock.acquire()
            db_connect()
            granule_failed = granule.select().where(
                granule.download_url == failed_url).get()
            granule_failed.downloaded = False
            granule_failed.in_progress = False
            granule_failed.download_failed = True
            granule_failed.save()
            db_close()
            thread_manager.lock.release()
            thread_manager.error_count += 1
            log(
                f"file aborted = {granule_failed.filename} ({failed_url}) msg={item['error_message']}  retry={granule_failed.retry} attempts", 'error')

    # check the upload queue
    if not thread_manager.upload_queue.empty():
        item = thread_manager.upload_queue.get()
        file_path = item['file_path']
        filename = basename(file_path)
        filename = filename.replace('zip', 'SAFE')

        # if file is successfully uploaded to S3, mark uploaded=True in the database and remove the file
        if item['success'] == True:

            log(f'file uploaded = {filename}', 'status')

            thread_manager.lock.acquire()
            db_connect()
            try:
                query = granule.select().where(granule.filename == filename).limit(1).offset(0)
                granule_to_download = query.get()
                granule_to_download.uploaded = True
                granule_to_download.downloaded = True
                granule_to_download.download_failed = False
                granule_to_download.in_progress = False
                granule_to_download.save()
            except Exception as e:
                log(f'error: cannot set uploaded = True:{str(e)}', 'error')
            db_close()
            thread_manager.lock.release()

        else:
            thread_manager.lock.acquire()
            db_connect()
            query = granule.select().where(granule.filename == filename).limit(1).offset(0)
            granule_to_download = query.get()
            granule_to_download.downloaded = False
            granule_to_download.in_progress = False
            granule_to_download.download_failed = True
            granule_to_download.uploaded = False
            granule_to_download.download_finished = datetime.now()
            granule_to_download.save()
            db_close()
            thread_manager.lock.release()

        remove_file(file_path)

def run_threaded(job_func):
    job_thread = thread_manager.Thread(target=job_func)
    job_thread.start()

def init():
    '''
        Initilize the link fetching and start the scheduler
    '''

    # remove orphan files in downloads folder
    clean_up_downloads()

    # expire older links
    expire_links(days=-4)

    # start the link fetcher
    check_link_fetcher()

    # kill existing aria2 instance
    kill_downloader()

    # requeue all the failed download by resetting flags in the database, either for a given day or for all days
    if DOWNLOAD_BY_DAY and not DOWNLOAD_DAY is None:
        requeue_failed(DOWNLOAD_DAY)
    else:
        requeue_failed(None, True)

    # start initial downloads, later this is being done by a scheduler
    queue_files()  

    # create scheduled events
    every(1).seconds.do(run_threaded, check_queues)
    every(15).seconds.do(run_threaded, collect_metrics)
    every(15).minutes.do(run_threaded, s3_upload_logs)
    every(4).hours.do(run_threaded, check_link_fetcher)
    every(24).hours.do(expire_links, days=-20)
    every(1).minutes.do(run_threaded, check_downloads_folder_size)
    every(5).hours.do(queue_files)  

    # start the scheduler
    while True:
        run_pending()
        sleep(1)

# check if any previous instance is already running
if file_is_locked():
    log(f'Can not start the downloader: another instance is running', 'error')
    exit(0)
else:
    log(f'Starting the downloader: no other instance is running found', 'status')
    init()