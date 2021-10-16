import milliped.constants as cst

from milliped.browser import Browser
from milliped.download_managers import SimpleDownloadManager
from milliped.extract_managers import JSONLinesExtractStore
from milliped.harvest_managers import ZipHarvestStore
from milliped.queues import LocalQueue
from milliped.utils import get_logger

LOGGER = get_logger(__name__, **cst.LOG_CONFIG)


def soup_parser(soup):
    """
    Get a map <link text> -> <link URL> from a BeautifulSoup object.

    :param bs4.BeautifulSoup soup: BeautifulSoup object.
    :returns (dict): Soup parsing results.
    """
    try:
        result = {
            "title": soup.find("h1").text,
            # remove Sterling pound sign
            "price": float(soup.find("p").text.replace("\u00a3", "")),
        }
        return result
    except Exception as e:
        LOGGER.info(e)
        pass
    return {}


class SimpleBrowser(Browser):
    def __init__(self, base_url, soup_parser):
        super().__init__(
            base_url=base_url,
            browse_queue=LocalQueue("Browse", logger=LOGGER),
            harvest_queue=LocalQueue("Harvest", logger=LOGGER),
            download_manager=SimpleDownloadManager(base_url, logger=LOGGER),
            soup_parser=soup_parser,
            harvest_store=ZipHarvestStore(logger=LOGGER),
            extract_store=JSONLinesExtractStore(logger=LOGGER),
            logger=LOGGER,
        )
