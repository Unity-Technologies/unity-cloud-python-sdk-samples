import json
from enum import Enum
from pathlib import PurePath, PurePosixPath


class Strategy(str, Enum):
    SINGLE_FILE_ASSET = "singleFileAsset"
    NAME_GROUPING = "nameGrouping"
    FOLDER_GROUPING = "folderGrouping"
    UNITY_PACKAGE = "unityPackage"


class ProjectUploaderConfig(object):

    def __init__(self):
        self.strategy = Strategy.SINGLE_FILE_ASSET
        self.files_common_to_every_assets = []
        self.assets_path = ""
        self.file_extensions = []
        self.org_id = ""
        self.project_id = ""
        self.key_id = ""
        self.key = ""
        self.amount_of_parallel_uploads = 15
        self.collection = ""
        self.tags = []
        self.case_sensitive = False
        self.metadata = {}
        self.update_files = False
        self.description = ""

    def load_from_json(self, config_json: dict):
        self.strategy = Strategy(config_json.get("strategy", "resource_type"))
        self.files_common_to_every_assets = config_json.get("filesCommonToEveryAssets", [])
        self.assets_path = config_json.get("assetsPath", "")
        self.file_extensions = config_json.get("assetFileExtensions", [])
        self.org_id = config_json.get("organizationId", "")
        self.project_id = config_json.get("projectId", "")
        self.key_id = config_json.get("serviceAccount", dict()).get("keyId", None)
        self.key = config_json.get("serviceAccount", dict()).get("key", None)
        self.amount_of_parallel_uploads = config_json.get("amountOfParallelUploads", 15)
        self.collection = config_json.get("collectionToLinkAssetTo", None)
        self.tags = config_json.get("tagsToApplyToAssets", [])
        self.case_sensitive = config_json.get("assetNameCaseSensitive", False)
        self.metadata = config_json.get("metadataToApply", {})
        self.update_files = config_json.get("updateFiles", False)
        self.description = config_json.get("description", "")

        # remove the "." from the file extensions
        self.file_extensions = [x[1:] if x.startswith(".") else x for x in self.file_extensions]

        # we remove meta file extension since they are included by default
        if "meta" in self.file_extensions:
            self.file_extensions.remove("meta")
        if ".meta" in self.file_extensions:
            self.file_extensions.remove(".meta")

    def to_json(self):

        asset_path = json.dumps(self.assets_path)
        files_common_to_every_assets = [json.dumps(x) for x in self.files_common_to_every_assets]
        return rf"""{{
    "strategy": "{self.strategy.value}",
    "filesCommonToEveryAssets": {json.dumps(files_common_to_every_assets)},
    "assetsPath": {json.dumps(self.assets_path)},
    "assetFileExtensions": {json.dumps(self.file_extensions)},
    "organizationId": "{self.org_id}",
    "projectId": "{self.project_id}",
    "serviceAccount": {{
        "keyId": "{self.key_id}",
        "key": "{self.key}"
    }},
    "amountOfParallelUploads": {self.amount_of_parallel_uploads},
    "collectionToLinkAssetTo": "{self.collection}",
    "tagsToApplyToAssets": {json.dumps(self.tags)},
    "assetNameCaseSensitive": {self.case_sensitive.__str__().lower()},
    "metadataToApply": {self.metadata},
    "updateFiles": {self.update_files.__str__().lower()},
    "description": {json.dumps(self.description)}
}}
"""


class FileInfo(object):
    def __init__(self, path: PurePath, cloud_path: PurePosixPath):
        self.path = path
        self.cloud_path = cloud_path


class AssetInfo(object):
    def __init__(self, name):
        self.name = name
        self.files = []
        self.am_id = None
        self.unity_id = None
        self.dependencies = []
        self.already_in_cloud = False
        self.version = ""
        self.preview_file = None
        self.is_frozen_in_cloud = False