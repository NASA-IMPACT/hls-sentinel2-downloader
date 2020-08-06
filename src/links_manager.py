# import external packages
from json import dumps as json_dump
from requests import get
from requests.auth import HTTPBasicAuth
from datetime import datetime
from thread_manager import lock

# import internal functions
from models import status, granule_count, granule, db
from utils import parse_size, convert_date, get_include_tiles_list
from log_manager import log
from settings import COPERNICUS_USERNAME, COPERNICUS_PASSWORD, SCIHUB_USERNAME, SCIHUB_PASSWORD, USE_SCIHUB_TO_FETCH_LINKS, DEBUG


'''
Product and Search URLs and API are constructed as per

https://inthub.copernicus.eu/userguide/OpenSearchAPI
https://inthub.copernicus.eu/twiki/do/view/SciHubUserGuide/FullTextSearch?redirectedfrom=SciHubUserGuide.3FullTextSearch

'''
if USE_SCIHUB_TO_FETCH_LINKS:
    AUTH = HTTPBasicAuth(
        SCIHUB_USERNAME,
        SCIHUB_PASSWORD
    )

    PRODUCT_URL = "https://scihub.copernicus.eu/dhus/odata/v1/Products('{}')/"
    SEARCH_URL = 'https://scihub.copernicus.eu/dhus/search'
else:
    AUTH = HTTPBasicAuth(
        COPERNICUS_USERNAME,
        COPERNICUS_PASSWORD
    )

    PRODUCT_URL = "https://inthub2.copernicus.eu/dhus/odata/v1/Products('{}')/"
    SEARCH_URL = 'https://inthub2.copernicus.eu/dhus/search'


# Filter to exclude tiles over Antartica
DEFAULT_TILE_FILTER = [
    '!A', '!B', '!C',
    '!(E,!23E,!26E)'
]

include_tiles = get_include_tiles_list()

platform_name = 'Sentinel-2'
processing_level = 'Level-1C'
tile_filter = DEFAULT_TILE_FILTER
rows_per_query = 100


def compile_tile_filter(args):
    '''
        construct a filename filter
    '''
    filter = ''
    for i, arg in enumerate(args):
        do_not = False
        if arg[0] == '!':
            do_not = True
            arg = arg[1:]

        f = None
        if arg[0] == '(' and arg[-1] == ')':
            f = compile_tile_filter(arg[1:-1].split(','))
            f = f'({f})'
        elif len(arg) > 1:
            f = f'(filename:*T{arg}*)'
        else:
            f = f'(filename:*T??{arg}*)'
        if do_not:
            f = f'NOT{f}'
        filter += f

        if i < len(args) - 1:
            filter += ' AND '

    return filter


def get_checksum(product_url):
    """
        Fetch checksum for the product with this id.
    """
    r = get(f'{product_url}?$format=json&$select=Checksum', auth=AUTH).json()

    return r['d']['Checksum']['Value']


def get_download_link(product_url):
    """
        Get a link to download this product.
    """
    return f'{product_url}$value'


