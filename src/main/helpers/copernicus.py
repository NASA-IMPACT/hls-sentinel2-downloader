"""
copernicus.py
Created On: Jan 27, 2020
Created By: Bibek Dahal
"""
from requests import get
from helpers.product import Product


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
        start_date: Minimum ingestion date for searching.
        end_date: Maximum ingestion date for searching.
        platform_name: Platform name to search for in the data hub archive.
                       Defaults to 'Sentinel-2' for Sentinel-2 data.
        rows_per_query: Number of rows to return in each request.
                        Defaults to 100.
        """

        # Sometimes the dates only contain date part and not time.
        # Fix it as the copernicus API needs time part as well.
        if 'T' not in start_date:
            start_date = start_date + 'T00:00:00Z'
        if 'T' not in end_date:
            end_date = end_date + 'T00:00:00Z'

        # Build the query for Sentinel-2 datasets for given time period.
        query = f'(platformname:{platform_name}) AND ' \
                f'ingestiondate:[{start_date} TO {end_date}]'

        # Collect the query params.
        self.params = {
            'q': query,
            'rows': rows_per_query,
            'format': 'json',
            'orderby': 'ingestiondate asc'
        }

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
            response = get(Copernicus.URL, params=params, auth=Product.AUTH)

            if response.status_code == 200:
                feed = response.json()['feed']

                if 'opensearch:totalResults' not in feed or \
                        'entry' not in feed:
                    # Can happen when there's no result.
                    break

                total_results = int(feed['opensearch:totalResults'])
                entries = feed['entry']
                fetched_entries = len(entries)

                yield from [
                    Product(
                        entry['id'],
                        entry['title'],
                        entry['date'][0]['content']
                    )
                    for entry in entries
                ]

                total_fetched_entries += fetched_entries
                start += fetched_entries

                if (total_fetched_entries >= total_results):
                    break
