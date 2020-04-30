from os import environ
from time import sleep  # , time
from multiprocessing import Process, Manager
from datetime import datetime, date, timedelta

from helpers.logger import Logger
from setup_db import setup_db
from serializer import Serializer
from models.job import job, JobStatus
from workflow import Workflow


def get_default_date():
    days_gap = int(environ.get('DAYS_GAP', 3))
    today = date.today()
    yesterday = today + timedelta(days=-days_gap)
    return yesterday


def start_workflow(shared_state, start_date, review_number=0):
    db_connection = setup_db().connect()
    logger = Logger(db_connection)

    shared_state.job_id = None
    shared_state.completed = False

    max_downloads = environ.get('MAX_DOWNLOADS')
    if max_downloads is not None:
        max_downloads = int(max_downloads)
    max_upload_workers = int(environ.get('MAX_UPLOADERS', 20))

    try:
        workflow = Workflow(
            db_connection, logger,
            start_date,
            max_downloads, max_upload_workers,
            environ.get('ALLOW_REPEAT', 'FALSE') == 'TRUE'
        )
        workflow.start(shared_state)
    except Exception:
        logger.exception()
        if shared_state.job_id is not None:
            job_serializer = Serializer(db_connection, job)
            job_serializer.put(shared_state.job_id, {
                'status': JobStatus.FAILED,
            })


def start_past_job(shared_state):
    def_date = shared_state.default_date
    if shared_state.past_date is None:
        date = def_date + timedelta(days=-15)
    else:
        date = shared_state.past_date + timedelta(days=1)
        if def_date == date:
            return None

    shared_state.past_date = date
    p = Process(target=start_workflow, args=(shared_state, date))
    p.start()
    return p


def start_main_job(shared_state):
    date = shared_state.default_date
    p = Process(target=start_workflow, args=(shared_state, date))
    p.start()
    return p


def run_downloader(db_connection, logger):
    manager = Manager()
    shared_state = manager.Namespace()
    shared_state.default_date = get_default_date()
    shared_state.past_date = None

    job_serializer = Serializer(db_connection, job)

    # TODO: Check if today's job is already running.
    # If so, just go with missed jobs.
    logger.info('Starting the main workflow')
    p = start_main_job(shared_state)

    if environ.get('JUST_MAIN', False):
        p.join()
        return

    end_time = datetime.now()\
        .replace(hour=23, minute=30, second=0, microsecond=0)

    while True:
        sleep(5)

        p.join(timeout=0)
        if not p.is_alive():
            job_id = shared_state.job_id
            completed = shared_state.completed
            if job_id is not None and not completed:
                job_serializer.put(job_id, {
                    'status': JobStatus.FAILED,
                })

            if p.exitcode != 0:
                logger.error('Job exited unexpectedly',
                             f'Exit code: {p.exitcode}\nJob id: {job_id}')

            if datetime.now() >= end_time:
                break

            p = start_past_job(shared_state)
            if p is None:
                break

        elif datetime.now() >= end_time:
            job_id = shared_state.job_id
            completed = shared_state.completed
            if job_id is not None and not completed:
                # Time to end.
                p.terminate()
                job_serializer.put(job_id, {
                    'status': JobStatus.FAILED,
                })

    logger.info('All jobs finished.')


def main():
    db_connection = setup_db().connect()
    logger = Logger(db_connection)

    logger.info('Initializing Downloader')

    try:
        run_downloader(db_connection, logger)
    except Exception:
        logger.exception()

    logger.info('Finishing Downloader')


if __name__ == '__main__':
    main()
