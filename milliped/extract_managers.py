import csv
import json
import os

from pathlib import Path
from urllib.parse import quote_plus

import sqlalchemy

import milliped.constants as cst

from milliped.utils import get_logger

LOGGER = get_logger(__name__)


class CSVExtractStore:
    """
    Class to manage storage of data extracted from web pages as a CSV file.

    :param str file_path: Path of the CSV file where to store data.
    :param sequence columns: Sequence (tuple, etc.) of column names.
    :param str encoding: File encoding (optional, default utf-8).
    :param logging.Logger logger: Configured logger object.
    :param kwargs: Keyword arguments used to create a CSV dialect. See
        https://docs.python.org/3/library/csv.html#csv-fmt-params for the list
        of parameters.
    """
    def __init__(
        self,
        columns,
        file_path=cst.CSV_EXTRACT_PATH,
        encoding="utf-8",
        logger=LOGGER,
        **kwargs,
    ):
        self.file_path = file_path
        self.columns = columns
        self.encoding = encoding
        self.logger = logger
        self.kwargs = kwargs
        csv.register_dialect(
            "custom",
            delimiter=kwargs.get("delimiter", ","),
            doublequote=kwargs.get("doublequote", True),
            escapechar=kwargs.get("escapechar", None),
            lineterminator=kwargs.get("lineterminator", os.linesep),
            quotechar=kwargs.get("quotechar", '"'),
            quoting=kwargs.get("quoting", csv.QUOTE_MINIMAL),
            skipinitialspace=kwargs.get("skipinitialspace", False),
            strict=kwargs.get("strict", False),
        )
        if not Path(self.file_path).exists():
            with open(self.file_path, "w", encoding=self.encoding) as f:
                writer = csv.DictWriter(f, self.columns, **self.kwargs)
                writer.writeheader()

        self.logger.info("CSVExtractStore ready")

    def write(self, records):
        """
        Store one or more records in a CSV file. A single record should be
        passed as a dictionary where keys are column names. Several records
        should be passed as a sequence (e.g. list) of dictionaries.

        :param list|dict records: one or more records
        """
        inserted_rows = 0
        with open(self.file_path, "a", encoding=self.encoding) as f:
            writer = csv.DictWriter(f, self.columns, **self.kwargs)
            if isinstance(records, (list, tuple)):
                for r in records:
                    writer.writerow(r)
                    inserted_rows += 1
            elif isinstance(records, dict):
                writer.writerow(records)
                inserted_rows += 1
            else:
                raise ValueError(
                    "records should be a list, tuple, or dict, "
                    f"got: {type(records)}"
                )
        return inserted_rows


class DatabaseExtractStore:
    """
    Class to manage storage of data extracted from web pages as a relational
    database table.

    The database table where to store data should already exist before this
    class is used to store data.

    :param str database: Name of the database where the table is located.
    :param sqlalchemy.Table table_object: SQLAlchemy table object that defines
        the table name, column names, and column types.
    :param str engine: Database engine. Valid values include: postgresql,
        mysql, sqlite.
    :param str dialect: Name of the dialect to use with the engine, for
        example psycopg2 for PostgreSQL. The appropriate dialect libraries
        should be installed by the user.
    :param str host: URL of the database host (optional, default localhost).
    :param int port: Port on which the database process is listening to.
    :param str username: User name for database authentication.
    :param str password: Password for database authentication.
    :param logging.Logger logger: Configured logger object.
    :param kwargs: Keyword arguments to tweak the behavior of database
        connections. Supported parameters include 'pool_recycle', and
        'isolation_level'.
    """

    def __init__(
        self,
        database,
        table_object,
        engine,
        dialect=None,
        host="localhost",
        port=None,
        username=None,
        password=None,
        logger=LOGGER,
        **kwargs,
    ):
        if engine not in cst.DB_ENGINES:
            raise NotImplementedError(
                f"engine should be one of {cst.IMPLEMENTED_ENGINES}, "
                f"got: {engine}"
            )
        self.logger = logger
        self.engine = engine
        self.database = database
        self.table_object = table_object
        if self.engine == cst.SQLITE_ENGINE:
            self.url = f"sqlite:///{self.database}"
        else:
            self.dialect = dialect or cst.DB_DIALECTS[self.engine]
            self.host = host
            self.port = port or cst.DB_PORT[self.engine]
            self.username = username
            self.password = password
            self.kwargs = kwargs
            self.url = (
                f"{self.engine}+{self.dialect}://"
                f"{self.username}:{quote_plus(self.password)}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        self.engine = sqlalchemy.create_engine(
            self.url,
            pool_recycle=kwargs.get("pool_recycle", cst.POOL_RECYCLE),
            isolation_level=kwargs.get("isolation_level", cst.ISOLATION_LEVEL),
        )
        self.connection = self.engine.connect()

        self.logger.info("DatabaseExtractStore ready")

    def write(self, records):
        """
        Store one or more records in a table. A single record should be passed
        as a dictionary where keys are column names. Several records should
        be passed as a sequence (e.g. list) of dictionaries.

        :param list|dict records: one or more records
        """
        if not isinstance(records, (dict, list, tuple)):
            raise ValueError(
                "records should be a list, tuple, or dict, "
                f"got: {type(records)}"
            )
        if isinstance(records, dict):
            records = [records]
        result = self.connection.execute(self.table_object.insert(), records)
        return result.rowcount


class JSONLinesExtractStore:
    """
    Class to store data extracted from web pages as a JSONLines file.

    :param str file_path: Path of the file where to store data.
    :param str encoding: File encoding (optional, default utf-8).
    :param logging.Logger logger: Configure logger object.
    """
    def __init__(
        self,
        file_path=cst.JSON_EXTRACT_PATH,
        encoding="utf-8",
        logger=LOGGER,
    ):
        self.file_path = file_path
        self.encoding = encoding
        self.logger = logger

        self.logger.info("JSONLinesExtractStore ready")

    def write(self, records):
        """
        Store one or more records in a JsonLines file. A single record should
        be passed as a dictionary where keys are column names. Several records
        should be passed as a sequence (e.g. list) of dictionaries.

        :param list|dict records: one or more records
        """
        inserted_rows = 0
        with open(self.file_path, "a", encoding=self.encoding) as f:
            if isinstance(records, (list, tuple)):
                for r in records:
                    f.write(json.dumps(r) + os.linesep)
                    inserted_rows += 1
            elif isinstance(records, dict):
                f.write(json.dumps(records) + os.linesep)
                inserted_rows += 1
            else:
                raise ValueError(
                    "records should be a list, tuple, or dict, "
                    f"got: {type(records)}"
                )
        return inserted_rows
