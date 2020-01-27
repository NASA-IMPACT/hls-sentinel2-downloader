"""
copernius.py
Created On: Jan 27, 2020
Created By: Bibek Dahal
"""
from os import environ
from requests import get
from requests.auth import HTTPBasicAuth


class Copernicus:
    """
    Handler to fetch Sentinel-2 data urls.
    It uses the search API to fetch N (default=100) entries per request
    and makes multiple requests until no more data is available.
    """

    # Copernicus search URL
    URL = 'https://inthub2.copernicus.eu/dhus/search'

    def __init__(
        self,
        start_date,
        end_date,
        platform_name='Sentinel-2',
        rows_per_query=100
    ):
        """
        start_date: Minimum ingestion date for returned urls in ISO8061 format.
        end_date: Maximum ingestion date for returned urls in ISO8061 format.
        platform_name: Platform name to search for in data hub archive.
                       Defaults to 'Sentinel-2' for Sentinel-2 data.
        rows_per_query: Number of rows to return in each request.
                        Defaults to 100.
        """

        # Build the query for Sentinel-2 datasets for given time period.
        query = f'(platformname:{platform_name}) AND ' \
                f'ingestiondate:[{start_date} TO {end_date}]'
        print(query)

        # Collect the query params.
        self.params = {
            'q': query,
            'rows': rows_per_query,
            'format': 'json',
        }

        # Create the authentication header.
        self.auth = HTTPBasicAuth(
            environ['COPERNICUS_USERNAME'],
            environ['COPERNICUS_PASSWORD']
        )
        print(environ['COPERNICUS_USERNAME'])

    def read_feed(self):
        """
        Start fetching the URL entries.

        Returns a generator yielding the each entry for the search results.
        """

        start = 0
        total_fetched_entries = 0

        # Continuously call the search API until all entries have been fetched.
        while True:
            params = {
                **self.params,
                'start': start,
            }
            response = get(Copernicus.URL, params=params, auth=self.auth)

            if response.status_code == 200:
                feed = response.json()['feed']
                print(feed)

                if 'opensearch:totalResults' not in feed or \
                        'entry' not in feed:
                    # Can happen when there's no result.
                    break

                total_results = int(feed['opensearch:totalResults'])
                entries = feed['entry']
                fetched_entries = len(entries)

                yield from entries

                total_fetched_entries += fetched_entries
                start += fetched_entries

            if (total_fetched_entries >= total_results):
                break