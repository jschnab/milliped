# Milliped

## Introduction

Milliped is a flexible framework that helps browsing websites and extract 
information from pages automatically, that is to say web scraping.

Milliped breaks down web scraping into three activities:

* browse: Navigating from page to page and building a sequence of pages of
  interest (i.e. pages that contains information we want to extract).
* harvest: Downloading pages of interest and store their HTML code.
* extract: Parse the HTML code of harvested pages, extract information from
  parsed data, then store results.

Separating browsing, harvesting, and extracting into distinct activities has
several benefits: it is easier to enforce data immutability (data is not
overwritten once produced), reproducibility (the output of browsing,
harvesting, and extraction is stored separately), distribution of scraping
across processes or machines.

## How to install

Using [pip](https://pypi.org/project/pip/) is the easiest way to install
Millipede. If you are not sure you have `pip` installed, check by running:

```
pip -V
```

You may have to run `pip3` instead of `pip`. Verify the output shows a version
of Python greater than or equal to 3.6.

If necessary, install `pip` by following the instructions from [this
page](https://pip.pypa.io/en/stable/installation/).

Download the Milliped code repository, then navigate to the root folder of the
repository and finally run:

```
pip3 install .
```

## First steps with Milliped

Milliped is a very flexible framework with many features and options. To
simplify its use for first-timers, Milliped provides a `SimpleBrowser` class
with sensible defaults. This class does not scrape very useful data, the goal
is to give a sense of how Milliped browser objects should be used.

To get started with `SimpleBrowser`, you just need the URL of a website you
would like to crawl, and a function that extracts information from a
`BeautifulSoup` object. Choose a website that allows you to crawl it, you can
search online the words "scraping sandbox" if you need inspiration. Make sure
you respect the rules described in "terms of use" and the file `robots.txt` of
the file you would like to crawl.

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

Now you should be ready to go. You can check logs in the file `browser.log`
that should be in your current folder.

To start browsing the website, run:

```
browser.browse()
```

The `browse` method will traverse the website in a breadth-first search
fashion, by maintaining a queue of URLs parsed from each web page. Every page
queued for browsing by `SimpleBrowser` is also queued for harvesting, so these
pages can be downloaded for actual data extraction using the following command:

```
browser.harvest()
```

`SimpleBrowser` is configured to download the HTML code of every page
previously queued for harvesting and store it in compressed archives that
follow the naming pattern `harvest_x.bz2` where `x` is the file number. This is
because file size is capped at 100MB so once a file reaches this size a new
file is produced.

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

Now that you are familiar with how to use Milliped `Browser` classes, we will
have a look at how you can create your own browser object that fits your
specific use-case.
