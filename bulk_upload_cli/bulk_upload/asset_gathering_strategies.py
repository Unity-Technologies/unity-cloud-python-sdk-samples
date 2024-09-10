import os
import tarfile
import re
import shutil

from abc import ABC, abstractmethod
from glob import glob
from pathlib import PurePath, PurePosixPath
from bulk_upload.models import AssetInfo, FileInfo, ProjectUploaderConfig


def get_file_info(file: PurePath, root_folder: str) -> FileInfo:
    return FileInfo(file, PurePosixPath(file.relative_to(root_folder)))


def get_meta_file(file: PurePath, root_folder: str) -> FileInfo:
    return get_file_info(PurePath(f"{file}.meta"), root_folder)


def meta_file_exists(file: PurePath) -> bool:
    return os.path.exists(f"{file}.meta")


class AssetGatheringStrategy(ABC):
    @abstractmethod
    def get_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        pass

    @abstractmethod
    def clean_up(self):
        pass


class SingleFileUnityProjectStrategy(AssetGatheringStrategy):

    def get_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        files = []

        if len(config.file_extensions) == 0:
            # If no file extensions are provided, we will use all files in the assets folder
            files = [y for x in os.walk(config.assets_path) for y in glob(os.path.join(x[0], '*'))]
        else:
            for extension in config.file_extensions:
                files.extend([y for x in os.walk(config.assets_path) for y in
                              glob(os.path.join(x[0], f'*.{extension}'))])

        assets = dict()
        for f in files:
            if os.path.isdir(f):
                continue
            if f.endswith(".meta"):  # meta file should not be considered as an asset alone
                continue

            file_name = os.path.basename(f)
            assets[file_name] = AssetInfo(file_name)

            file = get_file_info(PurePath(f), config.assets_path)
            assets[file_name].files.append(file)

            if meta_file_exists(file.path):
                meta_file = get_meta_file(file.path, config.assets_path)
                assets[file_name].files.append(meta_file)
                dependencies = []
                with open(file.path, 'r') as file_readable:
                    dependencies = get_dependencies_from_file(file_readable)

                with open(meta_file.path, 'r') as meta_file_readable:
                    meta_file_content = meta_file_readable.read()
                    assets[file_name].unity_id = get_unity_id_from_meta_file(meta_file_content)
                    dependencies.extend(get_dependencies_from_string(meta_file_content))

                assets[file_name].dependencies.extend(list(set(dependencies)))

        return list(assets.values())

    def clean_up(self):
        remove_empty_file()


class NameGroupingStrategy(AssetGatheringStrategy):

    def get_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        files = []

        if len(config.file_extensions) == 0:
            # If no file extensions are provided, we will use all files in the assets folder
            files = [y for x in os.walk(config.assets_path) for y in glob(os.path.join(x[0], '*'))]
        else:
            for extension in config.file_extensions:
                files.extend([y for x in os.walk(config.assets_path) for y in
                              glob(os.path.join(x[0], f'*.{extension}'))])

        assets = dict()
        for f in files:
            if os.path.isdir(f):
                continue
            if f.endswith(".meta"):  # meta file should not be considered as an asset alone
                continue

            base_name = os.path.splitext(os.path.basename(f))[0]
            if not config.case_sensitive:
                base_name = base_name.lower()

            if base_name not in assets:
                assets[base_name] = AssetInfo(base_name)

            file = get_file_info(PurePath(f), config.assets_path)
            assets[base_name].files.append(file)
            if meta_file_exists(file.path):
                assets[base_name].files.append(get_meta_file(file.path, config.assets_path))

        for common_file in config.files_common_to_every_assets:
            common_file = PurePath(common_file)
            for asset in assets.values():
                asset.files.append(get_file_info(common_file, config.assets_path))
                if meta_file_exists(common_file):
                    asset.files.append(get_meta_file(common_file, config.assets_path))

        return list(assets.values())

    def clean_up(self):
        pass


