import os
import random
import time

from urllib.parse import urljoin, urlparse

import requests

from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from requests.packages.urllib3.util.retry import Retry
from selenium import webdriver
from stem.util.log import get_logger as get_stem_logger

import milliped.constants as cst

from milliped.tor import TorSession
from milliped.utils import cut_url, get_logger, RobotParser, timeout

# silence Stem log messages
STEM_LOGGER = get_stem_logger()
STEM_LOGGER.propagate = False

LOGGER = get_logger(__name__)


class SimpleDownloadManager:
    """
    Simply uses the 'requests' Python library to download web pages.

    :param str base_url: URL of the website to browse.
    :param int max_retries: Maximum number of times a request for a web page
        is made before failing.
    :param float backoff_factor: Backoff factor for exponential decay.
    :param sequence retry_on: HTTP status code of responses that lead to a
        request retry.
    :param dict headers: Request headers.
    :param list proxies: List of proxies.
    :param float timeout: Timeout for requests.
    :param float request_delay: Time to wait between requests. This value
        will be searched in robots.txt but will default to the user-defined
        value.
    :param logging.Logger logger: Logger object.
    """
    def __init__(
        self,
        base_url,
        max_retries=cst.REQUEST_MAX_RETRIES,
        backoff_factor=cst.REQUEST_BACKOFF_FACTOR,
        retry_on=cst.REQUEST_RETRY_ON,
        headers=None,
        proxies=None,
        username=None,
        password=None,
        timeout=cst.REQUEST_TIMEOUT,
        request_delay=cst.REQUEST_DELAY,
        logger=LOGGER,
        ignore_robots_txt=False,
    ):
        self.base_url = base_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on = retry_on
        self.headers = headers
        if self.headers:
            self.user_agent = self.headers.get("User-Agent")
        else:
            self.user_agent = None
        self.proxies = proxies
        self.current_proxy = None
        if self.proxies:
            self.current_proxy = self.proxies.pop()
        self.auth = (username, password)
        self.timeout = timeout
        self.logger = logger
        self.get_session()

        self.robot_parser = RobotParser(self.base_url, self.user_agent)
        self.ignore_robots_txt = ignore_robots_txt
        self.request_delay = self.robot_parser.request_delay or request_delay

        self.logger.info("SimpleDownloadManager ready")
        self.logger.info(f"Using proxies: {self.current_proxy}")
        self.logger.info(f"Using headers: {self.headers}")

    def download(self, url):
        """
        Download a web page and return a tuple (status code, response content).

        If the request failed, the response text will be None. If the request
        was not sent, e.g. robots.txt indicates the page should not be
        accessed, the status code will be None.

        :param str url: URL of the page to download.
        :returns (tuple): 2-element tuple where the first element is the
            request status code (integer) and the second element is the
            response content (bytes).
        """
        if not url.startswith(self.base_url):
            url = urljoin(self.base_url, url)
        self.logger.info(f"Downloading {url}")

        if not self.ignore_robots_txt and not self.robot_parser.can_fetch(url):
            self.logger.info(f"Forbidden by robots.txt: {url}")
            return None, None

        try:
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.current_proxy,
                auth=self.auth,
                timeout=self.timeout,
            )
            self.logger.info("Download successful")
            return response.status_code, response.content

        except RequestException as e:
            self.logger.error(f"Failed to download {url}: {e}")
            if self.proxies:
                self.current_proxy = self.proxies.pop()
                self.logger.info(f"Now using proxies: {self.current_proxy}")
            return 500, None

    def get_session(self):
        """
        Create and configure a session object to make web requests.
        """
        session = requests.Session()

        retry = Retry(
            total=self.max_retries,
            read=self.max_retries,
            connect=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.retry_on,
        )

        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        self.session = session

    def sleep(self):
        """
        Pause the browser by the number of seconds defined in
        self.request_delay.
        """
        time.sleep(self.request_delay)


