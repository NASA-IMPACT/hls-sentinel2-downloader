from os import environ
from alembic import config as alembic_config
from sqlalchemy import create_engine


DB_URL = environ.get('DB_URL') or 'postgresql://postgres:postgres@localhost/postgres'  # noqa


def setup_db():
    engine = create_engine(DB_URL)
    alembic_args = [
        '--raiseerr',
        'upgrade', 'head',
    ]
    alembic_config.main(argv=alembic_args)
    return engine
