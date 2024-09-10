import json
import os

import unity_cloud as uc
from bulk_upload.models import ProjectUploaderConfig, Strategy, FileInfo, AssetInfo
from bulk_upload.asset_gathering_strategies import *
from concurrent.futures import ThreadPoolExecutor, wait
from unity_cloud.models import *
from pathlib import PurePath, PurePosixPath


def login_with_user_account():
    uc.identity.user_login.use()
    auth_state = uc.identity.user_login.get_authentication_state()
    if auth_state != uc.identity.user_login.Authentication_State.LOGGED_IN:
        uc.identity.user_login.login()


class ProjectUploader:

    def __init__(self):
        self.config = None
        self.futures = list()

    @staticmethod
    def login(key_id=None, key=None):
        uc.initialize()

        if key is not None and key_id != "" and key_id is not None and key != "":
            uc.identity.service_account.use(key_id, key)
        else:
            print("Logging in with user account in progress", flush=True)
            login_with_user_account()

    @staticmethod
    def get_collections(org_id: str, project_id: str):
        collections = uc.assets.list_collections(org_id, project_id)
        return [collection.name for collection in collections]

    def run(self, config: ProjectUploaderConfig, skip_login=False):
        self.config = config

        if not skip_login:
            self.login(config.key_id, config.key)

        self.validate_config()

        strategy = None
        if self.config.strategy == Strategy.NAME_GROUPING:
            strategy = NameGroupingStrategy()
        elif self.config.strategy == Strategy.FOLDER_GROUPING:
            strategy = FolderGroupingStrategy()
        elif self.config.strategy == Strategy.UNITY_PACKAGE:
            strategy = UnityPackageStrategy()
        elif self.config.strategy == Strategy.SINGLE_FILE_ASSET:
            strategy = SingleFileUnityProjectStrategy()

        print("Gathering assets", flush=True)

        project_assets = uc.assets.get_asset_list(self.config.org_id, self.config.project_id)

        assets = strategy.get_assets(self.config)
        if assets is None:
            return

        for asset in assets:
            for project_asset in project_assets:
                if asset.name == project_asset.name or (asset.name.lower() == project_asset.name.lower() and not self.config.case_sensitive):
                    asset.am_id = project_asset.id
                    asset.version = project_asset.version
                    asset.already_in_cloud = True
                    asset.is_frozen_in_cloud = project_asset.is_frozen
                    break

        with ThreadPoolExecutor(max_workers=self.config.amount_of_parallel_uploads) as executor:
            for asset in assets:
                if asset.am_id is None:
                    self.futures.append(executor.submit(self.create_asset, asset))
                elif asset.is_frozen_in_cloud:
                    self.futures.append(executor.submit(self.create_new_version, asset))

        wait(self.futures)
        self.futures = list()

        print("Setting asset dependencies", flush=True)
        with ThreadPoolExecutor(max_workers=self.config.amount_of_parallel_uploads) as executor:
            for asset in assets:
                self.futures.append(executor.submit(self.set_asset_references, asset, assets))

        wait(self.futures)
        self.futures = list()

        with ThreadPoolExecutor(max_workers=self.config.amount_of_parallel_uploads) as executor:
            for asset in assets:
                if not asset.already_in_cloud or self.config.update_files:
                    self.futures.append(executor.submit(self.upload_asset_files, asset))
                else:
                    print(f"Skipping file upload for asset: {asset.name} because updateFiles is set to False", flush=True)

        wait(self.futures)
        self.futures = list()

        print("Setting tags and collections for assets", flush=True)
        with ThreadPoolExecutor(max_workers=self.config.amount_of_parallel_uploads) as executor:
            for asset in assets:
                self.futures.append(executor.submit(self.set_metadata_and_collection, asset))

        wait(self.futures)

        strategy.clean_up()
        print("Done uploading assets")

    def validate_config(self):
        print("Validating configuration..", flush=True)
        metadata_keys = uc.assets.list_field_definitions(self.config.org_id, self.config.project_id)
        for key in self.config.metadata.keys():
            if key not in metadata_keys:
                print("Key: " + key + " is not a valid metadata key. It will be ignored.")
                self.config.metadata.pop(key)

    def create_asset(self, asset: AssetInfo):
        try:
            print(f"Creating asset: {asset.name} in cloud", flush=True)
            asset_creation = AssetCreation(name=asset.name, type= AssetType.OTHER if len(asset.files) == 0 else self.get_asset_type(asset.files[0].cloud_path))
            created_asset = uc.assets.create_asset(asset_creation, self.config.org_id, self.config.project_id)
            asset.am_id = created_asset.id
            asset.version = created_asset.version

        except Exception as e:
            print(f'Failed to create asset: {asset.name}', flush=True)
            print(e, flush=True)

    def create_new_version(self, asset: AssetInfo):
        try:
            print(f"Creating new version for asset: {asset.name}", flush=True)
            new_version = uc.assets.create_unfrozen_asset_version(self.config.org_id, self.config.project_id, asset.am_id, asset.version)
            asset.version = new_version.version
        except Exception as e:
            print(f'Failed to create new version for asset: {asset.name}', flush=True)
            print(e, flush=True)

    def upload_asset_files(self, asset: AssetInfo):
        try:

            dataset_id = uc.assets.get_dataset_list(self.config.org_id, self.config.project_id, asset.am_id, asset.version)[0].id

            if self.config.update_files:
                self.delete_existing_files(asset, dataset_id)

            print(f"Uploading files for asset: {asset.name}", flush=True)
            files_upload_futures = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                for file in asset.files:
                    files_upload_futures.append(executor.submit(self.upload_file, asset, dataset_id, file))

            wait(files_upload_futures)

        except Exception as e:
            print(f'Failed to upload files for asset: {asset.name}', flush=True)
            print(e, flush=True)

    def delete_existing_files(self, asset: AssetInfo, dataset_id: str):
        file_list = uc.assets.get_file_list(self.config.org_id, self.config.project_id, asset.am_id, asset.version, dataset_id)
        for file in file_list:
            uc.assets.remove_file(self.config.org_id, self.config.project_id, asset.am_id, asset.version, dataset_id, file.path)

    def upload_file(self, asset: AssetInfo, dataset_id: str, file: FileInfo):
        try:
            if not self.config.update_files:
                file_in_cloud = None
                try:
                    file_in_cloud = uc.assets.get_file(self.config.org_id, self.config.project_id, asset.am_id,
                                                   asset.version, dataset_id, file.cloud_path)
                except Exception:
                    # do nothing file was not found, this is expected
                    pass

                if file_in_cloud is not None:
                    print(f"File already in cloud: {file.cloud_path}", flush=True)
                    return

            file_upload = FileUploadInformation(organization_id=self.config.org_id, project_id=self.config.project_id,
                                                asset_id=asset.am_id, asset_version=asset.version, dataset_id=dataset_id,
                                                upload_file_path=file.path, cloud_file_path=file.cloud_path)
            uc.assets.upload_file(file_upload, disable_automatic_transformations=True)

        except Exception as e:
            print(f'Failed to upload file: {file.path}', flush=True)
            print(e, flush=True)

    def set_asset_references(self, asset: AssetInfo, assets: [AssetInfo]):
        try:
            for dependency in asset.dependencies:
                for a in assets:
                    if a.unity_id == dependency:
                        uc.assets.add_asset_reference(self.config.org_id, self.config.project_id, asset.am_id, asset.version, target_asset_id=a.am_id, target_asset_version=a.version)
                        asset.files.append(
                            FileInfo(get_empty_file(), PurePosixPath(f"{a.am_id}_{a.version}.am4u_dep")))
                        break

        except Exception as e:
            print(f'Failed to set references for asset: {asset.name}', flush=True)
            print(e, flush=True)

    def set_metadata_and_collection(self, asset: AssetInfo):

        asset_update = AssetUpdate(name=asset.name)

        if len(self.config.tags) > 0:
            asset_update.tags = self.config.tags

        if self.config.metadata is not None and len(self.config.metadata) > 0:
            asset_update.metadata = self.config.metadata

        if self.config.description is not None and self.config.description != "":
            asset_update.description = self.config.description

        try:
            uc.assets.update_asset(asset_update, self.config.org_id, self.config.project_id, asset.am_id, asset.version)
        except Exception as e:
            print(f'Failed to update asset: {asset.name}', flush=True)
            print(e, flush=True)

        if self.config.collection is not None and self.config.collection != "":
            uc.assets.link_assets_to_collection(self.config.org_id, self.config.project_id, self.config.collection,
                                                [asset.am_id])

        uc.assets.freeze_asset_version(self.config.org_id, self.config.project_id, asset.am_id, asset.version,
                                       "new version")

    def get_asset_type(self, cloud_path: PurePosixPath) -> AssetType:
        suffix = cloud_path.suffix.lower()
        if suffix in [".fbx", ".obj", ".prefab"]:
            return AssetType.MODEL_3D
        elif suffix in [".png", ".apng", ".jpg", ".jpeg", ".bmp", ".tiff", ".gif", ".psd", ".tga", ".tif",
                                   ".exr", ".webp", ".svg", "pjpeg", ".pjp", ".jfif", ".avif", ".ico", ".cur", ".ani"]:
            return AssetType.ASSET_2D
        elif suffix in [".mp4", ".webm", ".ogg", ".ogv", ".avi", ".mov", ".flv", ".mkv", ".m4v", ".3gp",
                                   ".h264", ".h265", "wmv"]:
            return AssetType.VIDEO
        elif suffix in [".mp3", ".wav", ".ogg", ".aac"]:
            return AssetType.AUDIO
        elif suffix == ".cs":
            return AssetType.SCRIPT
        elif suffix in [".mat", ".shader"]:
            return AssetType.MATERIAL
        else:
            return AssetType.OTHER

    def get_file_info(self, file: PurePath) -> FileInfo:
        return FileInfo(file, PurePosixPath(file.relative_to(self.config.assets_root_folder)))

    def get_meta_file(self, file: PurePath) -> FileInfo:
        return self.get_file_info(PurePath(f"{file}.meta"))


if __name__ == '__main__':
    config = ProjectUploaderConfig()
    with open("config.json") as f:
        config.load_from_json(json.load(f))

    uploader = ProjectUploader()
    uploader.run(config)