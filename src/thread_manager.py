from threading import Lock, Thread, active_count
from queue import Queue

open_connections = 0
lock = Lock()
download_queue = Queue()
upload_queue = Queue()
