import enum
from sqlalchemy import (
    Table, Column,
    String, Integer, DateTime, Enum
)
from .metadata import metadata


class JobStatus(str, enum.Enum):
    STARTED = 'started'
    SUCCESS = 'success'
    FAILED = 'failed'


job = Table(
    'job', metadata,
    Column('id', Integer, primary_key=True),
    Column('job_name', String(128), nullable=False),
    Column('start_time', DateTime, nullable=False),
    Column('end_time', DateTime),

    Column('status', Enum(JobStatus), nullable=False,
           server_default=(JobStatus.STARTED)),
    Column('error_summary', String(1024)),
)
