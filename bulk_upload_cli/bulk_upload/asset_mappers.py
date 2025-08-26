import os
import tarfile
import re
import shutil
import csv
import unity_cloud as uc

from abc import ABC, abstractmethod
from pathlib import PurePath, PurePosixPath, Path
from bulk_upload.models import AssetInfo, FileInfo, ProjectUploaderConfig, Strategy, Metadata
from bulk_upload.file_explorers import FileExplorer


def is_directory_path(file_path) -> bool:
    return len(file_path.name.split("/")[-1].split(".")) == 1


class AssetMapper(ABC):
    @abstractmethod
    def map_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        pass

    @abstractmethod
    def clean_up(self):
        pass


class UnityProjectAssetMapper(AssetMapper):

    def __init__(self, file_explorer: FileExplorer):
        self.file_explorer = file_explorer

    def map_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        files = self.file_explorer.list_files(config.assets_path)
        # remove files with excluded extensions
        files = [f for f in files if not any(f.suffix.endswith(ext) for ext in config.excluded_file_extensions)]

        assets = dict()
        for f in files:
            if self.is_directory_path(f):
                continue
            if f.name.endswith(".meta"):  # meta file should not be considered as an asset alone
                continue

            file_name = os.path.basename(f)
            assets[file_name] = AssetInfo(file_name)

            file = get_file_info(PurePath(f), config.assets_path)
            assets[file_name].files.append(file)

            if meta_file_exists(file.path, files):
                meta_file = get_meta_file(file.path, config.assets_path)
                assets[file_name].files.append(meta_file)
                dependencies = []
                with open(file.path, 'r') as file_readable:
                    dependencies = get_dependencies_from_file(file_readable)

                with open(meta_file.path, 'r') as meta_file_readable:
                    meta_file_content = meta_file_readable.read()
                    assets[file_name].unity_id = get_unity_id_from_meta_file(meta_file_content)
                    dependencies.extend(get_dependencies_from_string(meta_file_content))

                assets[file_name].unresolved_dependencies = list(set(dependencies))

        return list(assets.values())

    def clean_up(self):
        print("No clean up needed")

    @staticmethod
    def is_directory_path(file_path) -> bool:
        return len(file_path.name.split("/")[-1].split(".")) == 1


class NameGroupingAssetMapper(AssetMapper):

    def __init__(self, file_explorer: FileExplorer):
        self.file_explorer = file_explorer

    def map_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        files = self.file_explorer.list_files(config.assets_path)
        # remove files with excluded extensions
        files = [f for f in files if not any(f.endswith(ext) for ext in config.excluded_file_extensions)]

        assets = dict()
        for f in files:
            if is_directory_path(f):
                continue

            if f.name.endswith(".meta"):  # meta file should not be considered as an asset alone
                continue

            base_name = os.path.splitext(os.path.basename(f))[0]
            if not config.case_sensitive:
                base_name = base_name.lower()

            if base_name not in assets:
                assets[base_name] = AssetInfo(base_name)

            file = get_file_info(PurePath(f), config.assets_path)
            assets[base_name].files.append(file)

        for common_file in config.files_common_to_every_assets:
            common_file = PurePath(common_file)
            for asset in assets.values():
                asset.files.append(get_file_info(common_file, config.assets_path))

        return list(assets.values())

    def clean_up(self):
        print("No clean up needed")


class FolderGroupingAssetMapper(AssetMapper):

    def __init__(self, file_explorer: FileExplorer):
        self.file_explorer = file_explorer

    def map_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:

        abs_path = os.path.abspath(config.assets_path) if config.vcs_integration is None else config.assets_path
        folders = self.file_explorer.get_folders_at_hierarchy_level(abs_path, int(config.hierarchical_level))

        if len(folders) == 0:
            print(f"No folders found in the assets path. Only the root folder will be considered as an asset")
            folders = [config.assets_path]

        assets = dict()
        for folder in folders:
            asset_name = PurePath(folder).name
            assets[asset_name] = AssetInfo(asset_name)

            files = self.file_explorer.list_files(folder)
            # remove files with excluded extensions
            files = [f for f in files if not any(f.suffix.endswith(ext) for ext in config.excluded_file_extensions)]
            assets[asset_name].files = [get_file_info(f, abs_path) for f in files]

        for asset in assets.values():
            # detect preview files with extension as png
            asset_files = asset.files.copy()
            for file in asset_files:
                if is_directory_path(file.path):
                    asset.files.remove(file)

                if config.preview_detection and self.is_preview_file(file.path):
                    asset.preview_files.append(get_file_info(file.path, abs_path))
                    asset.files.remove(file)

        return list(assets.values())

    @staticmethod
    def is_preview_file(file_path) -> bool:
        file_suffix = file_path.suffix.lower()
        is_picture_file = file_suffix in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]

        file_stem = file_path.stem.lower()
        file_name_is_preview = file_stem in ["preview", "previews", "thumbnail", "thumbnails"]

        file_parent_folder = file_path.parent.name.lower()
        parent_folder_is_preview = file_parent_folder in ["preview", "previews", "thumbnail", "thumbnails"]

        return is_picture_file and file_name_is_preview or is_picture_file and parent_folder_is_preview

    def clean_up(self):
        print("No clean up needed")


