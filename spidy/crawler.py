#!/usr/bin/env python3
"""
spidy Web Crawler v2.0
Built by rivermont
"""

import argparse
import logging
import threading
import requests
import re
import time

import networkx as nx
import matplotlib.pyplot as plt

from hashlib import sha256

import resource

# try:
#     from spidy import __version__
# except ImportError:
#     from __init__ import __version__


# Setup
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.WARNING)

parser = argparse.ArgumentParser(
    description="Crawls the web and creates a connection map of the internet."
)


# Resource limiting

# GB to byte conversion:
# 32 - 34359738368
# 16 - 17179869184
# 8  - 8589934592
# 4  - 4294967296
# 1  - 1073741824

# Memory limit for the program, in bytes
limit = 10000000000

rsrc = resource.RLIMIT_DATA
soft, hard = resource.getrlimit(rsrc)
resource.setrlimit(rsrc, (limit, hard))

# Memory cleanup from memory limiting
del soft, hard, rsrc, limit


# Time statements
def get_time():
    return time.strftime('%H:%M:%S')


def get_full_time():
    return time.strftime('%H:%M:%S, %A %b %Y')


#############
# ARGUMENTS #
#############

# -v: verbose logging level (logging.DEBUG=-vvv, INFO=-vv, WARNING=-v (default), CRITICAL always shows)
# parser.add_argument('--verbose', '-v', action='count')

# -q, --quiet: quiet (restricts to logging.CRITICAL)
# -qq: no output
# --version
# -h, --headers: Set HTTP headers
# -d, --depth: How many links to stop after. Default is 100, 0 crawls forever but will crash
# -if: File to read starting link pool from
# T/F save image file
# T/F display image file
# T/F restrict all considered links to parsable ones (doesn't display or crawl images etc)
# --label: display subdomains on central nodes
# -l: Number of connections required to show a label
# -t, --title: Title to display in the image
# HTTP request timeout (seconds)
# Save content of urls to folder
# Limit
# -z, --zip: zip downloaded files every n pages
# --log: save output to a .log file


#############
# VARIABLES #
#############

# Regex
url_exp = r'''((?:https?|ftp):\/\/(?:www\.)?(?:(?:-|[0-9]|[A-Z]|[a-z])+\.)+(?:(?:[0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])com|org|edu|gov|uk|net|ca|de|jp|fr|au|us|ru|ch|it|nl|se|no|es|mil|fi|cn|br|be|at|info|pl|dk|cz|cl|hu|nz|il|ie|za|tw|kr|mx|gr|ar|co|ly|gl)(?:[\/]|[\-\?\+\=\_\&\%\#~\.]|[0-9]|[A-Z]|[a-z])+)'''
# url_exp = r'''(?:(?:https?|ftp):\/\/)?(?:www\.)?(?:(?:-|[0-9]|[A-Z]|[a-z])+\.)+(?:(?:[0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])|com|org|edu|gov|uk|net|ca|de|jp|fr|au|us|ru|ch|it|nl|se|no|es|mil|fi|cn|br|be|at|info|pl|dk|cz|cl|hu|nz|il|ie|za|tw|kr|mx|gr|ar|co|ly|gl)(?:[\/]|[\-\?\+\=\_\&\%\#~\.]|[0-9]|[A-Z]|[a-z])+'''
dom_exp = r'''(?:https?:\/\/(?:www\.)?)((?:(?:-|[0-9]|[A-Z]|[a-z])+\.)+(?:[0-9]|[A-Z]|[a-z])+)'''
mime_exp = r'''(?:application|audio|font|image|message|model|multipart|text|video|plain|binary)\/(?:(?:[a-z]|[A-Z]|[0-9])+|[\.\+-])+'''

# Data format:  {hashID: [url, parsable, {hashID, ...}, crawled]}
data = {}

# headers = {
#     'User-Agent': 'spidy Web Crawler (Mozilla/5.0; bot; +https://github.com/rivermont/spidy/)',
#     'Accept-Language': 'en_US, en-US, en',
#     'Accept-Encoding': 'gzip',
#     'Connection': 'keep-alive'
# }

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:56.0) Gecko/20100101 Firefox/56.0',
    'Accept-Language': 'en_US, en-US, en',
    'Accept-Encoding': 'gzip',
    'Connection': 'keep-alive'
}

parsable_types = [
    # MIME types that are textual and may contain links
    'text/html',
    'application/html',
    'application/xml',
    'text/plain',
    'text/javascript',
    'text/xml',
    'text/css',
    'application/javascript',
    'application/x-javascript',
    'application/json',
    'application/rss+xml',
    'application/atom+xml',
    'text/turtle',
    # Not an official IANA type but still found in the wild
    'plain/text',
]


###########
# CLASSES #
###########

class Counter(object):
    """Thread safe incrementing counter."""

    def __init__(self, value=0):
        self.lock = threading.Lock()
        self._int = value

    def inc(self):
        with self.lock:
            self._int += 1

    def dec(self):
        with self.lock:
            self._int -= 1

    def value(self):
        with self.lock:
            return self._int


