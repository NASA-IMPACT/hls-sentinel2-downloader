from threading import Lock, Thread, active_count
from queue import Queue

Thread = Thread
active_count = active_count
open_connections = 0
lock = Lock()
download_queue = Queue()
upload_queue = Queue()
error_count = 0
