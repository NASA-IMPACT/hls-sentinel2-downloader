from serializer import Serializer
from models.job_log import job_log, LogLevel


class Logger:
    def __init__(self, db_connection, job_id=None):
        self.log = Serializer(db_connection, job_log)
        self.job_id = job_id

    def log(self, summary, details='', level=LogLevel.INFO):
        self.log.post({
            'job_id': self.job_id,
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
