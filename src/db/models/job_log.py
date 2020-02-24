import enum
from sqlalchemy import (
    Table, Column,
    String, Integer, Text, ForeignKey, Enum,
)
from .metadata import metadata


class LogLevel(str, enum.Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


job_log = Table(
    'job_log', metadata,
    Column('id', Integer, primary_key=True),
    Column('job_id', Integer, ForeignKey('job.id')),
    Column('log_level', Enum(LogLevel), nullable=False,
           default=(LogLevel.INFO)),
    Column('summary', String(512)),
    Column('details', Text),
)
