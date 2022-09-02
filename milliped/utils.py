import errno
import hashlib
import logging
import os
import signal

from functools import wraps
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import milliped.constants as cst


def check_status(response):
    """
    Check that HTTP status code of the response from a call to AWS is 200.

    :param dict response: Response to the AWS call.
    :raises ValueError: If response HTTP status code is not 200.
    """
    code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
    if code != 200:
        raise ValueError(f"Expected HTTP status code 200, got: {code}")


def cut_url(url):
    """
    If URL is longer than 50 characters, show the last 45.
    Useful for logging.

    :param str url: URL to shorten.
    :returns (str): Short URL.
    """
    if len(url) > 50:
        return f"...{url[-45:]}"
    return url


def get_all_links(url=None, soup=None):
    """
    Get all links from a BeautifulSoup object.

    :param str url: URL of the HTML page. This is currently ignored and only
        present to satisfy signature requirements for this type of function.
    :param bs4.BeautifulSoup soup: Soup to parse links from.
    :returns (list): List of links.
    """
    if soup is not None:
        return [
            link.attrs["href"] for link in soup.find_all("a", {"href": True})
        ]
    return []


def get_logger(name, level=cst.LOG_LEVEL, propagate=False, *args, **kwargs):
    """
    Get a logger object.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate
    for config in kwargs.get("handlers", []):
        handler = cst.LOG_HANDLERS[config["handler"]](
            **config["handler_kwargs"]
        )
        handler.setFormatter(logging.Formatter(config.get("format")))
        handler.setLevel(config.get("level", level))
        logger.addHandler(handler)
    return logger


def hash_string(s):
    """
    Hash a string using MD5.

    :param str s: String to Hash.
    :returns (str): MD5 hash of the input.
    """
    return hashlib.md5(s.encode()).hexdigest()


class RobotParser:
    """
    Class that reads and interprets the information in the file robots.txt.

    :param str base_url: Root URL of the website being crawled.
    :param str user_agent: User agent used during crawling.
    """

    def __init__(self, base_url, user_agent=None):
        self.base_url = base_url
        self.user_agent = user_agent or "*"
        self.parser = RobotFileParser()
        self.parser.set_url(urljoin(base_url, "robots.txt"))
        try:
            self.parser.read()
            if self.parser.crawl_delay(self.user_agent):
                self.request_delay = self.parser.crawl_delay(self.user_agent)
            else:
                self.request_delay = None
        except URLError:
            self.request_delay = 0
            self.parser = None

    def can_fetch(self, url):
        """
        Checks the robots.txt file if we can fetch the page.
        Always returns True if the website does not have a robots.txt file.

        :param str url: URL to check.
        :returns (bool): True if we can browse the page else False.
        """
        if not url.startswith(self.base_url):
            url = urljoin(self.base_url, url)
        if self.parser:
            return self.parser.can_fetch(self.user_agent, url)
        return True


class TimeoutError(Exception):
    pass


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator
