import enum
from sqlalchemy import (
    Table, Column,
    String, Integer, ForeignKey, Enum, Boolean
)
from .metadata import metadata


class DownloadStatus(str, enum.Enum):
    NOT_STARTED = 'not_started'
    DOWNLOADING = 'downloading'
    SUCCESS = 'success'
    ERROR = 'error'
    INVALID = 'invalid'


granule = Table(
    'granule', metadata,
    Column('id', Integer, primary_key=True),
    Column('title', String(512), nullable=False),
    # Column('checksum', String(512)),
    Column('validated', Boolean(default=False), nullable=False),

    Column('downloader_job_id', Integer, ForeignKey('job.id')),
    Column('s3_location', String(1024)),
    Column('download_status', Enum(DownloadStatus), nullable=False,
           server_default=(DownloadStatus.NOT_STARTED)),
)
