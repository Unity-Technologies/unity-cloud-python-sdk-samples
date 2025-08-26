import os
import unity_cloud as uc

from abc import ABC, abstractmethod
from pathlib import PurePath
from glob import glob
from bulk_upload.models import VcsInformation, ProjectUploaderConfig


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


class VcsFileExplorer(FileExplorer):

    def __init__(self, config: ProjectUploaderConfig):
        self.org_id = config.org_id
        self.vcs_id = config.vcs_integration.vcs_integration_id
        self.repository_name = config.vcs_integration.repository
        self.branch_name = config.vcs_integration.branch

    def list_files(self, path: str) -> [PurePath]:
        import unity_cloud.assets

        files = []
        if path == "/":
            path = ""
        branch_folders = uc.assets.list_branch_folders(self.org_id, self.vcs_id, self.repository_name, self.branch_name, path)
        for file in branch_folders:
            if file.type == "Directory":
                files.extend(self.list_files(f"{path}/{file.name}"))
            else:
                files.append(PurePath(f"{path}/{file.name}"))

        return files

    def get_folders_at_hierarchy_level(self, path, level: int, current_level: int = 0) -> []:
        import unity_cloud.assets

        files = []
        if path == "/":
            path = ""
        branch_folders = uc.assets.list_branch_folders(self.org_id, self.vcs_id, self.repository_name, self.branch_name, path)
        for file in branch_folders:
            if file.type == "Directory":
                if current_level == level:
                    files.append(f"{path}/{file.name}")
                else:
                    files.extend(self.get_folders_at_hierarchy_level(f"{path}/{file.name}", level, current_level + 1))
        return files