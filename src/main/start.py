from os import environ
from time import time
from workflow import Workflow


def main():
    max_downloads = int(environ.get('MAX_DOWNLOADS', 30))
    max_upload_workers = int(environ.get('MAX_UPLOADERS', 20))

    workflow = Workflow(
        '2020-01-28T00:00:00.000Z',
        '2020-01-29T00:00:00.000Z',
        max_downloads, max_upload_workers
    )

    start_time = time()
    print('Starting downloads', start_time, flush=True)

    workflow.stop()

    end_time = time()
    print('Finishing downloads', end_time, flush=True)
    print('Total time', end_time - start_time, flush=True)


if __name__ == '__main__':
    main()
