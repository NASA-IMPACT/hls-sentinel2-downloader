from granule_validator import GranuleValidator
from setup_db import setup_db


def handler(event, context):
    db_connection = setup_db().connect()
    GranuleValidator(db_connection).validate_all()
    return None
