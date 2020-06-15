
# import external packages
from peewee import *

# import internal functions
from thread_manager import lock
from settings import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

# create database instance
db = MySQLDatabase(DB_NAME, user=DB_USER, password=DB_PASS,
                   host=DB_HOST, port=DB_PORT)


'''
    peewee database tables definition
'''


class BaseModel(Model):
    class Meta:
        database = db


class status(BaseModel):
    key_name = CharField(primary_key=True)
    value = TextField()


class granule_count(BaseModel):
    date = DateField(primary_key=True)
    available_links = IntegerField()
    fetched_links = IntegerField()
    last_fetched_time = DateTimeField()


class granule(BaseModel):
    id = CharField(primary_key=True, index=True)
    filename = TextField()
    tileid = TextField()
    size = BigIntegerField()
    checksum = TextField()
    beginposition = DateTimeField()
    endposition = DateTimeField()
    ingestiondate = DateTimeField()
    download_url = TextField()
    downloaded = BooleanField()
    in_progress = BooleanField(default=False)
    uploaded = BooleanField(default=False)
    ignore_file = BooleanField(default=False)
    download_started = DateTimeField(null=True)
    download_finished = DateTimeField(null=True)
    download_failed = DateTimeField(default=False)
    retry = IntegerField(default=0)


table_list = [status, granule_count, granule]


def create_tables():
    db.create_tables(table_list)


def drop_tables():
    db.drop_tables(table_list)


'''
    create tables if they don't exists
'''
lock.acquire()
db.connect()
create_tables()
db.close()
lock.release()

# create default status keys
lock.acquire()
db.connect()

try:
    status_key = status.get(status.key_name == 'last_linked_fetched_time')
except Exception:
    status.create(key_name='last_linked_fetched_time', value=0)

try:
    status_key = status.get(status.key_name == 'last_file_uploaded_time')
except Exception:
    status.create(key_name='last_file_uploaded_time', value=0)

try:
    status_key = status.get(status.key_name == 'last_file_download_time')
except Exception:
    status.create(key_name='last_file_download_time', value=0)

db.close()
lock.release()
