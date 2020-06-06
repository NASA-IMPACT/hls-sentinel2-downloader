#import external packages
from time import sleep
from multiprocessing import Process
from os import remove, path, listdir
from models import status,  granule, db
from log_manager import log
from settings import DEBUG
from datetime import datetime, date, timedelta
from ntpath import basename
from sys import exit
from colorama import init as colorama_init, Fore, Back, Style
from termcolor import colored
from schedule import every, run_pending

#import custom functions
from download_manager import add_download_url, get_active_urls
from s3_uploader import s3_upload_file, s3_file_exists
from utils import get_checksum_local, kill_downloader, clean_up_downloads, get_memory_usage, file_is_locked, get_folder_size
from log_manager import log, s3_upload_logs
from links_manager import fetch_links
from metrics_collector import collect_metrics
from settings import DOWNLOADS_PATH, DEBUG, DOWNLOAD_DAY, LOCK_FILE, FETCH_LINKS
from thread_manager import lock, download_queue, upload_queue, Thread, active_count


colorama_init(autoreset=True) #required to print colors in both UNIX and Windows OS
fetch_links_worker = None


def health_check():
    '''
        check health of various running threads
    '''
    if DEBUG:
        print(f"{str(datetime.now())}, Total threads = {active_count()}, aria2 downloads in progress = {len(get_active_urls())}")
        print(f"{str(datetime.now())}, {get_memory_usage()}")
    log(f"Total threads = {active_count()}, aria2 downloads in progress = {len(get_active_urls())}",status)


    if get_folder_size(DOWNLOADS_PATH) / (1024*1024*1024) > 500:
        #download folder's size has reached above 500GB that means something must be terribly went wrong
        #TODO: raise the alert
        clean_up_downloads()

    if len(get_active_urls()) == 0:  # if no active downloads cleanup the download dir
        clean_up_downloads()

    if FETCH_LINKS == True and (fetch_links_worker is None or fetch_links_worker.isAlive() == False):
        Thread(name="start_links_fetch", target=start_links_fetch, args=()).start()

def start_links_fetch():
    '''
        start fetching download links
    '''
    global fetch_links_worker

    fetch_day = date.today()

    try:

        #continue fetching links for the last 14 days
        while fetch_day >= date.today() + timedelta(days=-14):  
            fetch_day = fetch_day + timedelta(days=-1)
            fetch_links_worker = Thread(name="fetch_links_worker", target=fetch_links, args=(fetch_day,))
            fetch_links_worker.start()
            if fetch_links_worker.isAlive() == False:
                sleep(3)
            fetch_links_worker.join()
    except RuntimeError as runtime_err:
        if(DEBUG):
            print(f'{str(datetime.now())}, RuntimeError: {str(runtime_err)}')
        log(f'RuntimeError: {str(runtime_err)}','error')
         
