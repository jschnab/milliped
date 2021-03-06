import logging
import os

from logging import handlers
from pathlib import Path

CONFIG_DIR = os.path.join(str(Path.home()), ".browsing")
DEFAULT_CONFIG = os.path.join(CONFIG_DIR, "browser.conf")
LOG_LEVEL = logging.INFO
LOG_HANDLERS = {
    "stream": logging.StreamHandler,
    "file": logging.FileHandler,
    "null": logging.NullHandler,
    "watchedfile": handlers.WatchedFileHandler,
    "baserotating": handlers.BaseRotatingHandler,
    "rotatingfile": handlers.RotatingFileHandler,
    "timedrotatingfile": handlers.TimedRotatingFileHandler,
    "socket": handlers.SocketHandler,
    "datagram": handlers.DatagramHandler,
    "syslog": handlers.SysLogHandler,
    "nteventlog": handlers.NTEventLogHandler,
    "smtp": handlers.SMTPHandler,
    "memory": handlers.MemoryHandler,
    "http": handlers.HTTPHandler,
    "queue": handlers.QueueHandler,
    "queuelistener": handlers.QueueListener,
}
LOG_CONFIG = {
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
HARVEST_FILE_REGEX = r"^harvest_[0-9]+\.bz2$"
FORBIDDEN = "forbidden"
NOT_FOUND = "not found"
ARCHIVE_PREFIX = "harvest_"
MAX_ARCHIVE_SIZE = 100 * 1000 * 1000  # 100 MB
PAUSE_BACKOFF = 0.3
PAUSE_MAX = 60 * 30  # 30 minutes
GECKODRIVER_LOG = os.path.join(CONFIG_DIR, "geckodriver.log")
REQUEST_MAX_RETRIES = 10
REQUEST_BACKOFF_FACTOR = 0.3
REQUEST_RETRY_ON = (500, 502, 503, 504)
REQUEST_TIMEOUT = 3
REQUEST_DELAY = 1
MAX_TOR_REQUESTS = 50
FIREFOX_OPTIONS = [
    "headless",
    "window-size=1420,1080",
    "disable-extensions",
    "disable-plugins-discovery",
]
WAIT_PAGE_LOAD = 20
CSV_EXTRACT_PATH = "extract.csv"
JSON_EXTRACT_PATH = "extract.jsonl"
QUEUE_NAME = "Queue"

# database constants
SQLITE_ENGINE = "sqlite"
POSTGRES_ENGINE = "postgresql"
POSTGRES_DIALECT = "psycopg2"
POSTGRES_PORT = 5432
MYSQL_ENGINE = "mysql"
MYSQL_DIALECT = "mysqldb"
MYSQL_PORT = 3306
DB_ENGINES = [SQLITE_ENGINE, POSTGRES_ENGINE, MYSQL_ENGINE]
DB_DIALECTS = {POSTGRES_ENGINE: POSTGRES_DIALECT, MYSQL_ENGINE: MYSQL_DIALECT}
DB_PORT = {POSTGRES_ENGINE: POSTGRES_PORT, MYSQL_ENGINE: MYSQL_PORT}
ISOLATION_LEVEL = "REPEATABLE READ"
POOL_RECYCLE = 3600
