# Milliped

## Introduction

Milliped is a flexible framework that helps browsing websites and extracting 
information from pages automatically. It offers a customizable `Browser` class
to carry out three main activites:

* browsing: navigating from page to page and building a sequence of pages that
  contains information we want to extract.
* harvesting: downloading pages and store their HTML code.
* extracting: parse the HTML code of harvested pages, extract information from
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

Verify the output shows a version of Python greater than or equal to 3.6.

If necessary, install `pip` by following the instructions from [pip's
documentation](https://pip.pypa.io/en/stable/installation/).

[Download](https://github.com/jschnab/milliped.git) the Milliped code
repository, then navigate to the root folder of the repository and finally run:

```
pip3 install .
```

## First steps with Milliped

Milliped is a flexible framework with many features and options. To simplify
its use for first-timers, Milliped provides a `SimpleBrowser` class with
sensible defaults.

To get started with `SimpleBrowser`, you just need two things:

* a base URL: URL of a website you would like to crawl.
* a soup parser: function that extracts information from a `BeautifulSoup`
  object.

Choose a website that allows you to crawl it, you can search online the words
"scraping sandbox" if you need inspiration. Make sure you respect the rules
described in "terms of use" and the file `robots.txt`.

In this example, we are going to crawl the website
[books.toscrape.com](https://books.toscrape.com) and extract book titles and
prices.

To extract information from web pages, we will use the function `soup_parser`
from the module `examples`.

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

`soup_parser` tries to parse book title and price from a `BeautifulSoup`
object and returns a dictionary with keys named "title" and "price".

Open your favorite Python interpreter and run:

```
from milliped import examples

browser = examples.SimpleBrowser(
    url="https://books.toscrape.com",
    soup_parser=examples.soup_parser,
)
```

You are now ready to go. You can check log messages emitted during crawling by
watching the file `browser.log` in your current folder.

To start crawling the website, run:

```
browser.browse()
```

The `browse` method will traverse the website in a breadth-first search
fashion, by maintaining a queue of URLs parsed from each web page. In the
current `SimpleBrowser` configuration, every page queued for browsing is
also queued for harvesting, so these pages can be downloaded for actual
data extraction using the following command:

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

Extraction results are saved in the file `extract.jsonl`. which follows the
[JSONLines](https://jsonlines.org) specification.

## Digging in the `Browser` class

The `Browser` class is defined in the `browser.py` module. `Browser` organizes
the three main activities that make up extracting information from a website:

* browsing: navigating from page to page and building a sequence of pages that
  contains information we want to extract).
* harvesting: downloading pages  and store their HTML code.
* extracting: parse the HTML code of harvested pages, extract information from
  parsed data, then store results.

The behavior of the `Browser` class is defined at runtime by passing arguments
to its parameters. To customize `Browser` behavior, users do not have to
subclass `Browser`, but can simply use one of the functions or classes
available in the Milliped library (or write their own) and pass it as an
argument to `Browser` at runtime.

### `Browser` parameters

The `Browser` class can be instantiated with the following parameters:

* `base_url`: URL of the website to browse (required).
* `get_browsable`: function which returns the URL of the next page
  to browse (optional, default returns all links).
* `stop_browse`: function to determine if we should stop browsing (optional,
  default is None).
* `get_harvestable`: function which returns the URL of the next
  page to harvest (required).
* `get_page_id`: function which shortens the URL into a unique ID,
  this is used when saving harvested pages (optional, default returns the MD5
  hash).
* `browse_queue`: object to store a queue of web pages to browse (required).
* `harvest_queue`: object to store a queue of web pages to parse (required).
* `download_manager`: object to manage downloading web pages (required).
* `html_parser`: parser to use with BeautifulSoup, e.g. 'html.parser',
  'lxml', etc. (optional, default is "html.parser").
* `soup_parser`: function to use to parse the HTML tags soup into
  a dictionary (required).
* `harvest_store`: object to manage storage of downloaded web pages (required).
* `extract_store`: object to manage storage of extracted data from
  parsed web pages (required).
* `logger`: configured `Logger` object from the Python standard library
  logging module (optional, default logs with the level `INFO` to the file
  `browser.log` in the current working directory).

We will discuss these parameters in more detail in the following sections. A
few parameters are used across all `Browser` activities and will be detailed
here.

#### `base_url`

This is the URL of the website. If no `initial` URL is given as an argument
to the `Browser.browse()` method, browsing will start at `base_url`. Any
relative URL encountered by `Browser` will be prepended with `base_url`.

#### `download_manager`

Milliped defines download manager objects in the module `download_managers.py`.

A `download_manager` object controls everything that deals with download of
web pages:

* Which pages are downloaded:
    * Does the file robot.txt allows it?
    * Does the page start with `base_url`?
* How pages are downloaded:
    * Retry strategy
    * Headers
    * Proxies

The class `SimpleDownloadManager` is built on top of the Python library
[requests](https://docs.python-requests.org/en/latest/) and provides basic
functionality to download web pages. Its constructor has the following
parameters:

* `base_url`: URL of the website to browse (required).
* `max_retries`: maximum number of times a request for a web page
  is made before failing (optional, default 10).
* `backoff_factor`: exponential backoff factor (optional, default 0.3).
* `retry_on`: HTTP status code of responses that lead to a request
  retry (optional, default (500, 502, 503, 504)).
* `headers`: request headers (optional, default None).
* `proxies`: list of proxies (optional, default None).
* `timeout`: timeout for requests in seconds (optional, default 3).
* `request_delay`: time in seconds to wait between requests. This value will be
  searched in robots.txt but will default to the user-defined value (optional,
  default 1).
* `logger`: logger object from the Python standard library `logging` module
  (optional, default logs messages to the file `browser.log` in the current
  working directory).

A `download_manager` object must have the following methods:

* `download()`: takes a URL, downloads the web page, then returns a tuple (status
  code, response content).
* `sleep()`: pause for the amount of time defined by `request_delay`.

#### `logger`

This is a `Logger` object from the Python standard library `logging` module.
This is configured by default with a file handler that appends messages with
level `INFO` to a file named `browser.log` in the current working directory.

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
that is defined using the `initial` parameter, then traverses the website from
link to link using breadth-first search. If no `initial` URL is given, browsing
starts from the URL passed to the `base_url` parameter of the `Browser` class.

Child URLs are collected using the function passed to the `Browser`
`get_browsable` parameter. Child URLs are added to a queue object passed to
the `Browser` parameter `browse_queue`. This queue also keeps track of which
URLs it visited, to avoid visiting a page twice and falling into an
infinite browsing loop. Another way to control when browsing stops is the
`Browser` parameter `stop_browse`. This parameter expects a function that
inspects web page contents and decides if browsing should end or not.

In addition to the `browse_queue`, the `browse()` method builds a queue of URLs
for harvesting. This queue object is passed to the `Browser` parameter
`harvest_queue`. Like `browse_queue`, `harvest_queue` keeps track of which URLs
it visited to avoid harvesting a page twice.

### Browsing parameters

#### `get_browsable`

This function takes a `BeautifulSoup` object as an argument and returns an
iterable sequence of URLs.

#### `stop_browse`

This function must take a `BeautifulSoup` object as an argument and return a
boolean that signal the `browse()` method to return if `True`. If `False`, the
`browse()` method continues.

#### `browse_queue`

This object stores objects in a first-in-first-out fashion. This queue must
keep track of which objects it already saw in the past and avoid storing again
an item it has already seen, even if this object has since been removed from
the queue.

`browse_queue` must provide the following methods:

* `enqueue()`: add an object to the queue if this object has never been added
  to the queue before.
* `dequeue()`: remove an object from the queue and return it.
* `re_enqueue()`: add an object to the queue even this object was previously
  added to the queue. This is useful to process again an object that failed to
  be processed.

`browse_queue` must provide the following attributes:

* `is_empty`: returns `True` if the queue has no elements, or `False` if the
  queue has one or more elements.

### Harvesting

Harvesting is performed by the `Browser.harvest()` method. Harvesting
sequentially goes through URLs stored in `harvest_queue`, downloads web page
contents, and store them using the object passed to the `Browser` parameter
`harvest_store`. When harvested pages are stored, they are labeled with a
string given by the function `get_page_id` so they can be uniquely identified.
Harvested web pages will later be processed during the extract phase.

### Harvesting parameters

#### `get_harvestable`

This function takes a `BeautifulSoup` object as an argument and returns an
iterable sequence of URLs.

#### `harvest_queue`

This object stores objects in a first-in-first-out fashion. This queue must
keep track of which objects it already saw in the past and avoid storing again
an item it has already seen, even if this object has since been removed from
the queue.

`harvest_queue` must provide the following methods:

* `enqueue()`: add an object to the queue if this object has never been added
  to the queue before.
* `dequeue()`: remove an object from the queue and return it.
* `re_enqueue()`: add an object to the queue even this object was previously
  added to the queue. This is useful to process again an object that failed to
  be processed.

`harvest_queue` must provide the following attributes:

* `is_empty`: returns `True` if the queue has no elements, or `False` if the
  queue has one or more elements.

#### `get_page_id`

This is a function which takes the URL of a page and returns a unique
identifier that can be used as a file name, a primary key value, etc.

#### `harvest_store`

This object manages storage of harvested web pages code. This object must have
the following methods:

* `put()`: this takes the unique identifier generated by `get_page_id` and
  contents from a web page, then stores them for later extraction.
* `get()`: this method takes no arguments and returns a tuple made of a web
  page identifier and contents.
* `__len__()`: the `harvest_store` object must be callable by the Python
  builtin function `len()`.

### Extraction

Extraction is carried out by the `Browser.extract()` method. This method
retrieves web page contents from the `harvest_store` object, generates a
`BeautifulSoup` object from web page contents, extracts information from
the `BeautifulSoup` object into a dictionary, then stores extracted information
using the `Browser.extract_store` object.

### Extraction parameters

#### `html_parser`

This is a string that is passed as the `features` parameter of the
[`BeautifulSoup`
object](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#beautifulsoup).
By default, `html_parser` is set to "html.parser".

#### `soup_parser`

This function is responsible for extracting information from the
`BeautifulSoup` object made from web page contents. It takes a `BeautifulSoup`
object as input and returns a dictionary.

#### `extract_store`

This object manages storage of extracted data. It must have have the following
methods:

* `write()`: takes a dictionary or sequence (list or tuple) of dictionaries
  containing extracted data then durably stores data.
