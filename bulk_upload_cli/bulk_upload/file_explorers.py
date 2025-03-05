import os
import unity_cloud as uc

from abc import ABC, abstractmethod
from pathlib import PurePath
from glob import glob
from bulk_upload.models import ProjectUploaderConfig


class FileExplorer(ABC):
    @abstractmethod
    def list_files(self, path: str) -> [PurePath]:
        pass

    def get_folders_at_hierarchy_level(self, path, level: int) -> []:
        pass


class LocalFileExplorer(FileExplorer):
    def list_files(self, path) -> [PurePath]:
        os_files = [y for x in os.walk(path) for y in glob(os.path.join(x[0], '*'))]
        return [PurePath(file) for file in os_files]

    def get_folders_at_hierarchy_level(self, path, level: int) -> [str]:
        hierarchical_level = int(level) + path.count(os.sep)
        folders = [x[0] for x in os.walk(path) if x[0].count(os.sep) == hierarchical_level]
        return folders