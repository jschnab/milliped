# Milliped

## Introduction

Milliped is a flexible framework that helps browsing websites and extract 
information from pages automatically. It offers a customizable `Browser` class
to carry out three main activites:

* browsing: Navigating from page to page and building a sequence of pages of
  interest (i.e. pages that contains information we want to extract).
* harvesting: Downloading pages of interest and store their HTML code.
* extracting: Parse the HTML code of harvested pages, extract information from
  parsed data, then store results.

Separating browsing, harvesting, and extracting into distinct activities has
several benefits: it is easier to enforce data immutability (data is not
overwritten once produced), reproducibility (the output of browsing,
harvesting, and extraction are stored separately), distribution of activities
across processes or machines.

Milliped allows to customize its behavior at every step. For example,
out-of-the-box functionality include downloading pages using basic HTTP
requests, using Tor, or using Selenium to harvest data from dynamic pages.

## How to install

Using [pip](https://pypi.org/project/pip/) is the easiest way to install
Millipede. If you are not sure you have `pip` installed, check by running:

```
pip3 -V
```

You may have to run `pip3` instead of `pip`. Verify the output shows a version
of Python greater than or equal to 3.6.

If necessary, install `pip` by following the instructions from [pip's
documentation](https://pip.pypa.io/en/stable/installation/).

Download the Milliped code repository, then navigate to the root folder of the
repository and finally run:

```
pip3 install .
```

## First steps with Milliped

Milliped is a very flexible framework with many features and options. To
simplify its use for first-timers, Milliped provides a `SimpleBrowser` class
with sensible defaults.

To get started with `SimpleBrowser`, you just need the URL of a website you
would like to crawl, and a function that extracts information from a
`BeautifulSoup` object. Choose a website that allows you to crawl it, you can
search online the words "scraping sandbox" if you need inspiration. Make sure
you respect the rules described in "terms of use" and the file `robots.txt`.

In this example, we are going to crawl the website
[books.toscrape.com](https://books.toscrape.com) and extract book titles and
prices.

Open your favorite Python interpreter and run:

```
from milliped import examples

browser = examples.SimpleBrowser(
    url="https://books.toscrape.com",
    soup_parser=examples.soup_parser,
)
```

You are now ready to go. You can check messages emitted during crawling by
watching the file `browser.log` in your current folder.

To start crawling the website, run:

```
browser.browse()
```

The `browse` method will traverse the website in a breadth-first search
fashion, by maintaining a queue of URLs parsed from each web page. Every page
queued for browsing is also queued for harvesting, so these pages can be
downloaded for actual data extraction using the following command:

```
browser.harvest()
```

`SimpleBrowser` is configured to download the HTML code of every page
previously queued for harvesting and store it in compressed archives that
follow the naming pattern `harvest_x.bz2` where `x` is the file number.
Archive size is capped at 100MB so once a file reaches this size a new
file is produced with an incremented file number.

Finally, we run the data extraction step:

```
browser.extract()
```

Extraction results are saved in the file `extract.jsonl`.

The function `examples.soup_parser` that we used as an argument to the
`SimpleBrowser` parameter `soup_parser` is the following:

```
def soup_parser(soup):
    try:
        result = {
            "title": soup.find("h1").text,
            # remove Sterling pound sign
            "price": float(soup.find("p").text.replace("\u00a3", "")),
            }
        return result
    except Exception:
        pass
    return {}
```

It tries to parse book title and price from a `BeautifulSoup` object and
returns a dictionary with keys named "title" and "price". This dictionary is
then appended to a file named `extract.jsonl` that follows the
[JSONLines](https://jsonlines.org) specification.

## Digging in the `Browser` class

The `Browser` class is defined in the `browser.py` module. `Browser` organizes
the the three main activities that make up extracting information from a
website:

* browsing: Navigating from page to page and building a sequence of pages of
  interest (i.e. pages that contains information we want to extract).
* harvesting: Downloading pages of interest and store their HTML code.
* extracting: Parse the HTML code of harvested pages, extract information from
  parsed data, then store results.

The behavior of the `Browser` class is defined at runtime by passing arguments
to its parameters. To customize `Browser` behavior, users do not have to
subclass `Browser`, but can simply use one of the functions or classes
available in the Milliped library, or write their own.

### `Browser` parameters

The `Browser` class can be instantiated with the following parameters:

* `base_url` (string): URL of the website to browse.
* `get_browsable` (callable): Function which returns the URL of the next page
  to browse.
* `stop_browse` (callable): Function to determine if we should stop browsing.
* `get_harvestable` (callable): Function which returns the URL of the next
  page to harvest.
* `get_page_id` (callable): Function which shortens the URL into a unique ID,
  this is used when saving harvested pages.
* `browse_queue` (object): Object to store a queue of web pages to browse.
* `harvest_queue` (object): Object to store a queue of web pages to parse.
* `download_manager` (object): Object to manage downloading web pages.
* `html_parser` (string): Parser to use with BeautifulSoup, e.g. 'html.parser',
  'lxml', etc.
* `soup_parser` (callable): Function to use to parse the HTML tags soup into
  a dictionary.
* `harvest_store` (object): Object to manage storage of downloaded web pages.
* `extract_store` (object): Object to manage storage of extracted data from
  parsed web pages.
* `logger` (logging.Logger): Configured logger object.

We will discuss these parameters in more detail in the following sections. A
few parameters are used across all `Browser` activities and will be detailed
here.

#### base_url

This is the URL of the website, e.g. https://www.google.com. If no `initial`
URL is given as an argument to the `Browser.browse()` method, browsing will
start at `base_url`. Any relative URL encountered by `Browser` will be
prepended with `base_url`.

#### download_manager

Milliped defines download manager objects in the module `download_manager.py`.

A `download_manager` object controls everything that deals with download of
web pages:

* which pages are downloaded
    * does the file robot.txt allows it?
    * does the page start with `base_url`?
* how pages are downloaded
    * retry strategy
    * headers
    * proxies

The class `SimpleDownloadManager` is built on top of the Python library
[requests](https://docs.python-requests.org/en/latest/) and provides basic
functionality to download web pages. Its constructor has the following
parameters:

* `base_url` (string): URL of the website to browse, required.
* `max_retries` (integer): Maximum number of times a request for a web page
  is made before failing (optional, default 10).
* `backoff_factor` (float): Exponential backoff factor (optional, default 0.3).
* `retry_on` (sequence): HTTP status code of responses that lead to a request
  retry (optional, default (500, 502, 503, 504).
* `headers` (dictionary): Request headers (optional, default None).
* `proxies` (list): List of proxies (optional, default None).
* `timeout` (float): Timeout for requests (optional, default 3).
* `request_delay` (float): Time to wait between requests. This value will be
  searched in robots.txt but will default to the user-defined value (optional,
  default 1).
* `logger` (logging.Logger): Logger object from the Python standard library
  `logging` module (optional, default logs messages to the file `browser.log`
  in the current working directory).

A `download_manager` object must have the following methods:

* `download`: Takes a URL, downloads the web page, then returns a tuple (status
  code, response content).
* `sleep`: Pause for the amount of time defined by `request_delay`.

#### logger

Logger object from the Python standard library `logging` module. This is
configured by default with a file handler that appends messages with level
`INFO` to a file named `browser.log` in the current working directory.

The Milliped `utils.py` module provides the function `get_logger` that allows
to easily configure a logger and its handlers using a dictionary as follows:

```
import logging
from milliped.utils import get_logger

log_config = {
    "handlers": [
        {
            "handler": "file",
            "handler_kwargs": {
                "filename": "browser.log",
                "mode": "a",
            },
            "format": "%(asctime)s %(levelname)s %(message)s",
            "level": logging.INFO,
        },
    ]
}

logger = get_logger(__name__, **log_config)
```

### Browsing

Browsing is carried out by the `Browser.browse()` method. It starts from a URL
that is defined using the `initial` parameter of the `browse()` method, then
traverses the website from link to link using breadth-first search. If no
`initial` URL is given, browsing starts from the URL passed to the `base_url`
parameter of the `Browser` class.

To find child URLs, `Browser` calls the function passed to the its
`get_browsable` parameter. Child URLs are added to a queue object passed to
the `Browser` parameter `browse_queue`. This queue also keeps track of which
URLs it visited, to avoid visiting a page twice and possibly fall into an
infinite browsing loop. Another way to control when browsing stops is the
`Browser` parameter `stop_browse`. This parameter expects a user-defined
function which inspects web page contents and decides if browsing should end or
not.

In addition to the `browse_queue`, the `browse()` method builds a queue of URLs
for harvesting: the `harvest_queue`. This queue object is passed to the
`Browser` parameter `harvest_queue`. Like `browse_queue`, `harvest_queue` keeps
track of which URLs it visited to avoid harvesting a page twice.

### Browsing parameters

#### get_browsable

This is a function must take `BeautifulSoup` object as an argument and return
an iterable sequence of URLs.

#### stop_browse

This function must take a `BeautifulSoup` object as an argument and return a
boolean that signal the `browse()` method to return if `True`. If `False`, the
`browse()` method continues.

#### browse_queue

This object stores objects in a first-in-first-out fashion. This queue must
keep track of which objects it already saw in the past and avoid storing again
an item it has already seen, even if this object has since been removed from
the queue.

`browse_queue` must provide the following methods:

* `enqueue()`: Add an object to the queue if this object has never been added
  to the queue before.
* `dequeue()`: Remove an object from the queue and return it.
* `re_enqueue()`: Add an object to the queue even this object was previously
  added to the queue. This is useful to process again an object that failed to
  be processed.

`browse_queue` must provide the following attributes:

* `is_empty`: Returns `True` if the queue has no elements, or `False` if the
  queue has one or more elements.

### Harvesting

Harvesting is performed by the `Browser.harvest()` method. Harvesting
sequentially goes through URLs stored in `harvest_queue`, downloads web page
contents, and store them using the object passed to the `Browser` parameter
`harvest_store`. When harvested pages are stored, they are labeled with a
string given by the function `get_page_id` so they can be uniquely identified.
Harvested web pages will later be processed during the extract phase.

### Harvesting parameters

#### get_harvestable

This is a function must take `BeautifulSoup` object as an argument and return
an iterable sequence of URLs.

#### harvest_queue

This object stores objects in a first-in-first-out fashion. This queue must
keep track of which objects it already saw in the past and avoid storing again
an item it has already seen, even if this object has since been removed from
the queue.

`harvest_queue` must provide the following methods:

* `enqueue()`: Add an object to the queue if this object has never been added
  to the queue before.
* `dequeue()`: Remove an object from the queue and return it.
* `re_enqueue()`: Add an object to the queue even this object was previously
  added to the queue. This is useful to process again an object that failed to
  be processed.

`harvest_queue` must provide the following attributes:

* `is_empty`: Returns `True` if the queue has no elements, or `False` if the
  queue has one or more elements.

#### get_page_id

This is a function which takes the URL of a page and returns a unique
identifier that can be used as a file name, a primary key value, etc.

#### harvest_store

This object manages storage of harvested web pages code. This object must have
the following methods:

* `put()`: This takes the unique identifier generated by `get_page_id` and
  contents from a web page, then stores them for later extraction.
* `get()`: This method takes no arguments and returns a tuple made of a web
  page identifier and contents.
* `__len__()`: The `harvest_store` object must be callable by the Python
  builtin function `len()`.

### Extraction

Extraction is carried out by the `Browser.extract()` method. This method
retrieves web page contents from the `harvest_store` object, generates a
`BeautifulSoup` object from web page contents, extracts information from
the `BeautifulSoup` object into a dictionary, then stores extracted information
using the `Browser.extract_store` object.

### Extraction parameters

#### html_parser

This is a string that is passed as the `features` parameter of the
[`BeautifulSoup`
object](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#beautifulsoup).
By default, `html_parser` is set to "html.parser`.

#### soup_parser

This function is responsible for extracting information from the
`BeautifulSoup` object made from web page contents. It takes a `BeautifulSoup`
object as input and returns a dictionary.

#### extract_store

This object manages storage of extracted data. It must have have the following
methods:

* `write()`: Takes a dictionary or sequence (list or tuple) of dictionaries
  containing extracted data then durably stores data.
