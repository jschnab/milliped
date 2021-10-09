import milliped.constants as cst

from milliped.browser import Browser
from milliped.download_managers import SimpleDownloadManager
from milliped.extract_managers import JSONLinesExtractStore
from milliped.harvest_managers import ZipHarvestStore
from milliped.utils import (
    get_all_links,
    get_logger,
    hash_string,
    LocalExploredSet,
    LocalQueue,
    parse_soup,
)

LOGGER = get_logger(__name__, **cst.LOG_CONFIG)


class SimpleBrowser(Browser):
    def __init__(self, base_url):
        super().__init__(
            base_url=base_url,
            get_browsable=get_all_links,
            get_harvestable=get_all_links,
            get_page_id=hash_string,
            browse_set=LocalExploredSet(),
            browse_queue=LocalQueue(),
            harvest_set=LocalExploredSet(),
            harvest_queue=LocalQueue(),
            download_manager=SimpleDownloadManager(base_url, logger=LOGGER),
            soup_parser=parse_soup,
            harvest_store=ZipHarvestStore(logger=LOGGER),
            extract_store=JSONLinesExtractStore(logger=LOGGER),
            logger=LOGGER,
        )
