import enum
from sqlalchemy import (
    Table, Column,
    String, Integer, ForeignKey, Enum, Boolean, DateTime
)
from .metadata import metadata


class DownloadStatus(str, enum.Enum):
    NOT_STARTED = 'not_started'
    DOWNLOADING = 'downloading'
    SUCCESS = 'success'
    ERROR = 'error'
    INVALID = 'invalid'
    ARCHIVED = 'archived'


granule = Table(
    'granule', metadata,
    Column('uuid', String(256), primary_key=True),
    Column('title', String(512), nullable=False),
    Column('copernicus_ingestion_date', DateTime),
    Column('downloaded_at', DateTime),
    # Column('checksum', String(512)),
    Column('validated', Boolean, default=False, nullable=False),

    Column('downloader_job_id', Integer, ForeignKey('job.id')),
    Column('s3_location', String(1024)),
    Column('download_status', Enum(DownloadStatus), nullable=False,
           default=(DownloadStatus.NOT_STARTED)),
)
