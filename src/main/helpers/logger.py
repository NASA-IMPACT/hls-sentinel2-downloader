import traceback
from sys import exc_info
from datetime import datetime
from serializer import Serializer
from models.job_log import job_log, LogLevel


class Logger:
    def __init__(self, db_connection, job_id=None):
        self.log_serializer = Serializer(db_connection, job_log)
        self.job_id = job_id

    def set_job_id(self, job_id):
        self.job_id = job_id

    def log(self, summary, details='', level=LogLevel.INFO):
        self.log_serializer.post({
            'job_id': self.job_id,
            'logged_at': datetime.now(),
            'log_level': level,
            'summary': summary,
            'details': details,
        })

    def warn(self, summary, details=''):
        self.log(summary, details, LogLevel.WARNING)

    def info(self, summary, details=''):
        self.log(summary, details, LogLevel.INFO)

    def error(self, summary, details=''):
        self.log(summary, details, LogLevel.ERROR)

    def exception(self):
        try:
            etype, eval, tb = exc_info()
            summary = str(eval)[:512]
            details = traceback.format_exception(etype, eval, tb)
            self.error(summary, details)
        except Exception:
            self.error('Exception occurred while catching exception.')
