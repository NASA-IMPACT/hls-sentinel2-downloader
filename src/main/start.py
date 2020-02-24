from os import environ
from time import sleep  # , time
from multiprocessing import Process, Manager
from datetime import datetime, date, timedelta

from helpers.logger import logger
from setup_db import setup_db
from serializer import Serializer
from models.job import job, JobStatus
from workflow import Workflow


def get_default_date():
    today = date.today()
    yesterday = today + timedelta(days=-1)
    return yesterday


def start_workflow(shared_state, start_date=None, review_number=0):
    shared_state.job_id = None
    shared_state.completed = False

    max_downloads = environ.get('MAX_DOWNLOADS')
    max_upload_workers = int(environ.get('MAX_UPLOADERS', 20))

    workflow = Workflow(
        start_date or get_default_date(), review_number,
        max_downloads, max_upload_workers
    )

    try:
        workflow.start(shared_state)
    except Exception:
        if shared_state.job_id is not None:
            db_connection = setup_db().connect()
            job_serializer = Serializer(db_connection, job)
            job_serializer.put(shared_state.job_id, {
                'status': JobStatus.FAILED,
            })


def start_missed_job(job_serializer, shared_state):
    failed_job = job_serializer.first(
        params={
            'needs_review': True,    # Or should this be NOT STARTED
        },
        order_by=[
            'review_number',
            'start_time',
        ]   # Find the earliest failed Job with least reviews yet.
    )
    if failed_job is None:
        return None

    date = failed_job['date_handled']
    p = Process(target=start_workflow,
                args=(shared_state, date, failed_job['review_number'] + 1))
    p.start()

    job_serializer.put(failed_job['id'], {
        'needs_review': False,
    })
    return p


def start_main_job(shared_state):
    p = Process(target=start_workflow, args=(shared_state,))
    p.start()
    return p


def main():
    manager = Manager()
    shared_state = manager.Namespace()

    db_connection = setup_db().connect()
    job_serializer = Serializer(db_connection, job)

    # TODO: Check if today's job is already running.
    # If so, just go with missed jobs.
    p = start_main_job(shared_state)

    end_time = datetime.now()\
        .replace(hour=23, minute=30, second=0, microsecond=0)

    while True:
        sleep(5)

        p.join(timeout=0)
        if not p.is_alive():
            p = start_missed_job(job_serializer, shared_state)
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


if __name__ == '__main__':
    main()
