#import external packages
from time import sleep
from os import popen as os_popen
from subprocess import Popen as subprocess_Popen, PIPE as subprocess_PIPE
import aria2p

#import internal functions
from settings import COPERNICUS_USERNAME, COPERNICUS_PASSWORD, DOWNLOADS_PATH
from thread_manager import  download_queue


aria2 = None
aria2_client = None
gids = {}

def handle_download_start(aria2, gid):
    '''
        aria2 download start event handler
    '''
    download = aria2.get_download(gid)
    pass

def handle_download_error(aria2, gid):
    '''
        aria2 download failed event handler
    '''
    global gids
    download = aria2.get_download(gid)

    url_failed = gids[download.gid]  #alternate way - download.files[0].uris[0]['uri']

    if download.gid in gids.keys():
        del gids[download.gid]

    download_queue.put({"url":url_failed,"success":False})

def handle_download_complete(aria2, gid):
    '''
        aria2 download complete event handler
    '''

    global gids
    download = aria2.get_download(gid)
    if download.gid in gids.keys():
        del gids[download.gid] 
    file_path = str(download.root_files_paths[0])

    download_queue.put({"file_path":file_path,"success":True})
   

def aria2_add_listeners():
    '''
        aria2 add events handler
    '''

    global aria2
    aria2.listen_to_notifications(
        threaded=True,
        on_download_start=handle_download_start,
        on_download_error=handle_download_error,
        on_download_complete=handle_download_complete,
    )

def is_aria2_running():
    '''
        check if aria2 is already running
    '''

    processname = "aria2"
    tmp = os_popen("ps -Af").read()
    proccount = tmp.count(processname)

    if proccount > 0:
        return True
    else:
        return False

def start_aria2():
    '''
        start aria2
        ref - https://www.cyberciti.biz/faq/python-execute-unix-linux-command-examples/
    '''

    p = subprocess_Popen(
        [
            "aria2c",
            "--max-concurrent-downloads=15",  
            "--max-connection-per-server=1",
            "--split=1",
            f"--http-user={COPERNICUS_USERNAME}",
            f"--http-passwd={COPERNICUS_PASSWORD}",
            "--enable-rpc",
            "--rpc-listen-all",
            f"--dir={DOWNLOADS_PATH}",
            "--allow-overwrite=true",
            "-D",
        ],
        stdout=subprocess_PIPE,
    )
    output, err = p.communicate()

def init_aria2():
    '''
        initialize aria2
    '''

    global aria2, aria2_client

    if not is_aria2_running():
        start_aria2()
        sleep(2)

    aria2_client = aria2p.Client(host="http://localhost", port=6800, secret="",)
    aria2 = aria2p.API(aria2_client)
    aria2_add_listeners()

def add_download_url(url):
    '''
        add a url in aria2's download list
    '''
    global aria2
    global gids

    if aria2 is None:
        init_aria2()

    download = aria2.add_uris([url])
    gids[download.gid] = url
    return download

def get_active_urls():
    '''
        get active downloads from aria2
    '''
    global aria2

    if aria2 is None or aria2_client is None:
        init_aria2()

    return aria2_client.tell_active()