def upload_file(file_path):
    '''
        upload given file to S3 and set flag in the database
    '''
    if(DEBUG):
        print(f'{str(datetime.now())}, file downloaded {file_path}')

    filename = basename(file_path)

    log(f'file downloaded = {filename}','status')

    filename = filename.replace('zip','SAFE')

    try:
        lock.acquire()
        db.connect()
        query = granule.select().where(granule.filename==filename).limit(1).offset(0)
        granule_to_download= query.get()
        granule_to_download.downloaded = True
        granule_to_download.in_progress = False
        granule_to_download.download_failed = False
        granule_to_download.download_finished = datetime.now()
        granule_to_download.save()
        db.close()
        lock.release()

        granule_to_download_size = granule_to_download.size

        log(f'{filename},{granule_to_download_size}','downloads')

        #verify the checksum before uploading a file to S3
        granule_expected_checksum = granule_to_download.checksum  
        granule_downloaded_checksum = get_checksum_local(file_path)
    
        if granule_downloaded_checksum.upper() == granule_expected_checksum.upper():
            s3_upload_worker = Thread(name=f'upload {filename}',target=s3_upload_file,args=(file_path,granule_to_download.beginposition,))
            s3_upload_worker.start()
        else:
            if(DEBUG):
                print(f'{str(datetime.now())}, Checksum did not match for {file_path}')
            log(f'Checksum did not match for {file_path}','error')
            upload_queue.put({"file_path":file_path,"success":False})

        lock.acquire()
        db.connect()
        last_file_download_time = status.get(status.key_name == 'last_file_download_time')
        last_file_download_time.value = str(datetime.now())
        last_file_download_time.save()
        db.close()
        lock.release()

    except MemoryError as memory_err:
        if(DEBUG):
            print(f'{str(datetime.now())}, Memory Error')
        remove(file_path)
        log(f'Memory Error','error')
    except UnicodeDecodeError as unicode_error:
        if(DEBUG):
            print(f'{str(datetime.now())}, Unicode decode error during download of {file_path}')
        remove(file_path)
        log(f'Unicode decode error during download of {file_path}','error')
    except Exception as e:
        if(DEBUG):
            print(f'{str(datetime.now())}, error during file_downloaded event: {str(e)},{file_path}')
        remove(file_path)
        log(f'error during file_downloaded event: {str(e)}','error')

def requeue_retry_failed(DOWNLOAD_DAY=None):
    '''
        requeue the failed downloads by resetting flags in the database
    '''
    try:
       
        if not DOWNLOAD_DAY is None:
            start_date = str(DOWNLOAD_DAY) + " 00:00:00"  #MySQL format
            end_date = str(DOWNLOAD_DAY) + " 23:59:59"    #MySQL format

            lock.acquire()
            db.connect()

            query = granule.select().where(granule.download_failed == True).where(granule.beginposition.between(start_date, end_date))
            
            failed_count = query.count()

            if(failed_count > 0):
                granule.update(download_failed=False,downloaded=False,in_progress=False,uploaded=False).where(granule.download_failed == True).where(granule.beginposition.between(start_date, end_date)).execute() #.where(granule.retry < 5)
                if DEBUG:
                    print(f"{str(datetime.now())}, resettting download failed flag for {DOWNLOAD_DAY}")
                log(f"resettting download failed flag for {DOWNLOAD_DAY}", "status")
                db.close()
                lock.release()
                return True
            else:
                db.close()
                lock.release()
                return False
        else:
            lock.acquire()
            db.connect()
            granule.update(in_progress=False,downloaded=False,download_failed=False,uploaded=False).where(granule.download_failed == True).execute()
            if DEBUG:
                print(f"{str(datetime.now())}, resetting flags to download all remaining files")
            log(f"resetting flags to download all remaining files", "status")
            db.close()
            lock.release()
            return True
    
    except Exception as e:
        if DEBUG:
            print(f"{str(datetime.now())}, failed resettting download failed flag")
        log(f"failed resettting download failed flag", "error")
        return False

