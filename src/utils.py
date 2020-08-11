# import existing packages
from datetime import datetime
from hashlib import md5
from glob import glob
from os import remove, path, getcwd, getpid, listdir
from psutil import process_iter, virtual_memory, Process, NoSuchProcess
from dateparser import parse as dateparser_parse
from re import match, sub
from fcntl import lockf, LOCK_EX, LOCK_NB
from colorama import Fore
from pathlib import Path

# import custom functions
from models import granule, db
from thread_manager import lock
from log_manager import log
from settings import DOWNLOADS_PATH, DEBUG, DOWNLOAD_DAY, LOCK_FILE, INCLUDE_TILES_FILE


file_handle = None


def file_is_locked():
    '''
        check if file is already locked by current running process
        Ref - #https://stackoverflow.com/questions/14406562/prevent-running-concurrent-instances-of-a-python-script
    '''
    global file_handle
    file_handle = open(LOCK_FILE, 'w')
    try:
        lockf(file_handle, LOCK_EX | LOCK_NB)
        return False
    except IOError:
        return True


def get_download_folder_size():
    '''
        get download folder size
    '''
    return int(get_folder_size(DOWNLOADS_PATH) / (1024*1024*1024))


def parse_size(size):
    '''
        parse size from string
        ref - https://stackoverflow.com/questions/42865724/python-parse-human-readable-filesizes-into-bytes, https://stackoverflow.com/a/42865957/2002471
    '''

    units = {"B": 1, "KB": 2**10, "MB": 2**20, "GB": 2**30, "TB": 2**40}
    size = size.upper()
    if not match(r' ', size):
        size = sub(r'([KMGT]?B)', r' \1', size)
    number, unit = [string.strip() for string in size.split()]
    return int(float(number)*units[unit])


def convert_date(date_str):
    '''
        convert string to date object
    '''
    return dateparser_parse(date_str)


def get_checksum_local(file_path):
    '''
        get checksum of a file using md5
        there is a way to do this in chuncks as mentioned below but that turned out to be extreamly slow
        https://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python
        https://stackoverflow.com/questions/32442693/memory-error-python-when-processing-files/32443595
    '''
    try:
        hash = md5(open(file_path, 'rb').read()).hexdigest()
    except Exception as e:
        hash = ''
        log(f"error during md5 {str(e)}", "error")

    return hash


def get_include_tiles_list():
    '''
        get list of tiles to include during downloads
    '''
    tiles = []
    with open(f'{INCLUDE_TILES_FILE}') as f:
        for line in f:
            tiles.append(line.strip())
    return tiles


def update_ignore_links_in_datebase():
    '''
        this is a one time use function to set ignore flag on tiles
    '''
    lock.acquire()
    db.connect()
    query = granule.update(ignore_file=True).where(
        granule.tileid.not_in(get_include_tiles_list()))
    print(query.sql())
    query.execute()
    db.close()
    lock.release()


def remove_file(file_path):
    '''
        remove a file
    '''
    try:
        log(f'removing file {file_path}', 'status')
        remove(file_path)
    except Exception as e:
        log(f'cannot remove {file_path} {str(e)}', 'error')


def clean_up_downloads():
    '''
        remove all files in the downloads folder
    '''
    log(f'cleaning up the downloads folder', 'status')
    files = glob(f'{DOWNLOADS_PATH}/*.*')
    for f in files:
        remove_file(f)


def get_memory_usage():
    '''
        Prints current memory usage stats.
        Ref: https://stackoverflow.com/a/15495136
    '''
    PROCESS = Process(getpid())
    MEGA = 10 ** 6
    MEGA_STR = ' ' * MEGA

    total = virtual_memory().total
    available = virtual_memory().available
    percent = virtual_memory().percent
    used = virtual_memory().used
    free = virtual_memory().free

    total, available, used, free = total / \
        MEGA, available / MEGA, used / MEGA, free / MEGA
    proc = PROCESS.memory_info()[1] / MEGA

    return f'Memory Stat: process = {proc}, total = {total}, available = {available}, used = {used}, free = {free}, percent = {percent}'


def get_folder_size(p):
    '''
        get folder size
    '''
    root_directory = Path(p)
    try:
        size = sum(f.stat().st_size for f in root_directory.glob(
            '**/*') if f.is_file())
    except Exception as e:
        size = -1
        log(f'error during getting folder size {str(e)}', 'error')

    return size

def get_zip_count():
    '''
        get number of active downloads in the downloads folder
    '''
    zip_count = 0
    for item in listdir(DOWNLOADS_PATH):
        if item.endswith(".zip"):
            zip_count = zip_count + 1
    
    return zip_count

def get_wget_count():
    '''
        get number of active wget processes count
    '''
    wget_count = 0
    for proc in process_iter():
        try:
            if proc.name().lower() == 'wget':
                wget_count = wget_count + 1
        except NoSuchProcess:
            pass
    
    return wget_count

def kill_wget():
    '''
        kill existing running wget processes if any
    '''
    for proc in process_iter():
        if proc.name().lower() == 'wget':
            proc.kill()
            log(f"existing wget process killed", "status")