
from os import environ
from requests import get
from requests.auth import HTTPBasicAuth

from serializer import Serializer
from models.granule import granule, DownloadStatus


class GranuleValidator:
    URL = "https://inthub2.copernicus.eu/dhus/odata/v1/Products('{}')/"
    AUTH = HTTPBasicAuth(
        environ['COPERNICUS_USERNAME'],
        environ['COPERNICUS_PASSWORD']
    )

    def __init__(self, db_connection):
        self.serializer = Serializer(db_connection, granule)

    def validate_all(self):
        granules = self.serializer.get_all(
            params={'validated': False},
            fields=['uuid', 'checksum']
        )
        for g in granules:
            self._validate_granule(g['uuid'], g['checksum'])

    def _validate_granule(self, id, checksum):
        link = GranuleValidator.URL.format(id)
        r = get(f'{link}?$format=json&$select=Checksum',
                auth=GranuleValidator.AUTH).json()
        src_checksum = r['d']['Checksum']['Value'].upper()
        if src_checksum == checksum:
            self.serializer.put(id, {
                'validated': True,
            })
        else:
            self.serializer.put(id, {
                'validated': True,
                'download_status': DownloadStatus.INVALID
            })