def download_file():
    '''
        put a file to download in aria2's queue by fetching a link from the database
    '''
    global DOWNLOAD_DAY # should be in format Y-m-d

    query = (
        granule.select()
        .where(granule.ignore_file == False)
        .where(granule.downloaded == False)
        .where(granule.in_progress == False)
        .where(granule.uploaded == False)
        .where(granule.download_failed == False)
    )

    if not DOWNLOAD_DAY is None:
        start_date = str(DOWNLOAD_DAY) + " 00:00:00"  #MySQL format
        end_date = str(DOWNLOAD_DAY) + " 23:59:59"    #MySQL format
        query = query.where(granule.beginposition.between(start_date, end_date))

    query = query.order_by(granule.beginposition.desc())

    lock.acquire()
    db.connect()

    try:

        granule_to_download = query.get()
        granule_to_download_count = query.count()

        if not DOWNLOAD_DAY == None:
            if DEBUG:
                print(f'{str(datetime.now())}, {granule_to_download_count} left to download for {DOWNLOAD_DAY}')
            log(f'{granule_to_download_count} left to download for {DOWNLOAD_DAY}', "status")
        else:
            DOWNLOAD_DAY = granule_to_download.beginposition.strftime("%Y-%m-%d")
            if DEBUG:
                print(f"{str(datetime.now())}, no download day specified so setting download day to {DOWNLOAD_DAY}")
            log(f"no download day specified so setting download day to {DOWNLOAD_DAY}", "status")
            db.close()
            lock.release()
            return

    except Exception as e:

        if DEBUG:
            print(f"{str(datetime.now())}, No file to download found (DOWNLOAD_DAY={DOWNLOAD_DAY})")
        log(f"No file to download found (DOWNLOAD_DAY={DOWNLOAD_DAY})", "status")

        db.close()
        lock.release()

        if requeue_retry_failed(DOWNLOAD_DAY) == False:
            DOWNLOAD_DAY = None  # no files found for current day so resume downloading rest of the days

        return

    db.close()
    lock.release()

    filename = granule_to_download.filename.replace("SAFE", "zip")
    file_path = f"{DOWNLOADS_PATH}/{filename}"

    #check if file is already downloaded with valid checksum in the downloads folder
    if path.exists(file_path):
        granule_expected_checksum = granule_to_download.checksum
        granule_downloaded_checksum = get_checksum_local(file_path)
        if granule_downloaded_checksum.upper() == granule_expected_checksum.upper():
            log(f"{str(datetime.now())}, file already downloaded = {filename}", "status")
            download_queue.put({"file_path":file_path,"success":True})
            return

    #check if file is already uploaded to S3
    if not s3_file_exists(filename, granule_to_download.beginposition):
        lock.acquire()
        db.connect()
        granule_to_download.retry = granule_to_download.retry + 1
        granule_to_download.in_progress = True
        granule_to_download.download_started = datetime.now()
        granule_to_download.save()
        db.close()
        lock.release()

        download = add_download_url(granule_to_download.download_url)

        if DEBUG:
            print(f"{str(datetime.now())}, downloading file {filename} (retry = {granule_to_download.retry}) for day {str(granule_to_download.beginposition)}")
        log(f"file download started = {filename}(retry = {granule_to_download.retry})  for day {str(granule_to_download.beginposition)}","status",)
   
    else:
        if DEBUG:
            print(f"{str(datetime.now())}, file already uploaded = {filename}")
        log(f"file already uploaded = {filename}", "status")

        lock.acquire()
        db.connect()
        granule_to_download.uploaded = True
        granule_to_download.download_failed = False
        granule_to_download.save()
        db.close()
        lock.release()

def check_orphan_uploads():
    '''
        check downloads folder to upload files those were downloaded 1 hr ago did not get not uploaded
        this shoudn't really happen but found that sometimes downloaded event from aria2 was missed and 
        download folder was getting filled up pretty fast
    '''
    if(DEBUG):
        print(f'{str(datetime.now())}, checking downloads folder for orphan files that were downloaded but not uploaded')
    log('checking downloads folder for orphan files that were downloaded but not uploaded','status')
  
    all_zip_files = filter(lambda x: x.endswith('.zip'), listdir(DOWNLOADS_PATH))
   
    now = datetime.now()
    for f in all_zip_files:
        file_path = f'{DOWNLOADS_PATH}/{f}'
        modify_date = datetime.fromtimestamp(path.getmtime(file_path))
        modify_date_1hr_ago= now + timedelta(hours=-1)
        if modify_date < modify_date_1hr_ago:
            upload_file(file_path)

def do_downloads():
    '''
        if there are less than 14 downloads in progress, add one more to aria2 queue
    '''
    if len(get_active_urls()) < 15:
        try:
            download_file()
        except Exception as e:
            if DEBUG:
                print(f"{str(datetime.now())}, error during initiaing_downloads:{str(e)}", "status")
            log(f"error during initiaing downloads:{str(e)}", "status")

