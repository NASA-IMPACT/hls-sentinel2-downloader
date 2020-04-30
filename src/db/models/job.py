import enum
from sqlalchemy import (
    Table, Column,
    String, Integer, DateTime, Date, Enum, Boolean,
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

    Column('date_handled', Date),

    # The following two fields are no longer used. They may be removed.
    Column('needs_review', Boolean, default=True, nullable=False),
    Column('review_number', Integer, default=0, nullable=False),

    Column('status', Enum(JobStatus), nullable=False,
           default=(JobStatus.STARTED)),
    Column('error_summary', String(1024)),
)