def fetch_links(fetch_day):
    '''
        Fetch links for the given day
    '''
    log(f'started fetching links for {fetch_day}', 'status')

    global status, granule_count, granule, db

    lock.acquire()
    db.connect()
    try:
        fetch_day_available_links = granule_count.get(
            granule_count.date == fetch_day).available_links
        fetch_day_fetched_links = granule_count.get(
            granule_count.date == fetch_day).fetched_links
    except:
        granule_count.create(date=fetch_day, available_links=0,
                             fetched_links=0, last_fetched_time=datetime.now())
        fetch_day_available_links = 0
        fetch_day_fetched_links = 0
    db.close()
    lock.release()

    start_date = str(fetch_day) + 'T00:00:00Z'  # open search API format
    end_date = str(fetch_day) + 'T23:59:59Z'  # open search API format

    # Build the query for Sentinel-2 datasets for given time period.
    query = f'(platformname:{platform_name}) AND ' \
            f'(processinglevel:{processing_level}) AND ' \
            f'(ingestiondate:[{start_date} TO {end_date}]) '  # alternative is beginposition

    # if tile_filter is not None:
    #    query = f'{query} AND {compile_tile_filter(tile_filter)}'

    start = fetch_day_fetched_links
    total_fetched_entries = fetch_day_fetched_links

    params = {
        'q': query,
        'rows': rows_per_query,
        'format': 'json',
        'orderby': 'ingestiondate desc',  # alternative is beginposition
        'start': start
    }

    # Continuously call the search API until all entries have been fetched.
    while True:

        log(f'fetching {SEARCH_URL} with params {json_dump(params)}', 'links')

        try:
            response = get(SEARCH_URL, params, auth=AUTH)
        except Exception as e:
            log(f"unable fetch links {str(e)}", "error")

        log(f'fetched {SEARCH_URL} with status {response.status_code}', 'links')

        if response.status_code == 200:
            feed = response.json()['feed']

            if 'opensearch:totalResults' not in feed or 'entry' not in feed:
                # Can happen when there's no result or all links are fetched
                log(f'all links fetched for {fetch_day}', 'status')
                log(f'all links fetched for {fetch_day}', 'links')
                return

            total_results = int(feed['opensearch:totalResults'])

            if (fetch_day_available_links == total_results) and (fetch_day_fetched_links == total_results):
                # ee.emit('links_fetched',fetch_day)
                break

            entries = feed['entry']
            fetched_entries = len(entries)

            lock.acquire()
            db.connect()
            granule_counter = granule_count.get(
                granule_count.date == fetch_day)
            granule_counter.available_links = total_results
            granule_counter.save()
            db.close()
            lock.release()

            try:
                for entry in entries:
                    id = entry['id']

                    for d in entry['date']:
                        if d['name'] == "beginposition":
                            beginposition = convert_date(d['content'])
                        elif d['name'] == "endposition":
                            endposition = convert_date(d['content'])
                        elif d['name'] == "ingestiondate":
                            ingestiondate = convert_date(d['content'])

                    for s in entry['str']:
                        if s['name'] == "uuid":
                            uuid = s['content']
                        elif s['name'] == "size":
                            size = parse_size(s['content'])
                        elif s['name'] == "filename":
                            filename = s['content']
                        elif s['name'] == "tileid":
                            tileid = s['content']

                    #log(f'getting checksum for {id}','links')
                    checksum = get_checksum(PRODUCT_URL.format(id))
                    #log(f'got checksum {checksum} for {id}','links')

                    download_url = get_download_link(PRODUCT_URL.format(id))

                    if USE_SCIHUB_TO_FETCH_LINKS:
                        download_url = download_url.replace(
                            'scihub', 'inthub2')

                    if(tileid in include_tiles):
                        ignore_file = False
                    else:
                        ignore_file = True

                    lock.acquire()
                    db.connect()

                    # check and add only a new link in the database
                    try:
                        granule_exists = granule.create(id=id, filename=filename, tileid=tileid, size=size, checksum=checksum, beginposition=beginposition, endposition=endposition,
                                                        ingestiondate=ingestiondate, download_url=download_url, downloaded=False, in_progress=False, uploaded=False, ignore_file=ignore_file, retry=0)
                    except Exception as e:
                        log(f'skipping {id} as it already exists in database', 'links')

                    db.close()
                    lock.release()

            except TypeError as e:
                log(f'Type error for entry object {str(entry)}', 'error')

            total_fetched_entries += fetched_entries
            params['start'] += fetched_entries

            lock.acquire()
            db.connect()
            last_linked_fetched_time = status.get(
                status.key_name == 'last_linked_fetched_time')
            last_linked_fetched_time.value = str(datetime.now())
            last_linked_fetched_time.save()
            db.close()
            lock.release()

            lock.acquire()
            db.connect()
            try:
                granule_counter = granule_count.get(
                    granule_count.date == fetch_day)
                granule_counter.fetched_links = total_fetched_entries
                granule_counter.last_fetched_time = datetime.now()
                granule_counter.save()
                log(f'{total_fetched_entries} links fetched for {fetch_day}', 'links')
            except Exception as e:
                log(f'error: {str(e)}, {filename}', 'error')

            db.close()
            lock.release()

            if (total_fetched_entries >= total_results):
                break