def check_queues():
    '''
        check both downloaded or uploaded files queue, perform upload and clean up
    '''
    #check download queue
    if not download_queue.empty():
        item = download_queue.get()

        # if item is successfully downloaded, attempt upload otherwise, mark as failed in the database
        if item['success'] == True:
            upload_file(item['file_path'])
        elif item['success'] == False:
            failed_url = item['url']
            lock.acquire()
            db.connect()
            granule_failed= granule.select().where(granule.download_url==failed_url).get()
            granule_failed.downloaded = False
            granule_failed.in_progress = False
            granule_failed.download_failed = True
            granule_failed.save()
            db.close()
            lock.release()

            if(DEBUG):
                print(Fore.RED + f'{str(datetime.now())}, file aborted = {granule_failed.filename} ({failed_url}) retry={granule_failed.retry} attempts')
            log(f'file aborted = {granule_failed.filename} ({failed_url})  retry={granule_failed.retry} attempts','error')

    #check the upload queue        
    if not upload_queue.empty():
        item = upload_queue.get()
        file_path = item['file_path']

        #if file is successfully uploaded to S3, mark uploaded=True in the database and remove the file
        if item['success'] == True:
            
            if(DEBUG):
                print(Fore.GREEN + f'{str(datetime.now())}, file uploaded {file_path}')

            filename = basename(file_path)
            filename = filename.replace('zip','SAFE')

            log(f'file uploaded = {filename}','status')

            remove(file_path)

            lock.acquire()
            db.connect()
            try:
                query = granule.select().where(granule.filename==filename).limit(1).offset(0)
                granule_to_download= query.get()
                granule_to_download.uploaded = True
                granule_to_download.downloaded = True
                granule_to_download.download_failed = False
                granule_to_download.in_progress = False
                granule_to_download.save()
            except Exception as e:
                if(DEBUG):
                    print(f'{str(datetime.now())}, Error: cannot set uploaded = True:{str(e)}')
                log(f'Error: cannot set uploaded = True:{str(e)}','error')    
            db.close()
            lock.release()
        else:
            remove(file_path)
            lock.acquire()
            db.connect()
            granule_to_download.downloaded = False
            granule_to_download.in_progress = False
            granule_to_download.download_failed = True
            granule_to_download.uploaded = False
            granule_to_download.download_finished = datetime.now()
            granule_to_download.save()
            db.close()
            lock.release()

def init():
    '''
        Initilize the link fetching and start the scheduler
    '''
     
    

    #start the link fetcher
    if FETCH_LINKS == True:
        Thread(name="start_links_fetch", target=start_links_fetch, args=()).start()

    #requeue all the failed download by resetting flags in the database, either for a given day or for all days
    if not DOWNLOAD_DAY is None:
        requeue_retry_failed(DOWNLOAD_DAY)
    else:
        requeue_retry_failed()

    
    
  
    kill_downloader()
    clean_up_downloads()

    #create scheduled events    
    every(3).seconds.do(check_queues)
    every(1).seconds.do(do_downloads)
    every(2).seconds.do(health_check)
    every(1).minutes.do(collect_metrics)
    every(5).minutes.do(s3_upload_logs)
    every(1).hour.do(check_orphan_uploads)
    
    
    #start the scheduler
    while True:
        run_pending()
        sleep(1)

#check if any previous instance is already running
if file_is_locked():
    if DEBUG:
        print (Fore.RED + f'{str(datetime.now())}, Can not start the downloader: another instance is running')
        log(f'Can not start the downloader: another instance is running','error')
    exit(0)
else:
    if DEBUG:
        print(f'{str(datetime.now())}, Starting the downloader: no other instance is running found')
    log(f'Starting the downloader: no other instance is running found','status')
    init()



