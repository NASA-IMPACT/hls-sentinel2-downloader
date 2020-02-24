import signal


class Timeout:
    def __init__(self, seconds):
        self.seconds = seconds

    def __enter__(self):
        signal.signal(signal.SIGALRM, self._handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, tpye, value, traceback):
        signal.alarm(0)

    def _handle_timeout(self, signum, frame):
        raise TimeoutError('Job Timeout')
