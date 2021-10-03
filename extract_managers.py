import csv
import json
import os

from pathlib import Path
from urllib.parse import quote_plus

import sqlalchemy

import constants as cst


class CSVExtractStore:
    def __init__(
        self,
        file_path,
        columns,
        encoding="utf-8",
        **kwargs,
    ):
        self.file_path = file_path
        self.columns = columns
        self.encoding = encoding
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
        table_schema=None,
        **kwargs,
    ):
        if engine not in cst.DB_ENGINES:
            raise NotImplementedError(
                f"engine should be one of {cst.IMPLEMENTED_ENGINES}, "
                f"got: {engine}"
            )
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


class JsonLinesExtractStore:
    def __init__(
        self,
        file_path,
        encoding="utf-8",
        **kwargs,
    ):
        self.file_path = file_path
        self.encoding = encoding
        self.kwargs = kwargs

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
