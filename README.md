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
would like to crawl. Choose a website that allows you to crawl it (for example
[books.toscrape.com](https://books.toscrape.com) or search online "scraping
sandbox" if you have no idea), and make sure you respect the rules described
in "terms of use" and or the file `robots.txt`. Then open your favorite Python
interpreter and run:

```
from milliped import SimpleBrowser

browser = SimpleBrowser(url="https://books.toscrape.com")
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

`SimpleBrowser` is configured to extract the title and URL of a most one link
(HTML `a` element) in each harvested page, and store it in a dictionary with
keys named "title" and "url". This dictionary is then appended to a file named
`extract.jsonl` that follows the [JSONLines](https://jsonlines.org)
specification.

The `SimpleBrowser` class is configured with very simple options, so it does
not lead to ground-breaking results. However, now that you are familiar with
how to use Milliped `Browser` classes, we will have a look at how you can
create your own browser object that fits your specific use-case.
