# import external packages
from datetime import datetime
from json import dumps as json_dump
from glob import glob1
from psutil import virtual_memory, cpu_percent, cpu_count

# import internal functions
from models import granule, granule_count, status, db
from utils import get_folder_size
from settings import LOGS_PATH, DOWNLOADS_PATH
from download_manager import get_active_urls
from log_manager import log
from thread_manager import lock, active_count, upload_queue, download_queue


def collect_metrics():
    '''
        collect metrics in JSON format and store in logs folder
    '''
    lock.acquire()
    db.connect()

    metrics = {}
    metrics['datetime'] = str(datetime.now())
    metrics['total_days'] = granule_count.select().count()
    metrics['total_granules'] = granule.select().count()
    metrics['total_granules_ignore'] = granule.select().where(
        granule.ignore_file == True).count()
    metrics['total_granules_in_progress'] = granule.select().where(
        granule.in_progress == True).count()
    metrics['total_granules_not_uploaded'] = granule.select().where(
        granule.uploaded == False).where(granule.ignore_file == False).count()
    metrics['total_granules_uploaded'] = granule.select().where(
        granule.uploaded == True).count()
    metrics['total_granules_not_downloaded'] = granule.select().where(
        granule.downloaded == False).where(granule.ignore_file == False).count()
    metrics['total_granules_downloaded'] = granule.select().where(
        granule.downloaded == True).count()
    metrics['total_downloads_in_progress'] = len(get_active_urls())
    metrics['total_upload_queue_items'] = upload_queue.qsize()
    metrics['total_download_queue_items'] = download_queue.qsize()
    metrics['total_active_threads'] = active_count()
    metrics['log_folder_size'] = get_folder_size(LOGS_PATH)
    metrics['download_folder_size'] = get_folder_size(DOWNLOADS_PATH)
    metrics['count_download_folder_files'] = len(
        glob1(DOWNLOADS_PATH, "*.zip"))
    metrics['count_download_folder_aria2_files'] = len(
        glob1(DOWNLOADS_PATH, "*.aria2"))
    metrics['total_memory'] = virtual_memory().total
    metrics['available_memory'] = virtual_memory().available
    metrics['used_memory'] = virtual_memory().used
    metrics['free_memory'] = virtual_memory().free
    metrics['percent_memory'] = virtual_memory().percent
    metrics['cpu_percent'] = cpu_percent()

    if cpu_count() == 8:
        cpu1, cpu2, cpu3, cpu4, cpu5, cpu6, cpu7, cpu8 = cpu_percent(
            interval=0, percpu=True)
        metrics['cpu1_percent'] = cpu1
        metrics['cpu2_percent'] = cpu2
        metrics['cpu3_percent'] = cpu3
        metrics['cpu4_percent'] = cpu4
        metrics['cpu5_percent'] = cpu5
        metrics['cpu6_percent'] = cpu6
        metrics['cpu7_percent'] = cpu7
        metrics['cpu8_percent'] = cpu8
    elif cpu_count() == 4:
        cpu1, cpu2, cpu3, cpu4 = cpu_percent(interval=0, percpu=True)
        metrics['cpu1_percent'] = cpu1
        metrics['cpu2_percent'] = cpu2
        metrics['cpu3_percent'] = cpu3
        metrics['cpu4_percent'] = cpu4

    db.close()
    lock.release()
    log(json_dump(metrics), 'metrics')