class UnityPackageAssetMapper(AssetMapper):

    def map_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        if config.assets_path == "":
            print("No unity package path provided. Please provide a unityPackagePath in the config file. Exiting...")
            return

        assets = []
        os.makedirs("tempo", exist_ok=True)
        with tarfile.open(config.assets_path, 'r:gz') as tar:
            tar_names = tar.getnames()
            for name in tar_names:
                member = tar.getmember(name)
                if member.isdir():
                    asset_file_name = name + "/asset"
                    meta_file_name = name + "/asset.meta"
                    path_file = name + "/pathname"
                    if asset_file_name in tar_names and meta_file_name in tar_names and path_file in tar_names:
                        tar.extract(asset_file_name, path="tempo")
                        tar.extract(meta_file_name, path="tempo")

                        asset_path = self.get_path_from_pathname_file(tar, path_file)
                        asset = AssetInfo(asset_path.name)
                        asset_file = PurePath("tempo").joinpath(asset_file_name)
                        asset.files.append(FileInfo(asset_file, PurePosixPath(asset_path.as_posix())))
                        meta_file = PurePath("tempo").joinpath(meta_file_name)
                        asset.files.append(FileInfo(meta_file, PurePosixPath(asset_path.as_posix().__str__() + ".meta")))
                        asset.unity_id = PurePath(name).as_posix()

                        # Get dependencies
                        dependencies = []
                        for file_info in asset.files:
                            file_path = Path(file_info.path)
                            with open(file_path, 'r') as file:
                                dependencies.extend(get_dependencies_from_file(file))

                        asset.unresolved_dependencies = list(set(dependencies))

                        preview_file = name + "/preview.png"
                        if preview_file in tar_names:
                            tar.extract(preview_file, path="tempo")
                            asset.preview_files = [FileInfo(PurePosixPath(PurePath("tempo").joinpath(preview_file).__str__()),
                                                           PurePosixPath("preview.png"))]

                        assets.append(asset)

        return assets

    def clean_up(self):
        shutil.rmtree("tempo")
        print("Extracted files have been deleted")


    @staticmethod
    def get_path_from_pathname_file(tar, path_file):
        file = tar.extractfile(path_file)
        if file:
            #read only the first line of the path file
            return PurePath(file.read().decode('utf-8').split("\n")[0])
        return None


class SingleFileAssetMapper(AssetMapper):

    def __init__(self, file_explorer: FileExplorer):
        self.file_explorer = file_explorer

    def clean_up(self):
        print("No clean up needed")

    def map_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        files = self.file_explorer.list_files(config.assets_path)
        # remove files with excluded extensions
        files = [f for f in files if not any(f.suffix.endswith(ext) for ext in config.excluded_file_extensions)]

        assets = []

        potential_previews = {}
        if config.preview_detection:
            for file in files:
                if self.is_directory_path(file):
                    continue

                if self.is_preview_file(file):
                    file_stem = self.remove_preview_suffix(file)
                    potential_previews[file_stem] = FileInfo(file, PurePosixPath(file.relative_to(config.assets_path)))

        for file in files:
            if self.is_directory_path(file):
                continue

            if file in potential_previews.values():
                continue

            asset = AssetInfo(os.path.basename(file))
            asset.files.append(FileInfo(file, PurePosixPath(file.relative_to(config.assets_path))))

            if file.stem.lower() in potential_previews:
                preview_file = potential_previews[file.stem.lower()]
                asset.preview_files.append(preview_file)
                del potential_previews[file.stem.lower()]

            assets.append(asset)

        # Add the remaining preview files as assets
        for preview_file in potential_previews.values():
            asset = AssetInfo(preview_file.path.stem + "_preview")
            asset.preview_files.append(preview_file)
            assets.append(asset)

        return assets

    @staticmethod
    def is_preview_file(file_path) -> bool:
        file_suffix = file_path.suffix.lower()
        is_picture_file = file_suffix in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]

        file_stem = file_path.stem.lower()
        file_name_is_preview = file_stem in ["preview", "previews", "thumbnail", "thumbnails"]

        file_parent_folder = file_path.parent.name.lower()
        parent_folder_is_preview = file_parent_folder in ["preview", "previews", "thumbnail", "thumbnails"]

        return is_picture_file and file_name_is_preview or is_picture_file and parent_folder_is_preview

    @staticmethod
    def is_directory_path(file_path) -> bool:
        return len(file_path.name.split("/")[-1].split(".")) == 1

    @staticmethod
    def remove_preview_suffix(file_path) -> str:
        file_stem = file_path.stem.lower()

        for suffix in ["preview", "previews", "thumbnail", "thumbnails"]:
            if file_stem.endswith(suffix):
                new_stem = file_stem.replace(suffix, "")
                break

        return file_stem


