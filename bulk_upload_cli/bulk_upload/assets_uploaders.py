import logging
import time

import unity_cloud.assets.asset_reference

from bulk_upload.asset_mappers import *
from bulk_upload.models import *
from concurrent.futures import ThreadPoolExecutor, wait
from unity_cloud.models import *


logger = logging.getLogger(__name__)


class AssetUploader(ABC):
    @abstractmethod
    def upload_assets(self, asset_infos: [AssetInfo], config: ProjectUploaderConfig, app_settings: AppSettings):
        pass


class CloudAssetUploader(AssetUploader):

    def __init__(self):
        self.config = None
        self.futures = list()

    def upload_assets(self, asset_infos: [AssetInfo], config: ProjectUploaderConfig, app_settings: AppSettings):
        self.config = config

        cloud_assets = [] if config.strategy == Strategy.CLOUD_ASSET else uc.assets.get_asset_list(self.config.org_id, self.config.project_id)

        if asset_infos is None:
            return

        if any(collection.exists_in_cloud is False for collection in config.collections):
            print("Creating collections", flush=True)
            self.create_collections(config.collections)

        for asset in asset_infos:
            for project_asset in cloud_assets:
                if asset.name == project_asset.name or (asset.name.lower() == project_asset.name.lower() and not self.config.case_sensitive):
                    asset.am_id = project_asset.id
                    asset.version = project_asset.version
                    asset.already_in_cloud = True
                    asset.is_frozen_in_cloud = project_asset.is_frozen
                    break

        with ThreadPoolExecutor(max_workers=app_settings.parallel_creation_edit) as executor:
            for asset in asset_infos:
                if not asset.already_in_cloud:
                    self.futures.append(executor.submit(self.create_asset, asset))
                elif asset.is_frozen_in_cloud:
                    self.futures.append(executor.submit(self.create_new_version, asset))

        wait(self.futures)
        self.futures = list()

        #sleep for 12 seconds to allow the asset to be created with their dataset
        time.sleep(10)

        print("Setting asset dependencies", flush=True)
        with ThreadPoolExecutor(max_workers=app_settings.parallel_creation_edit) as executor:
            for asset in asset_infos:
                self.futures.append(executor.submit(self.set_asset_references, asset, asset_infos))

            wait(self.futures)
            self.futures = list()

        #sleep for 10 seconds to allow back-end to finish processing
        time.sleep(10)
        print("Setting collections", flush=True)
        self.set_collections(config.collections)

        #sleep for 5 seconds to allow back-end to finish processing
        time.sleep(5)

        if self.config.update_files and self.config.strategy == Strategy.CLOUD_ASSET:
            self.config.update_files = False
            print("File update not supported for cloud assets, skipping file upload", flush=True)
        with ThreadPoolExecutor(max_workers=app_settings.parallel_asset_upload) as executor:
            for asset in asset_infos:
                if not asset.already_in_cloud or self.config.update_files:
                    self.futures.append(executor.submit(self.upload_asset_files, asset, app_settings))

        self.futures = list()

        print("Setting tags and metadata for assets", flush=True)
        with ThreadPoolExecutor(max_workers=app_settings.parallel_creation_edit) as executor:
            for asset in asset_infos:
                self.futures.append(executor.submit(self.set_asset_decorations, asset))

        wait(self.futures)

        action = "uploading"
        print(f"Done {action} assets")

    def validate_config(self):
        print("Validating configuration..", flush=True)
        metadata_keys = uc.assets.list_field_definitions(self.config.org_id, self.config.project_id)
        for key in self.config.metadata.keys():
            if key not in metadata_keys:
                print("Key: " + key + " is not a valid metadata key. It will be ignored.")
                self.config.metadata.pop(key)

    def create_asset(self, asset: AssetInfo):
        try:
            print(f"Creating asset: {asset.name}", flush=True)
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

    def upload_asset_files(self, asset: AssetInfo, app_settings: AppSettings):
        try:

            dataset_id = uc.assets.get_dataset_list(self.config.org_id, self.config.project_id, asset.am_id, asset.version)[0].id

            if self.config.update_files:
                self.delete_existing_files(asset, dataset_id)

            print(f"Uploading files for asset: {asset.name}", flush=True)
            files_upload_futures = []
            with ThreadPoolExecutor(max_workers=app_settings.parallel_file_upload_per_asset) as executor:
                for file in asset.files:
                    files_upload_futures.append(executor.submit(self.upload_file, asset, dataset_id, file))

                if asset.preview_files is not None and len(asset.preview_files) > 0:
                    files_upload_futures.append(executor.submit(self.upload_preview_files, asset))

            wait(files_upload_futures)

        except Exception as e:
            print(f'Failed to upload files for asset: {asset.name}', flush=True)
            logger.exception(e)

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
            logger.exception(e)

    def upload_preview_files(self, asset: AssetInfo):
        try:
            print(f"Uploading preview files for asset: {asset.name}", flush=True)
            datasets = uc.assets.get_dataset_list(self.config.org_id, self.config.project_id, asset.am_id,
                                                  asset.version)
            preview_dataset = next((dataset for dataset in datasets if dataset.name == "Preview"), None)

            for preview_file in asset.preview_files:
                preview_file_upload = FileUploadInformation(organization_id=self.config.org_id,
                                                            project_id=self.config.project_id,
                                                            asset_id=asset.am_id, asset_version=asset.version,
                                                            dataset_id=preview_dataset.id,
                                                            upload_file_path=preview_file.path,
                                                            cloud_file_path=preview_file.cloud_path)

                uc.assets.upload_file(preview_file_upload, disable_automatic_transformations=True)

        except Exception as e:
            print(f'Failed to upload preview file for asset: {asset.name}', flush=True)
            logger.exception(e)

    def set_asset_references(self, asset: AssetInfo, assets: [AssetInfo]):
        try:
            for dependence_index in asset.dependencies:
                asset_referenced = assets[dependence_index]
                unity_cloud.assets.add_asset_reference(self.config.org_id, self.config.project_id, asset.am_id, asset.version,
                                              target_asset_id=asset_referenced.am_id,
                                              target_asset_version=asset_referenced.version)

        except Exception as e:
            print(f'Failed to set references for asset: {asset.name}', flush=True)
            logger.exception(e)

    def set_asset_decorations(self, asset: AssetInfo, skip_freeze: bool = False):
        asset_update = AssetUpdate(name=asset.name)

        if len(asset.customization.tags) > 0:
            asset_update.tags = asset.customization.tags

        if len(asset.customization.metadata) > 0:
            for metadata_field in asset.customization.metadata:
                asset_update.metadata[metadata_field.field_definition] = metadata_field.field_value

        if asset.customization.description is not None and asset.customization.description != "":
            print(asset.customization.description)
            asset_update.description = asset.customization.description

        try:
            uc.assets.update_asset(asset_update, self.config.org_id, self.config.project_id, asset.am_id, asset.version)
        except Exception as e:
            print(f'Failed to update asset: {asset.name}', flush=True)
            print(e, flush=True)

        if not skip_freeze:
            uc.assets.freeze_asset_version(self.config.org_id, self.config.project_id, asset.am_id, asset.version,
                                           "new version")

    def create_collections(self, collections: [CollectionInfo]):
        for collection in collections:
            try:
                if not collection.exists_in_cloud:
                    collection_creation = CollectionCreation(name=collection.get_name(), parent_path=collection.get_parent(), description=collection.get_name())
                    uc.assets.create_collection(collection_creation, self.config.org_id, self.config.project_id)
                    collection.exists_in_cloud = True

            except Exception as e:
                print(f'Failed to create collection: {collection.path.__str__()}', flush=True)
                print(e, flush=True)

    def set_collections(self, collections: [CollectionInfo]):
        for collection in collections:
            try:
                if len(collection.assets) > 0:
                    uc.assets.link_assets_to_collection(self.config.org_id, self.config.project_id, collection.path.__str__(), [asset.am_id for asset in collection.assets])

            except Exception as e:
                print(f'Failed to set assets to collection : {collection.path.__str__()}', flush=True)
                print(e, flush=True)

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

    uploader = AssetUploader()
    uploader.run(config)