class ThreadSafeSet(list):
    """Thread safe set."""

    def __init__(self):
        self.lock = threading.Lock()
        self._set = set()

    def __len__(self):
        return len(self._set)

    def __bool__(self):
        return bool(self._set)

    def __iter__(self):
        return self.__iter__()

    def get(self):
        with self.lock:
            return self._set.pop()

    def add(self, o):
        with self.lock:
            self._set.add(o)

    def update(self, o):
        with self.lock:
            self._set.update(o)

    def get_all(self):
        with self.lock:
            return self._set

    def clear(self):
        with self.lock:
            self._set.clear()


def count(start=0, step=1):
    """Duplicate of itertools.count"""
    n = start
    while True:
        yield n
        n += step


#############
# FUNCTIONS #
#############

def get_uid(string):
    """Returns a unique ID."""
    s = string.encode('utf-8')
    return sha256(s).hexdigest()


def crop_urls(connections_required=10):
    """Returns a dictionary made from global ids,
    with the same keys but values have been cropped to the subdomain level."""
    result = {}
    for a in data:
        if len(data[a][2]) > connections_required:
            # b = re.match(dom_exp, data[a][0]).group()
            b = data[a][0]
        else:
            b = ''
        result.update({a: b})

    return result


def make_graph():
    logging.debug('Creating graph...')
    mg = nx.Graph()
    plt.figure(figsize=(16, 16))

    logging.debug('Adding content to graph...')
    for obj in data:
        for b in data[obj][2]:
            mg.add_node(obj)
            mg.add_edge(obj, b)

    logging.info('Drawing the graph...')
    nx.draw(mg, node_size=25,
            width=1,
            # labels=crop_urls(),
            node_color='b',
            font_color='r'
            )

    logging.info('Saving the graph...')
    plt.savefig('../graphs/graph_{0}.png'.format(get_time()), format="PNG")
    # logging.info('Displaying the graph...')
    # plt.show()


def get_mime_type(content):
    """
    Extracts the Content-Type header from the headers returned by page.
    """
    doc_type = ''  # Satisfy PEP8
    try:
        doc_type = str(content.headers['content-type'])
        doc_type = re.search(mime_exp, doc_type).group()
    except Exception as e:
        err_mro = type(e).mro()
        if KeyError in err_mro:  # If no Content-Type was returned, return blank
            logging.warning('No content-type returned')
        if AttributeError in err_mro:  # Invalid MIME type
            logging.warning('Invalid MIME in content-type "{0}"'.format(doc_type))

    return doc_type


def register_url(url, parsable=True, crawled=False):
    uid = get_uid(url)
    if uid in data:
        logging.debug("URL already in database: {0}".format(url))
        return uid
    else:
        data.update({uid: [url, parsable, set(), crawled]})
        logging.debug("Added new url to database: {0} as {1}".format(url, uid))
    return uid


def get_page(url):
    """Performs the requests.get() to retrieve url and does any error catching."""
    try:
        page = requests.get(url, headers=headers, timeout=10)
        return page

    except Exception as e:
        logging.warning("An error was raised trying to get {0}".format(url))
        err_mro = type(e).mro()

        if requests.exceptions.ReadTimeout in err_mro:
            logging.warning("Connection timed out")
        elif requests.exceptions.TooManyRedirects in err_mro:
            logging.warning("Too many redirects")
        elif requests.exceptions.ChunkedEncodingError in err_mro:
            logging.warning("Chunked encoding error")
        elif requests.exceptions.ConnectionError in err_mro:
            logging.warning("Connection Error")
        else:
            raise e

    # In the case of an error, return an blank Response object
    return requests.models.Response()


def process_link(url):
    uid = register_url(url)
    if data[get_uid(url)][3]:
        return None
    raw_links = crawl_link(url)
    if raw_links:
        for l in raw_links:
            pool.add(l)
            new_uid = register_url(l)
            data[uid][2].add(new_uid)
            del new_uid
    else:
        data[uid][1] = False

    data[uid][3] = True


def crawl_link(url):
    logging.info("Starting crawl on {0}".format(url))
    page = get_page(url)
    mime = get_mime_type(page)
    if mime not in parsable_types:
        logging.debug("Unparsable MIME type {0}".format(mime))
        return []
    del mime
    logging.debug("Received response.")
    content = page.text
    logging.debug("Parsing out links.")
    links = re.findall(url_exp, content)
    return links


def graceful_exit():
    make_graph()
    exit()


def main():
    pool = ThreadSafeSet()
    global pool

    # Starting link pool
    pool.update(["https://www.reddit.com/r/all/new/"])

    counter = Counter()

    while pool:
        process_link(pool.get())

        counter.inc()
        if counter.value() == 100:
            break
        if counter.value() % 50 == 0:
            print(counter.value())

    print('Done crawling.')
    print('Pool size: {0}'.format(len(pool)))
    # Memory cleanup to make room for graphing
    del counter, pool

    make_graph()

    data.clear()


if __name__ == "__main__":
    try:
        for i in range(1, 10):
            main()
    except KeyboardInterrupt:
        logging.error('KeyboardInterrupt')
        graceful_exit()
    except MemoryError:
        logging.critical('Ran out of memory! Shutting down...')
        exit()