class TorDownloadManager:
    """
    Download web pages using Tor.

    :param str base_url: URL of the website to browse.
    :param int max_retries: Maximum number of times a request for a web page
        is made before failing.
    :param float backoff_factor: Backoff factor for exponential decay.
    :param sequence retry_on: HTTP status code of responses that lead to a
        request retry.
    :param dict headers: Request headers.
    :param list proxies: List of proxies.
    :param float timeout: Timeout for requests.
    :param float request_delay: Time to wait between requests. This value
        will be searched in robots.txt but will default to the user-defined
        value.
    :param str tor_password: Password for the Tor application.
    :param logging.Logger logger: Logger object.
    """
    def __init__(
        self,
        base_url,
        max_retries=cst.REQUEST_MAX_RETRIES,
        backoff_factor=cst.REQUEST_BACKOFF_FACTOR,
        retry_on=cst.REQUEST_RETRY_ON,
        headers=None,
        proxies=None,
        timeout=cst.REQUEST_TIMEOUT,
        request_delay=cst.REQUEST_DELAY,
        max_requests=cst.MAX_TOR_REQUESTS,
        tor_password=None,
        logger=LOGGER,
    ):
        self.base_url = base_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on = retry_on
        self.headers = headers
        if self.headers:
            self.user_agent = self.headers.get("User-Agent")
        else:
            self.user_agent = None
        self.proxies = proxies
        self.current_proxy = None
        if self.proxies:
            self.current_proxy = self.proxies.pop()
        self.timeout = timeout
        self.max_requests = max_requests
        self.tor_password = tor_password or os.getenv("TOR_PASSWORD")
        self.logger = logger
        self.session = self.get_session()

        self.robot_parser = RobotParser(self.base_url, self.user_agent)
        self.request_delay = request_delay or self.robot_parser.request_delay

        self.logger.info("TorDownloadManager ready")
        self.logger.info(f"Using proxies: {self.current_proxy}")
        self.logger.info(f"Using proxies: {self.headers}")

    def download(self, url):
        """
        Download a web page.

        :param str url: URL of the page to download.
        :returns (tuple): 2-element tuple where the first element is the
            request status code (integer) and the second element is the
            response content (bytes).
        """
        if self.max_requests != 0 and self.n_requests == self.max_requests:
            self.logger.info(
                "Reached max number of requests for single session, "
                "getting new session"
            )
            self.session = self.get_session()
        self.n_requests += 1

        if not url.startswith(self.base_url):
            url = urljoin(self.base_url, url)
        self.logger.info(f"Downloading {url}")

        if not self.robot_parser.can_fetch(url):
            self.logger.info("Forbidden by robots.txt: {url}")
            return None, None

        try:
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.current_proxy,
                timeout=self.timeout,
            )
            response.raise_for_status()
            self.logger.info("Download successful")
            return response.status_code, response.content

        except RequestException as e:
            self.logger.error(f"Failed to download {url}: {e}")
            if self.proxies:
                self.current_proxy = self.proxies.pop()
                self.logger.info(f"Now using proxies: {self.current_proxy}")
            return response.status_code, None

    def get_session(self):
        """
        Create and configure a session object to make web requests.
        """
        self.n_requests = 0
        # new IP only after reset_identity() is called and new session is made
        self.logger.info("Making a Tor session")
        session = TorSession(password=self.tor_password)
        session.reset_identity()
        session = TorSession(password=self.tor_password)
        self.logger.info("Made a Tor session")

        retry = Retry(
            total=self.max_retries,
            read=self.max_retries,
            connect=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.retry_on,
        )

        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def sleep(self):
        """
        Pause the browser by the number of seconds defined in
        self.request_delay.
        """
        time.sleep(self.request_delay)


