import time

from functools import partial
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import milliped.constants as cst

from milliped.utils import get_all_links, get_logger, hash_string

LOGGER = get_logger(__file__)


class Browser:
    """
    Automated web browser.

    :param str base_url: URL of the website to browse.
    :param callable stop_test: Function to determine if we should stop
        browsing.
    :param callable get_browsable: Function which returns the URL
        of the next page to browse.
    :param callable get_harvestable: Function which returns the URL
        of the next page to harvest.
    :param callable get_page_id: Function which shortens the URL into a
        unique ID, this is used when saving harvested pages.
    :param class browse_queue: Object to store a queue of web pages to
        browse.
    :param class harvest_queue: Object to store a queue of web pages to
        parse.
    :param object download_manager: Object to manage downloading web pages.
    :param str html_parser: Parser to use with BeautifulSoup, e.g.
        'html.parser', 'lxml', etc.
    :param soup_parser: Function to use to parse the HTML tags soup into
        a dictionary.
    :param object harvest_store: Object to manage storage of downloaded
        web pages.
    :param object extract_store: Object to manage storage of extracted
        data from parsed web pages.
    :param logging.Logger logger: Configured logger object.
    """

    def __init__(
        self,
        base_url,
        stop_test=None,
        get_browsable=get_all_links,
        get_harvestable=get_all_links,
        get_page_id=hash_string,
        browse_queue=None,
        harvest_queue=None,
        download_manager=None,
        html_parser="html.parser",
        soup_parser=None,
        harvest_store=None,
        extract_store=None,
        logger=LOGGER,
    ):
        self.base_url = base_url
        self.stop_test = stop_test
        self.get_browsable = get_browsable
        self.get_harvestable = get_harvestable
        self.get_page_id = get_page_id
        self.soup_parser = soup_parser
        self.browse_queue = browse_queue
        self.harvest_queue = harvest_queue
        self.download_manager = download_manager
        self.harvest_store = harvest_store
        self.extract_store = extract_store
        self.logger = logger
        self.archive_count = 1
        self.pauses = 0

        if not html_parser:
            self.html_parser = partial(BeautifulSoup, features="html.parser")
        else:
            self.html_parser = partial(BeautifulSoup, features=html_parser)

        self.logger.info("Browser ready")

    def __repr__(self):
        return f"Browser(base_url={self.base_url})"

    def pause(self):
        """
        Pause browser if no message is returned from the queue.
        Pause times increase exponentially until a defined maximum is reached.
        """
        duration = min(
            cst.PAUSE_BACKOFF * 2 ** self.pauses,
            cst.PAUSE_MAX
        )
        time.sleep(duration)
        self.pauses += 1

    def retry_request(self, status_code):
        """
        Determines if a request should be retried based on its status code.

        If the status code is None, does not retry.

        :param int status_code: Request status code.
        :returns (bool): True if request should be retried, else False.
        """
        if status_code is not None:
            # 408 is "Read Timeout"
            # 429 is "Too Many Requests"
            if status_code >= 500 or status_code in (408, 429):
                return True
        return False

    def browse(self, initial=None):
        """
        Browse a website in a breadth-first search fashion, find pages to
        extract and store them in self.harvest_queue.

        :param str initial: URL where to start browsing (suffix to append
            to the base URL)
        """
        self.logger.info("Start browsing")
        if not initial:
            initial = self.base_url

        self.browse_queue.enqueue(initial)

        while not self.browse_queue.is_empty:
            current = self.browse_queue.dequeue()
            if not current:
                self.logger.info("Empty message received from queue, pausing")
                self.pause()
                continue

            self.pauses = 0

            status_code, content = self.download_manager.download(url=current)

            self.download_manager.sleep()

            # if page access is forbidden by robots.txt, continue
            if status_code is None:
                continue

            # if download failed, push URL back to queue
            if content is None:
                self.logger.info(
                    f"Failed to download {current} with status code "
                    f"{status_code}"
                )
                if self.retry_request(status_code):
                    self.browse_queue.re_enqueue(current)
                continue

            self.logger.info("Parsing HTML code")
            soup = self.html_parser(content)

            # get pages to harvest
            for child in self.get_harvestable(soup):
                # we join child with current to account for relative URLs
                self.harvest_queue.enqueue(urljoin(current, child))

            # check if we're at the last page
            # if yes return, else get next page to browse
            if self.stop_test and self.stop_test(soup):
                self.logger.info("Reached last page to browse, stopping")
                return

            # get pages to browse next
            for child in self.get_browsable(soup):
                # we join child with current to account for relative URLs
                self.browse_queue.enqueue(urljoin(current, child))

        self.logger.info("Finished browsing")

    def harvest(self):
        """
        Download the web pages stored in self.harvest_queue and save the data
        in the harvest store.
        """
        self.logger.info("Start harvesting")

        while not self.harvest_queue.is_empty:
            current = self.harvest_queue.dequeue()
            if not current:
                self.logger.info("Empty message received from queue, pausing")
                self.pause()
                continue

            self.pauses = 0

            status_code, content = self.download_manager.download(url=current)

            self.download_manager.sleep()

            # if page access is forbidden by robots.txt, continue
            if status_code is None:
                continue

            # if download failed, push URL back to queue
            if content is None:
                self.logger.info(
                    f"Failed to download {current} with status code "
                    f"{status_code}"
                )
                if self.retry_request(status_code):
                    self.browse_queue.re_enqueue(current)
                continue

            self.logger.info(f"Storing {current}")
            file_name = self.get_page_id(current)
            self.harvest_store.put(file_name, content)

        self.logger.info("Finished harvesting")

    def extract(self):
        """
        Extract data from HTML pages stored in the harvest store and save it
        with the extract store.
        """
        self.logger.info("Start extracting")

        while len(self.harvest_store) > 0:
            file_name, content = self.harvest_store.get()
            self.logger.info(f"Parsing {file_name}")
            soup = self.html_parser(content)
            parsed = self.soup_parser(soup)
            self.extract_store.write(parsed)

        self.logger.info("Finished extracting")
