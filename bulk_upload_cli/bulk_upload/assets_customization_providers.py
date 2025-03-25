from abc import ABC, abstractmethod
from bulk_upload.models import AssetCustomization, AssetInfo, ProjectUploaderConfig, Strategy, CollectionInfo, DependencyStrategy
from pathlib import PurePath, PurePosixPath
from shared.utils import execute_prompt
import unity_cloud as uc


class AssetCustomizationProvider(ABC):

    @abstractmethod
    def apply_asset_customization(self, assets: [AssetInfo], config: ProjectUploaderConfig) -> AssetCustomization:
        pass


class InteractiveAssetCustomizer(AssetCustomizationProvider):

    def apply_asset_customization(self, assets: [AssetInfo], config: ProjectUploaderConfig) -> AssetCustomization:
        asset_customization = AssetCustomization()
        asset_customization.tags = self.get_tags()

        if config.strategy == Strategy.UNITY_PACKAGE:
            asset_customization.tags.append(PurePath(config.assets_path).name.replace(".unitypackage", ""))

        if supports_folder_to_collections(config):
            config.path_to_collection = self.get_assets_organization()
        else:
            print("Folder structure to collections mapping is not supported for the selected strategy and/or dependency strategy.")

        if config.path_to_collection:
            print("Mapping folder structure to collections...")
            config.collections = get_folder_collections(config, assets)

        global_collection_name = ""
        if not config.path_to_collection:
            global_collection_name = self.get_collection(config.org_id, config.project_id)

        if global_collection_name != "":
            global_collection = CollectionInfo(PurePosixPath(global_collection_name))
            for asset in assets:
                global_collection.add_asset(asset)
            global_collection.exists_in_cloud = True
            config.collections.append(global_collection)
            config.collection = global_collection_name

        config.tags = asset_customization.tags
        for asset in assets:
            asset.customization.tags = asset_customization.tags

        return assets

    @staticmethod
    def get_tags() -> [str]:
        from InquirerPy import inquirer

        tags = sanitize_tags(execute_prompt(inquirer.text(
            message="Enter the tags to apply to the assets (comma separated; leave empty to assign no tag):",
            mandatory_message="Cannot go back here.")))
        return tags

    @staticmethod
    def get_collection(org_id, project_id) -> str:
        from InquirerPy import inquirer

        try:
            collections = get_cloud_collections(org_id, project_id)
        except Exception as e:
            collections = []

        collections.append("No collection")
        collections.append("Create new collection")
        collection = execute_prompt(inquirer.select(message="Select a collection you want to link all assets to.",
                                                    choices=collections,
                                                    mandatory_message="Cannot go back here."))

        if collection == "Create new collection":
            collection = execute_prompt(inquirer.text(message="Enter the name of the new collection:",
                                                      mandatory_message="Cannot go back here."))

            if collection == "":
                print("Collection name cannot be empty. No collection will be linked to the assets.")
                return ""

            collection_creation = uc.models.CollectionCreation(name=collection, parent_path="",
                                                               description=collection)
            uc.assets.create_collection(collection_creation, org_id, project_id)

        return collection if collection != "No collection" else ""

    @staticmethod
    def get_assets_organization() -> bool:
        from InquirerPy import inquirer
        return execute_prompt(inquirer.confirm(message="Do you want to replicate folder structure with collections?", default=False))


class HeadlessAssetCustomizer(AssetCustomizationProvider):
    def apply_asset_customization(self, assets: [AssetInfo], config: ProjectUploaderConfig) -> AssetCustomization:
        asset_customization = AssetCustomization()
        asset_customization.tags = config.tags

        if config.strategy == Strategy.UNITY_PACKAGE:
            asset_customization.tags.append(PurePath(config.assets_path).name.replace(".unitypackage", ""))

        for asset in assets:
            asset.customization.tags = asset_customization.tags

        if not supports_folder_to_collections(config):
            config.path_to_collection = False
            print("Folder structure to collections mapping is not supported for the selected strategy and/or dependency strategy.")

        if config.path_to_collection:
            print("Global collection not supported when mapping folder structure to collections.")
            config.collection = ""
            print("Mapping folder structure to collections...")
            config.collections = get_folder_collections(config, assets)

        global_collection_name = config.collection
        if global_collection_name != "":
            global_collection = CollectionInfo(PurePosixPath(global_collection_name))
            for asset in assets:
                global_collection.add_asset(asset)
            global_collection.exists_in_cloud = check_if_collection_exist_in_cloud(config.org_id, config.project_id, global_collection_name)
            config.collections.append(global_collection)
            config.collection = global_collection_name

        return assets