class FirefoxDownloadManager:
    """
    Download web pages using the Python library selenium and the Firefox
    webdriver (geckodriver).

    :param str base_url: URL of the website to browse.
    :param int max_retries: Maximum number of times a request for a web page
        is made before failing.
    :param float wait_page_load: Number of seconds to wait for a page to load
        before downloading its contents.
    :param dict headers: Request headers.
    :param list proxies: List of proxies.
    :param str driver_path: Path to the Geckodriver executable.
    :param str log_path: Path of the file where to log activity.
    :param float request_delay: Time to wait between requests. This value
        will be searched in robots.txt but will default to the user-defined
        value.
    :param logging.Logger logger: Logger object.
    """
    def __init__(
        self,
        base_url,
        max_retries=cst.REQUEST_MAX_RETRIES,
        wait_page_load=cst.WAIT_PAGE_LOAD,
        headers=None,
        proxies=None,
        driver_path=None,
        options=cst.FIREFOX_OPTIONS,
        webdriver_log_path=cst.GECKODRIVER_LOG,
        request_delay=cst.REQUEST_DELAY,
        logger=LOGGER,
    ):
        self.base_url = base_url
        self.max_retries = max_retries
        self.wait_page_load = wait_page_load
        if headers:
            self.user_agent = headers.get("User-Agent")
        else:
            self.user_agent = None
        self.proxies = proxies
        self.current_proxy = {}
        if self.proxies:
            self.current_proxy = self.proxies.pop()
        self.driver_path = driver_path
        self.options = options
        self.webdriver_log_path = webdriver_log_path
        self.logger = logger
        self.session = self.get_session()

        self.robot_parser = RobotParser(self.base_url, self.user_agent)
        self.request_delay = request_delay or self.robot_parser.request_delay

        self.logger.info("FirefoxDownloadManager ready")
        self.logger.info(f"Using proxies: {self.current_proxy}")
        self.logger.info(f"Using user agent: {self.user_agent}")

    def close(self):
        self.session.close()

    @timeout(60)
    def _get_page_content(self, url):
        self.session.get(url)
        time.sleep(random.gauss(self.wait_page_load, self.wait_page_load / 6))
        return self.session.page_source

    def download(self, url):
        """
        Download a web page.

        :param str url: URL of the page to download.
        :returns (tuple): 2-element tuple where the first element is the
            request status code (integer) and the second element is the
            response content (bytes).
        """
        if not url.startswith(self.base_url):
            url = urljoin(self.base_url, url)
        self.logger.info(f"Downloading {url}")

        if not self.robot_parser.can_fetch(url):
            self.logger.info("Forbidden by robots.txt: {url}")
            return None, None

        for i in range(self.max_retries):
            try:
                content = self._get_page_content(url)
                self.logger.info("Download successful")
                return 200, content
            except Exception as e:
                self.logger.error(
                    f"{e}: retry {i+1}/{self.max_retries} downloading "
                    f"{cut_url(url)} failed"
                )
        self.logger.error(f"Too many retries downloading {url}")
        if self.proxies:
            self.current_proxy = self.proxies.pop()
            self.logger.info(f"Now using proxies: {self.current_proxy}")
        return None, None

    def get_session(self):
        """
        Create and configure a session object to make web requests.
        """
        https_proxy = urlparse(self.current_proxy.get("https")).netloc
        http_proxy = urlparse(self.current_proxy.get("http")).netloc
        if not http_proxy:
            http_proxy = https_proxy
        webdriver.DesiredCapabilities.FIREFOX["proxy"] = {
            "httpProxy": http_proxy,
            "sslProxy": https_proxy,
            "proxyType": "MANUAL",
        }
        options = webdriver.FirefoxOptions()
        for opt in self.options:
            options.add_argument(f"--{opt.lstrip('--')}")
        profile = webdriver.FirefoxProfile()
        if self.user_agent:
            profile.set_preference(
                "general.useragent.override",
                self.user_agent
            )
        session = webdriver.Firefox(
            executable_path=self.driver_path,
            options=options,
            firefox_profile=profile,
            log_path=self.webdriver_log_path,
        )
        if not self.user_agent:
            self.user_agent = session.execute_script(
                "return navigator.userAgent"
            )
        return session

    def sleep(self):
        """
        Pause the browser by the number of seconds defined in
        self.request_delay.
        """
        time.sleep(self.request_delay)
