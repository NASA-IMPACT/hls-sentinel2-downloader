from threading import Lock, Thread, active_count
from queue import Queue


lock = Lock()
download_queue = Queue()
upload_queue = Queue()
error_count = 0
