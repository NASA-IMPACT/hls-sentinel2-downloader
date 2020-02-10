from os import environ
from requests import get
from requests.auth import HTTPBasicAuth


class Product:
    URL = "https://inthub2.copernicus.eu/dhus/odata/v1/Products('{}')/"
    AUTH = HTTPBasicAuth(
        environ['COPERNICUS_USERNAME'],
        environ['COPERNICUS_PASSWORD']
    )

    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.link = Product.URL.format(id)
        self.checksum = None

    def get_checksum(self):
        if self.checksum is None:
            r = get(f'{self.link}?$format=json&$select=Checksum',
                    auth=Product.AUTH).json()
            self.checksum = r['d']['Checksum']['Value']
        return self.checksum

    def get_download_link(self):
        return f'{self.link}$value'
