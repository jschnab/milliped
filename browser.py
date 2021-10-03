import logging
import time

from configparser import ConfigParser
from functools import partial
from pathlib import Path

from bs4 import BeautifulSoup

import constants as cst

from utils import cut_url


class Browser:
    def __init__(
        self,
        base_url,
        stop_test=None,
        get_browsable=None,
        get_harvestable=None,
        get_page_id=None,
        config_path=cst.DEFAULT_CONFIG,
        explored_set=None,
        browse_queue=None,
        harvest_queue=None,
        download_manager=None,
        html_parser="html.parser",
        soup_parser=None,
        harvest_store=None,
        extract_store=None,
    ):
        """
        Automated web browser.

        :param str base_url: URL where to start browsing
        :param callable stop_test: function to determine if we should stop
            browsing
        :param callable get_browsable: function which returns the URL
            of the next page to browse
        :param callable get_harvestable: function which returns the URL
            of the next page to harvest
        :param callable get_page_id: function which shortens the URL into a
            unique ID
        :param str html_parser: parser to use with BeautifulSoup, e.g.
            'html.parser', 'lxml', etc
        :param soup_parser: function to use to parse the HTML tags soup into
            a dictionary
        :param str config_path: path to the browser configuration file
        :param class explored_set: Object to store a set of explored web pages.
            Must have methods named 'add' and '__contains__'.
        :param class browse_queue: Object to store a queue of web pages to
            browse. This must have methods named 'enqueue' and 'dequeue'.
        :param class parse_queue: Object to store a queue of web pages to
            parse. This must have methods named 'enqueue' and 'dequeue'.
        :param object download_manager: Object to manage downloading web pages.
        :param object harvest_store: Object to manage storage of downloaded
            web pages.
        :param object extract_store: Object to manage storage of extracted
            data from parsed web pages.
        """
        self.configure(config_path)
        self.base_url = base_url
        self.stop_test = stop_test
        self.get_browsable = get_browsable
        self.get_harvestable = get_harvestable
        self.get_page_id = get_page_id
        self.soup_parser = soup_parser
        self.explored_set = explored_set
        self.browse_queue = browse_queue
        self.harvest_queue = harvest_queue
        self.download_manager = download_manager
        self.harvest_store = harvest_store
        self.extract_store = extract_store
        self.archive_count = 1
        self.pauses = 0

        if not html_parser:
            self.html_parser = partial(BeautifulSoup, features="html.parser")
        else:
            self.html_parser = partial(BeautifulSoup, features=html_parser)

    def configure(self, config_path):
        """
        Read and apply the configuration.

        :param str config_path: path to the configuration file
        """
        if Path(config_path).exists():
            config = ConfigParser()
            config.read(config_path)
            log_file = config["logging"]["log_file"]
        else:
            log_file = "browser.log"

        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(message)s",
            level=logging.INFO,
            filename=log_file,
            filemode="a"
        )

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

    def browse(self, initial=None):
        """
        Crawl the web in a breadth-first search fashion, find pages to extract
        and store them in self.harvest_queue.

        :param str initial: URL where to start browsing (suffix to append
            to the base URL)
        """
        logging.info("start browsing")
        if not initial:
            initial = self.base_url

        if initial not in self.explored_set:
            self.browse_queue.enqueue(initial)
            self.explored_set.add(initial)

        while not self.browse_queue.is_empty:
            current = self.browse_queue.dequeue()
            if not current:
                logging.info("empty message received from queue, pausing")
                self.pause()
                continue

            self.pauses = 0

            logging.info(f"downloading {cut_url(current)}")
            content = self.download_manager.download_page(url=current)

            self.download_manager.sleep()

            # if download failed, push URL back to queue
            if content is None:
                self.browse_queue.enqueue(current)
                continue

            # if download is forbidden, skip
            if content == cst.FORBIDDEN:
                continue

            logging.info("parsing HTML code")
            soup = self.html_parser(content)

            # get list of web links to harvest
            for child in self.get_harvestable(soup):
                if child in self.explored_set:
                    continue
                logging.info(f"found to harvest {cut_url(child)}")
                self.explored_set.add(child)
                self.harvest_queue.enqueue(child)

            # check if we're at the last page
            # if yes return, else get next page of listings
            if self.stop_test(soup):
                logging.info("reached last page to browse, stopping")
                return

            for child in self.get_browsable(soup):
                if child in self.explored_set:
                    continue
                logging.info(f"found to browse next {cut_url(child)}")
                self.explored_set.add(child)
                self.browse_queue.enqueue(child)

    def harvest(self):
        """
        Download the web pages stored in self.harvest_queue and save the data.
        """
        logging.info("start harvesting")

        while not self.harvest_queue.is_empty:
            current = self.harvest_queue.dequeue()
            if not current:
                logging.info("empty message received from queue, pausing")
                self.pause()
                continue

            self.pauses = 0

            logging.info(f"downloading {cut_url(current)}")
            content = self.download_manager.download_page(url=current)

            self.download_manager.sleep()

            # if download failed, push URL back to queue
            if content is None:
                self.harvest_queue.enqueue(current)
                continue

            # if download is forbidden, skip
            if content == cst.FORBIDDEN:
                continue

            logging.info(f"storing {cut_url(current)}")
            file_name = self.get_page_id(current)
            self.harvest_store.put(file_name, content)

        logging.info("finished harvesting")

    def extract(self):
        """
        Extract data from HTML pages stored in an archive and saves it as a
        CSV file.
        """
        logging.info("start extracting")

        while len(self.harvest_store) > 0:
            file_name, content = self.harvest_store.get()
            logging.info(f"parsing {file_name}")
            soup = self.html_parser(content)
            parsed = self.soup_parser(soup)
            inserted_rows = self.extract_store.write(parsed)
            logging.info(f"inserted {inserted_rows}")

        logging.info("finished extracting")
