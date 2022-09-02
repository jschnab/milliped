import glob
import os

from collections import deque
from zipfile import ZipFile, ZIP_BZIP2

import boto3

import milliped.constants as cst
from milliped.utils import check_status, get_logger

LOGGER = get_logger(__name__)


class ZipHarvestStore:
    """
    Stores harvested web pages as compressed bzip2 archives.

    Archive size is capped.

    This class writes and reads compressed web pages, but does not delete them.

    If files that match the archive name prefix exist in the harvest directory
    when this class is instantiated, they will be added to this store.

    :param str harvest_dir: Directory where archive files are stored.
    :param str archive_prefix: Prefix for the archive file names (optional,
        default 'harvest_'.
    :param int max_archive_size: Maximum size in bytes for a single archive
        file (optional, default 100MB).
    :param logging.Logger logger: Configured logger object.
    """
    def __init__(
        self,
        harvest_dir=None,
        archive_prefix=cst.ARCHIVE_PREFIX,
        max_archive_size=cst.MAX_ARCHIVE_SIZE,
        logger=LOGGER,
    ):
        self.harvest_dir = harvest_dir or os.getcwd()
        self.archive_prefix = archive_prefix
        self.max_archive_size = max_archive_size
        self.logger = logger
        self.archive_count = 1
        self.file_names = deque()

        glob_path = os.path.join(
            self.harvest_dir,
            f"{self.archive_prefix}*.bz2"
        )
        for path in glob.glob(glob_path):
            with ZipFile(path, "r", compression=ZIP_BZIP2) as archive:
                for name in archive.namelist():
                    self.file_names.appendleft((path, name))
            self.archive_count += 1

    def __len__(self):
        return len(self.file_names)

    def _get_archive_name(self):
        """
        Returns the current archive's file name.

        Names are suffixed with '1' and increment when the archive size
        exceeds the maximum archive size.

        :returns (str): archive file name
        """
        archive_name = os.path.join(
            self.harvest_dir, f"{self.archive_prefix}{self.archive_count}.bz2"
        )
        while (
            os.path.exists(archive_name)
            and os.path.getsize(archive_name) > self.max_archive_size
        ):
            self.archive_count += 1
            archive_name = os.path.join(
                self.harvest_dir,
                f"{self.archive_prefix}{self.archive_count}.bz2"
            )
        archive_name = os.path.join(
            self.harvest_dir,
            f"{self.archive_prefix}{self.archive_count}.bz2"
        )
        return archive_name

    def put(self, file_name, data):
        """
        Compress and store the data as a file in the current archive.

        :param str file_name: name of the file that store the data in the
            archive
        :param str data: HTML text of a harvested web page
        """
        archive_name = self._get_archive_name()
        with ZipFile(archive_name, "a", compression=ZIP_BZIP2) as archive:
            archive.writestr(file_name, data)
        self.file_names.appendleft((archive_name, file_name))

    def get(self):
        """
        Decompress and return archived web page contents.

        :returns (str): archived web page contents
        """
        archive_path, file_name = self.file_names.pop()
        with ZipFile(archive_path, "r", compression=ZIP_BZIP2) as archive:
            data = archive.read(file_name).decode()
        return file_name, data


class S3FlatHarvestStore:

    def __init__(
        self, bucket,
        key_prefix,
        data_encoding=cst.DEFAULT_DATA_ENCODING,
        logger=LOGGER,
        aws_profile=None,
        aws_region=None,
    ):
        self.bucket = bucket
        self.key_prefix = key_prefix.strip("/")
        self.encoding = data_encoding
        self.logger = logger
        self.file_names = deque()
        self.s3_client = boto3.Session(
            profile_name=aws_profile, region_name=aws_region
        ).client("s3")

    def __len__(self):
        return len(self.file_names)

    def put(self, key, data):
        """
        Store an S3 object containing the data, under the specified key.

        :param str key: S3 object key. Will be prefixed by the key prefixed
            used when instantiating ``S3FlatHarvestStore``.
        :param str|bytes data: Data to store. Can be HTML text of a harvested
            web page or bytes of a data file.
        :returns: None
        """
        if isinstance(data, str):
            data = data.encode(encoding=self.encoding)
        check_status(
            self.s3_client.put_object(
                Bucket=self.bucket,
                Body=data,
                Key=f"{self.key_prefix}/{key.strip('/')}",
            )
        )
        self.file_names.appendleft(key)

    def get(self):
        """
        Downloads an object from S3 and returns its data.

        :returns (tuple): S3 object key (string) and object data (bytes).
        """
        key = self.file_names.pop()
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=f"{self.key_prefix}/{key}",
            )
            check_status(response)
            return key, response["Body"].read()
        except ValueError as e:
            self.logger.error(f"Failed to get key '{key}': {e}")
            self.file_names.appendleft(key)
            return None, None
