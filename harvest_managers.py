import glob
import os

from collections import deque
from zipfile import ZipFile, ZIP_BZIP2

import constants as cst


class ZipHarvestStore:
    """
    Stores harvested web pages as compressed bzip2 archives.
    Archive size is capped.
    This class writes and reads compressed web pages, but does not delete them.
    If files that match the archive name prefix exist in the harvest directory
    when this class is instantiated, they will be added to this store.
    """

    def __init__(
        self,
        harvest_dir,
        archive_prefix=cst.ARCHIVE_PREFIX,
        max_archive_size=cst.MAX_ARCHIVE_SIZE,
    ):
        self.harvest_dir = harvest_dir
        self.archive_prefix = archive_prefix
        self.max_archive_size = max_archive_size
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