class FolderGroupingStrategy(AssetGatheringStrategy):

    def get_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        folders = [x[0] for x in os.walk(config.assets_path) if x[0] != config.assets_path]

        if len(folders) == 0:
            print(f"No folders found in the assets path. Only the root folder will be considered as an asset")
            folders = [config.assets_path]

        assets = dict()
        for folder in folders:
            asset_name = PurePath(folder).name
            assets[asset_name] = AssetInfo(asset_name)

            if len(config.file_extensions) == 0:
                # If no file extensions are provided, we will use all files in the folder
                assets[asset_name].files = [get_file_info(PurePath(f), config.assets_path) for x in os.walk(folder) for f in glob(os.path.join(x[0], '*'))]
            else:
                for extension in config.file_extensions:
                    assets[asset_name].files.extend(
                        [get_file_info(PurePath(f), config.assets_path) for f in
                         glob(os.path.join(folder, f'*.{extension}'))])

                for asset in assets.values():
                    asset_files = asset.files.copy()
                    for file in asset_files:
                        if meta_file_exists(file.path) and get_meta_file(file.path, config.assets_path) not in asset.files:
                            asset.files.append(get_meta_file(file.path, config.assets_path))

        return list(assets.values())

    def clean_up(self):
        pass


class UnityPackageStrategy(AssetGatheringStrategy):

    def get_assets(self, config: ProjectUploaderConfig) -> [AssetInfo]:
        if config.assets_path == "":
            print("No unity package path provided. Please provide a unityPackagePath in the config file. Exiting...")
            return

        config.tags.append(PurePath(config.assets_path).name.replace(".unitypackage", ""))

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
                        dependencies = self.get_dependencies_from_tar_file(tar, asset_file_name)
                        dependencies.extend(self.get_dependencies_from_tar_file(tar, meta_file_name))

                        asset_path = self.get_path_from_pathname_file(tar, path_file)
                        asset = AssetInfo(asset_path.name)
                        asset.dependencies = list(set(dependencies))
                        asset_file = PurePath("tempo").joinpath(asset_file_name)
                        asset.files.append(FileInfo(asset_file, PurePosixPath(asset_path.__str__())))
                        meta_file = PurePath("tempo").joinpath(meta_file_name)
                        asset.files.append(FileInfo(meta_file, PurePosixPath(asset_path.__str__() + ".meta")))
                        asset.unity_id = PurePath(name).as_posix()

                        preview_file = name + "/preview.png"
                        if preview_file in tar_names:
                            tar.extract(preview_file, path="tempo")
                            asset.files.append(FileInfo(PurePosixPath(PurePath("tempo").joinpath(preview_file).__str__()),
                                                        PurePosixPath("preview.png")))
                            asset.preview_file = PurePosixPath("preview.png")

                        assets.append(asset)

        return assets

    def clean_up(self):
        shutil.rmtree("tempo")
        remove_empty_file()

    @staticmethod
    def get_dependencies_from_tar_file(tar, file) -> list:
        file = tar.extractfile(file)
        return get_dependencies_from_file(file)

    @staticmethod
    def get_path_from_pathname_file(tar, path_file):
        file = tar.extractfile(path_file)
        if file:
            return PurePath(file.read().decode('utf-8'))
        return None


def get_dependencies_from_file(file) -> list:
    try:
        file_content = file.read()
        # If the file is a string, we can directly use it, otherwise we need to decode it
        if isinstance(file_content, str):
            return get_dependencies_from_string(file_content)
        return get_dependencies_from_string(file_content.decode('utf-8'))
    except UnicodeDecodeError:
        pass  # Ignore non-UTF-8 encoded files, they do not contain dependency information
    return []


def get_dependencies_from_string(file_content: str) -> list:
    guid_regex = r"fileID:.*guid: ([a-f0-9]{32})"
    pattern = re.compile(guid_regex)
    return pattern.findall(file_content)


def get_unity_id_from_meta_file(meta_file_content) -> str:
    guid_regex = r"\nguid: ([a-f0-9]{32})"
    pattern = re.compile(guid_regex)
    return pattern.findall(meta_file_content)[0]


def get_empty_file() -> PurePath:
    if not os.path.exists("empty-file.template"):
        with open("empty-file.template", "w") as file:
            file.write("")
    return PurePath("empty-file.template")


def remove_empty_file():
    try:
        os.remove("empty-file.template")
    except FileNotFoundError:
        pass