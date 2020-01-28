from itertools import islice

from copernicus import Copernicus

copernicus = Copernicus(
    start_date='2020-01-19T00:00:00.000Z',
    end_date='2020-01-20T00:00:00.000Z'
)

urls = []
for entry in islice(copernicus.read_feed(), 50):
    urls.append(entry['link'][0]['href'])
    print(urls[-1])