class CsvAssetMapper(AssetMapper):

    def __init__(self):
        self.sub_strategy = None

    def clean_up(self):
        if self.sub_strategy == "unityPackage":
            shutil.rmtree("tempo")
            print("Extracted files have been deleted")
        else:
            print("No clean up needed")

    def map_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        assets = []
        with open(config.assets_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            input_row = next(reader)

            inputs = input_row.get("Input").split("?")
            if len(inputs) == 2:
                self.sub_strategy = Strategy(inputs[0])
                sub_path = inputs[1]
                if self.sub_strategy == Strategy.UNITY_PACKAGE:
                    self.extract_unity_package(sub_path)
                elif self.sub_strategy == Strategy.CLOUD_ASSET:
                    config.update_files = False

            for row in reader:
                asset = AssetInfo(row.get("Name"))
                asset.from_csv(row)
                assets.append(asset)

        return assets

    @staticmethod
    def extract_unity_package(unity_package_path):

        os.makedirs("tempo", exist_ok=True)
        with tarfile.open(unity_package_path, 'r:gz') as tar:
            tar_names = tar.getnames()
            for name in tar_names:
                member = tar.getmember(name)
                if member.isdir():
                    asset_file_name = name + "/asset"
                    meta_file_name = name + "/asset.meta"
                    path_file = name + "/pathname"
                    if asset_file_name in tar_names and meta_file_name in tar_names and path_file in tar_names:
                        tar.extract(asset_file_name, path="tempo")
                        tar.extract(meta_file_name, path="tempo")

                        preview_file = name + "/preview.png"
                        if preview_file in tar_names:
                            tar.extract(preview_file, path="tempo")


class CloudAssetMapper(AssetMapper):

    def map_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        print("Fetching assets from Unity Cloud...")
        cloud_assets = uc.assets.get_asset_list(config.org_id, config.project_id)
        asset_infos = []
        for ca in cloud_assets:
            asset_info = AssetInfo(ca.name)
            asset_info.am_id = ca.id
            asset_info.version = ca.version
            asset_info.already_in_cloud = True
            asset_info.is_frozen_in_cloud = ca.is_frozen
            asset_info.customization.tags = ca.tags

            asset_metadata = uc.assets.get_asset_metadata(config.org_id, config.project_id, ca.id, ca.version)
            for metadata_key, metadata_value in asset_metadata.items():
                asset_info_metadata = Metadata()
                asset_info_metadata.field_definition = metadata_key
                asset_info_metadata.field_value = metadata_value
                asset_info.customization.metadata.append(asset_info_metadata)

            asset_infos.append(asset_info)

        print(f"Found {len(asset_infos)} assets in your project")

        return asset_infos

    def clean_up(self):
        print("No clean up needed")


def get_unity_id_from_meta_file(meta_file_content) -> str:
    guid_regex = r"\nguid: ([a-f0-9]{32})"
    pattern = re.compile(guid_regex)
    return pattern.findall(meta_file_content)[0]


def get_file_info(file: PurePath, root_folder: str) -> FileInfo:
    return FileInfo(file, PurePosixPath(file.relative_to(root_folder)))


def get_meta_file(file: PurePath, root_folder: str) -> FileInfo:
    return get_file_info(PurePath(f"{file}.meta"), root_folder)


def meta_file_exists(file: PurePath, files) -> bool:
    meta_file_path = PurePath(f"{file}.meta")
    return meta_file_path in files

def get_dependencies_from_file(file) -> []:
    try:
        file_content = file.read()
        # If the file is a string, we can directly use it, otherwise we need to decode it
        if isinstance(file_content, str):
            return get_dependencies_from_string(file_content)
        return get_dependencies_from_string(file_content.decode('utf-8'))
    except UnicodeDecodeError:
        pass  # Ignore non-UTF-8 encoded files, they do not contain dependency information
    return []


def get_dependencies_from_string(file_content: str) -> []:
    guid_regex = r"fileID:.*guid: ([a-f0-9]{32})"
    pattern = re.compile(guid_regex)
    return pattern.findall(file_content)