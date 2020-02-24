"""
product.py
Created On: Feb 10, 2020
Created By: Bibek Dahal
"""
from os import environ
from requests import get
from requests.auth import HTTPBasicAuth


class Product:
    """
    Sentinel product incorporating it's id, title, link and checksum.
    """
    URL = "https://inthub2.copernicus.eu/dhus/odata/v1/Products('{}')/"
    AUTH = HTTPBasicAuth(
        environ['COPERNICUS_USERNAME'],
        environ['COPERNICUS_PASSWORD']
    )

    def __init__(self, id, title, ingestion_date):
        """
        id: Unique product id.
        title: Product title.
        """
        self.id = id
        self.title = title
        self.link = Product.URL.format(id)
        self.ingestion_date = ingestion_date
        self.checksum = None

    def get_checksum(self):
        """
        Fetch checksum for the product with this id.
        """
        if self.checksum is None:
            r = get(f'{self.link}?$format=json&$select=Checksum',
                    auth=Product.AUTH).json()
            self.checksum = r['d']['Checksum']['Value']
        return self.checksum

    def get_download_link(self):
        """
        Get a link to download this product.
        """
        return f'{self.link}$value'
