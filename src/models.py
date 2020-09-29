# import external packages
from peewee import *

# import internal functions
from thread_manager import lock
from settings import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER
from log_manager import log

# create database instance
db = MySQLDatabase(DB_NAME, user=DB_USER, password=DB_PASS,
                   host=DB_HOST, port=DB_PORT)


def db_connect():
    '''
    connect to the database
    this function is just a wrapper against db.connect method but enclosed in a try/catch block
    sometimes database times out so this centralized method can be used to log error messages
    '''
    try:
        db.connect()
    except Exception as e:
        log(f'could not connect to the database: {str(e)}', 'error')
        # if lock.locked_lock() == True:
        # lock.release()


def db_close():
    '''
    close the connection to the database
    this function is just a wrapper against db.close method but enclosed in a try/catch block
    sometimes database times out so this centralized method can be used to log error messages
    '''
    try:
        db.close()
    except Exception as e:
        log(f'could not connect to the database: {str(e)}', 'error')


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
    expired = BooleanField(default=False)
    retry = IntegerField(default=0)


table_list = [status, granule_count, granule]


def create_tables():
    '''
    create all tables
    '''
    db.create_tables(table_list)


def drop_tables():
    '''
    drop all tables
    this method is only used during initial development or when you had to delete the database tables
    '''
    db.drop_tables(table_list)


'''
    create tables if they don't exists
'''
try:
    lock.acquire()
    db_connect()
    create_tables()
    db_close()
    lock.release()
except Exception as e:
    log(f'failed database table status check: {str(e)}', 'error')
    if lock.locked_lock() == True:
        lock.release()


# create default status keys
lock.acquire()
db_connect()

try:
    status_key = status.get(status.key_name == 'last_linked_fetched_time')
except OperationalError as ops_err:
    log(f'could not connect to the database: {str(ops_err)}', 'error')
except Exception as e:
    status.create(key_name='last_linked_fetched_time', value=0)

try:
    status_key = status.get(status.key_name == 'last_file_uploaded_time')
except OperationalError as ops_err:
    log(f'could not connect to the database: {str(ops_err)}', 'error')
except Exception:
    status.create(key_name='last_file_uploaded_time', value=0)

try:
    status_key = status.get(status.key_name == 'last_file_download_time')
except OperationalError as ops_err:
    log(f'could not connect to the database: {str(ops_err)}', 'error')
except Exception:
    status.create(key_name='last_file_download_time', value=0)

db_close()

if lock.locked_lock() == True:
    lock.release()
