from os import environ
from time import sleep  # , time
from multiprocessing import Process, Manager
from datetime import datetime, date

from setup_db import setup_db
from serializer import Serializer
from models.job import job, JobStatus
from workflow import Workflow


def start_workflow(shared_state, start_date=None, review_number=0):
    shared_state.job_id = None
    shared_state.completed = False

    max_downloads = int(environ.get('MAX_DOWNLOADS', 30))
    max_upload_workers = int(environ.get('MAX_UPLOADERS', 20))

    workflow = Workflow(
        start_date or date.today(), review_number,
        max_downloads, max_upload_workers
    )

    # start_time = time()
    # print('Starting downloads', start_time, flush=True)

    try:
        workflow.start(shared_state)
    except Exception:
        if shared_state.job_id is not None:
            db_connection = setup_db().connect()
            job_serializer = Serializer(db_connection, job)
            job_serializer.put(shared_state.job_id, {
                'status': JobStatus.FAILED,
            })

    # end_time = time()
    # print('Finishing downloads', end_time, flush=True)
    # print('Total time', end_time - start_time, flush=True)


def start_main_job(shared_state):
    p = Process(target=start_workflow, args=(shared_state,))
    p.start()
    return p


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


def main():
    manager = Manager()
    shared_state = manager.Namespace()

    db_connection = setup_db().connect()
    job_serializer = Serializer(db_connection, job)

    p = start_main_job(shared_state)

    end_time = datetime.now()\
        .replace(hour=23, minute=30, second=0, microsecond=0)

    while True:
        sleep(30)

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
