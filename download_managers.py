import logging
import os
import random
import time

import requests

from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from requests.packages.urllib3.util.retry import Retry
from selenium import webdriver
from stem.util.log import get_logger
from urllib.parse import urljoin, urlparse

import constants as cst

from tor import TorSession
from utils import cut_url, RobotParser, timeout

# silence stem log messages
stem_logger = get_logger()
stem_logger.propagate = False


class SimpleDownloadManager:
    """
    Simply uses the 'requests' Python library to download web pages.
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
        self.timeout = timeout
        self.session = self.get_session()

        self.robot_parser = RobotParser(self.base_url, self.user_agent)
        self.request_delay = request_delay or self.robot_parser.request_delay

        logging.info(f"using proxies: {self.proxies}")
        logging.info(f"using headers: {self.headers}")

    def download_page(self, url):
        if not url.startswith(self.base_url):
            url = urljoin(self.base_url, url)

        if not self.robot_parser.can_fetch(url):
            logging.info("forbidden to browse the current page")
            return cst.FORBIDDEN

        try:
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxies,
                timeout=self.timeout,
            )
            return response.content

        except RequestException:
            logging.error(f"failed to download {cut_url(url)}")

    def get_session(self):
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
        return session

    def sleep(self):
        time.sleep(self.request_delay)


class TorDownloadManager:
    """
    Download web pages using Tor.
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
        self.timeout = timeout
        self.max_requests = max_requests
        self.tor_password = tor_password or os.getenv("TOR_PASSWORD")
        self.session = self.get_session()

        self.robot_parser = RobotParser(self.base_url, self.user_agent)
        self.request_delay = request_delay or self.robot_parser.request_delay

        logging.info(f"using proxies: {self.proxies}")
        logging.info(f"using proxies: {self.headers}")

    def download_page(self, url):
        if self.max_requests != 0 and self.n_requests == self.max_requests:
            logging.info(
                "reached max number of requests for single session, "
                "getting new session"
            )
            self.session = self.get_session()
        self.n_requests += 1

        if not url.startswith(self.base_url):
            url = urljoin(self.base_url, url)

        if not self.robot_parser.can_fetch(url):
            logging.info("forbidden to browse the current page")
            return cst.FORBIDDEN

        try:
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxies,
                timeout=self.timeout,
            )
            return response.content

        except RequestException:
            logging.error(f"failed to download {cut_url(url)}")

    def get_session(self):
        self.n_requests = 0
        # new IP only after reset_identity() is called and new session is made
        logging.info("making a Tor session")
        session = TorSession(password=self.tor_password)
        session.reset_identity()
        session = TorSession(password=self.tor_password)
        logging.info("made a Tor session")

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
        time.sleep(self.request_delay)


class FirefoxDownloadManager:
    """
    Download web pages using the Python library selenium and the Firefox
    webdriver (geckodriver).
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
        log_path=cst.GECKODRIVER_LOG,
        request_delay=cst.REQUEST_DELAY,
    ):
        self.base_url = base_url
        self.max_retries = max_retries
        self.wait_page_load = wait_page_load
        if headers:
            self.user_agent = headers.get("User-Agent")
        else:
            self.user_agent = None
        self.proxies = proxies or {}
        self.driver_path = driver_path
        self.options = options
        self.log_path = log_path
        self.session = self.get_session()

        self.robot_parser = RobotParser(self.base_url, self.user_agent)
        self.request_delay = request_delay or self.robot_parser.request_delay

        logging.info(f"using proxies: {self.proxies}")
        logging.info(f"using user agent: {self.user_agent}")

    def close(self):
        self.session.close()

    @timeout(60)
    def _get_page_contents(self, url):
        self.session.get(url)
        time.sleep(random.gauss(self.wait_page_load, self.wait_page_load / 6))
        return self.session.page_source

    def download_page(self, url):
        if not url.startswith(self.base_url):
            url = urljoin(self.base_url, url)

        if not self.robot_parser.can_fetch(url):
            logging.info("forbidden to browse the current page")
            return cst.FORBIDDEN

        for i in range(self.max_retries):
            try:
                return self._get_page_contents(url)
            except Exception as e:
                logging.error(
                    f"{e}: retry {i+1}/{self.max_retries} downloading "
                    f"{cut_url(url)} failed"
                )
        logging.error(f"too many retries downloading {cut_url(url)}")

    def get_session(self):
        https_proxy = urlparse(self.proxies.get("https")).netloc
        http_proxy = urlparse(self.proxies.get("http")).netloc or https_proxy
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
            log_path=self.log_path,
        )
        if not self.user_agent:
            self.user_agent = session.execute_script(
                "return navigator.userAgent"
            )
        return session

    def sleep(self):
        time.sleep(self.request_delay)
