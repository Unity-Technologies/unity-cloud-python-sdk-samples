from abc import ABC, abstractmethod
from bulk_upload.models import AssetCustomization, AssetInfo, ProjectUploaderConfig, Strategy
from pathlib import PurePath
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

        asset_customization.collection = self.get_collection(config.org_id, config.project_id)

        config.tags = asset_customization.tags
        config.collection = asset_customization.collection
        for asset in assets:
            asset.customization.tags = asset_customization.tags
            asset.customization.collection = asset_customization.collection

        return assets

    @staticmethod
    def get_tags() -> [str]:
        from InquirerPy import inquirer

        tags = sanitize_tags(inquirer.text(
            message="Enter the tags to apply to the assets (comma separated; leave empty to assign no tag):").execute())
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
        collection = inquirer.select(message="Select the collection you want to link the assets to.",
                                     choices=collections).execute()

        if collection == "Create new collection":
            collection = inquirer.text(message="Enter the name of the new collection:").execute()

            if collection == "":
                print("Collection name cannot be empty. No collection will be linked to the assets.")
                return ""

            collection_description = inquirer.text(message="Enter the description of the new collection:").execute()
            if collection_description == "":
                collection_description = collection

            collection_creation = uc.models.CollectionCreation(name=collection, parent_path="",
                                                               description=collection_description)
            uc.assets.create_collection(collection_creation, org_id, project_id)

        return collection if collection != "No collection" else ""


class HeadlessAssetCustomizer(AssetCustomizationProvider):
    def apply_asset_customization(self, assets: [AssetInfo], config: ProjectUploaderConfig) -> AssetCustomization:
        asset_customization = AssetCustomization()

        asset_customization.collection = config.collection
        asset_customization.tags = config.tags

        if config.strategy == Strategy.UNITY_PACKAGE:
            asset_customization.tags.append(PurePath(config.assets_path).name.replace(".unitypackage", ""))

        for asset in assets:
            asset.customization.tags = asset_customization.tags
            asset.customization.collection = asset_customization.collection

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