class CsvAssetCustomizer(AssetCustomizationProvider):
    def apply_asset_customization(self, assets: [AssetInfo], config: ProjectUploaderConfig) -> AssetCustomization:
        print("Parsing collections from csv file...")
        collections = {}
        for asset in assets:
            for asset_collection in asset.customization.collections:
                if asset_collection == "":
                    continue

                if asset_collection not in collections:
                    collection = CollectionInfo(PurePosixPath(asset_collection))
                    collections[asset_collection] = collection

                collections[asset_collection].add_asset(asset)
                parse_parent_paths_collections(config, collections, PurePosixPath(asset_collection).parent)

        # order collections by depth to ensure that parent collections are created before child collections
        collections = dict(sorted(collections.items(), key=lambda item: len(item[1].path.parts), reverse=False))

        check_if_collections_exists_in_cloud(config.org_id, config.project_id, collections.values())
        config.collections = list(collections.values())

        return assets


class DefaultCustomizationProvider(AssetCustomizationProvider):
    def apply_asset_customization(self, assets: [AssetInfo], config: ProjectUploaderConfig) -> AssetCustomization:
        return assets


def get_cloud_collections(org_id: str, project_id: str):
    collections = uc.assets.list_collections(org_id, project_id)
    return [collection.name for collection in collections]


def sanitize_tags(tags: str) -> list[str]:
    tags = [tag for tag in tags.split(",") if tag != ""]
    return_tags = []
    for tag in tags:
        if tag == "":
            continue
        tag = sanitize_string(tag)
        return_tags.append(tag)
    return return_tags


def sanitize_string(value: str) -> str:
    while value.startswith(" ") or value.endswith(" "):
        if value.startswith(" "):
            value = value[1:]
        if value.endswith(" "):
            value = value[:-1]

    return value


def get_folder_collections(config, assets: [AssetInfo]) -> []:
    collections = {}
    for asset in assets:
        if len(asset.files) == 0:
            continue

        collection_path = asset.files[0].cloud_path.parent

        # We find the shortest file path to the asset to determine the collection path
        for file in asset.files:
            if len(file.cloud_path.parts) < len(collection_path.parts):
                collection_path = file.cloud_path.parent

        if collection_path.__str__() == ".":
            continue

        if collection_path.__str__() not in collections:
            collection = CollectionInfo(collection_path)
            collections[collection_path.__str__()] = collection

        collections[collection_path.__str__()].add_asset(asset)
        parse_parent_paths_collections(config, collections, collection_path.parent)

    # order collections by depth to ensure that parent collections are created before child collections

    collections = dict(sorted(collections.items(), key=lambda item: len(item[1].path.parts), reverse=False))

    check_if_collections_exists_in_cloud(config.org_id, config.project_id, collections.values())
    return list(collections.values())


def parse_parent_paths_collections(config, collections: dict, parent_path: PurePosixPath):
    if parent_path.__str__() == ".":
        return

    if parent_path.__str__() not in collections:
        parent_collection = CollectionInfo(parent_path)
        collections[parent_path.__str__()] = parent_collection

    if len(parent_path.parts) > 1:
        parse_parent_paths_collections(config, collections, parent_path.parent)


def check_if_collections_exists_in_cloud(org_id, project_id, collections: [CollectionInfo]):
    cloud_collections = uc.assets.list_collections(org_id, project_id)

    for collection in collections:
        name = collection.get_name()
        parent_path = collection.get_parent()

        if any(cloud_collection.name == name and cloud_collection.parent_path == parent_path for cloud_collection in
               cloud_collections):
            collection.exists_in_cloud = True


def check_if_collection_exist_in_cloud(org_id, project_id, collection_path: str) -> bool:
    try:
        uc.assets.get_collection(org_id, project_id, collection_path)
        return True
    except Exception as e:
        return False


def supports_folder_to_collections(config: ProjectUploaderConfig) -> bool:
    if (config.strategy in [Strategy.UNITY_PACKAGE, Strategy.SINGLE_FILE_ASSET_UNITY, Strategy.SINGLE_FILE_ASSET]
            and config.dependency_strategy in [DependencyStrategy.NONE, DependencyStrategy.ASSET_REFERENCE]):
        return True

    return False