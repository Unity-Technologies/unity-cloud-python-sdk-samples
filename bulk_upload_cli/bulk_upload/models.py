import json
import os
from enum import Enum
from pathlib import PurePath, PurePosixPath


class Strategy(str, Enum):
    SINGLE_FILE_ASSET_UNITY = "singleFileAssetUnity"
    NAME_GROUPING = "nameGrouping"
    FOLDER_GROUPING = "folderGrouping"
    UNITY_PACKAGE = "unityPackage"
    SINGLE_FILE_ASSET = "singleFileAsset"
    CSV_FILE = "csvFile"
    CLOUD_ASSET = "cloudAsset"


class DependencyStrategy(str, Enum):
    NONE = "none"
    EMBEDDED = "embedded"
    ASSET_REFERENCE = "reference"


class FileSource(str, Enum):
    LOCAL = "local"


class ProjectUploaderConfig(object):

    def __init__(self):
        self.file_source = FileSource.LOCAL
        self.strategy = Strategy.SINGLE_FILE_ASSET
        self.dependency_strategy = DependencyStrategy.NONE
        self.files_common_to_every_assets = []
        self.assets_path = ""
        self.excluded_file_extensions = []
        self.org_id = ""
        self.project_id = ""
        self.key_id = ""
        self.key = ""
        self.collection = ""
        self.tags = []
        self.case_sensitive = False
        self.metadata = {}
        self.update_files = False
        self.description = ""
        self.hierarchical_level = 0
        self.preview_detection = False
        self.path_to_collection = False
        self.collections = []

    def load_from_json(self, config_json: dict):
        self.file_source = FileSource(config_json.get("fileSource", "local"))
        self.strategy = Strategy(config_json.get("strategy", "resource_type"))
        self.dependency_strategy = DependencyStrategy(config_json.get("dependency_strategy", "none"))
        self.files_common_to_every_assets = config_json.get("filesCommonToEveryAssets", [])
        self.assets_path = config_json.get("assetsPath", "")
        self.excluded_file_extensions = config_json.get("excludedFileExtensions", [])
        self.org_id = config_json.get("organizationId", "")
        self.project_id = config_json.get("projectId", "")
        self.key_id = config_json.get("serviceAccount", dict()).get("keyId", None)
        self.key = config_json.get("serviceAccount", dict()).get("key", None)
        self.collection = config_json.get("collectionToLinkAssetTo", None)
        self.tags = config_json.get("tagsToApplyToAssets", [])
        self.case_sensitive = config_json.get("assetNameCaseSensitive", False)
        self.metadata = config_json.get("metadataToApply", {})
        self.update_files = config_json.get("updateFiles", False)
        self.description = config_json.get("description", "")
        self.hierarchical_level = config_json.get("hierarchicalLevel", 0)
        self.preview_detection = config_json.get("previewDetection", False)
        self.path_to_collection = config_json.get("pathToCollection", False)

        # remove the "." from the file extensions
        self.excluded_file_extensions = [x[1:] if x.startswith(".") else x for x in self.excluded_file_extensions]

        # we remove meta file extension since they are included by default
        if "meta" in self.excluded_file_extensions:
            self.excluded_file_extensions.remove("meta")
        if ".meta" in self.excluded_file_extensions:
            self.excluded_file_extensions.remove(".meta")



    def to_json(self):

        asset_path = json.dumps(self.assets_path)
        files_common_to_every_assets = [json.dumps(x) for x in self.files_common_to_every_assets]
        return rf"""{{
    "fileSource": "{self.file_source.value}",
    "strategy": "{self.strategy.value}",
    "dependency_strategy": "{self.dependency_strategy.value}",
    "filesCommonToEveryAssets": {json.dumps(files_common_to_every_assets)},
    "assetsPath": {json.dumps(self.assets_path)},
    "excludedFileExtensions": {json.dumps(self.excluded_file_extensions)},
    "organizationId": "{self.org_id}",
    "projectId": "{self.project_id}",
    "serviceAccount": {{
        "keyId": "{self.key_id}",
        "key": "{self.key}"
    }},
    "collectionToLinkAssetTo": "{self.collection}",
    "tagsToApplyToAssets": {json.dumps(self.tags)},
    "assetNameCaseSensitive": {self.case_sensitive.__str__().lower()},
    "metadataToApply": {self.metadata},
    "updateFiles": {self.update_files.__str__().lower()},
    "description": {json.dumps(self.description)},
    "hierarchicalLevel": {self.hierarchical_level},
    "previewDetection": {self.preview_detection.__str__().lower()},
    "pathToCollection": {json.dumps(self.path_to_collection)}
}}
"""


class AppSettings(object):
    DEFAULT_PARALLEL_CREATION_EDIT = 20
    DEFAULT_PARALLEL_ASSET_UPLOAD = 5
    DEFAULT_PARALLEL_FILE_UPLOAD_PER_ASSET = 5
    DEFAULT_HTTP_TIMEOUT = 300

    def __init__(self):
        self.parallel_creation_edit = self.DEFAULT_PARALLEL_CREATION_EDIT
        self.parallel_asset_upload = self.DEFAULT_PARALLEL_ASSET_UPLOAD
        self.parallel_file_upload_per_asset = self.DEFAULT_PARALLEL_FILE_UPLOAD_PER_ASSET
        self.http_timeout = self.DEFAULT_HTTP_TIMEOUT
        self.environment_variables = {}
        self.feature_flags = []

    def load_from_json(self):
        if not os.path.exists("app_settings.json"):
            with open("app_settings.json", "w") as f:
                f.write(self.to_json())
            return

        with open("app_settings.json") as json_file:
            data = json.load(json_file)
            self.parallel_creation_edit = data.get("parallelCreationEdit", self.DEFAULT_PARALLEL_CREATION_EDIT)
            self.parallel_asset_upload = data.get("parallelAssetUpload", self.DEFAULT_PARALLEL_ASSET_UPLOAD)
            self.parallel_file_upload_per_asset = data.get("parallelFileUploadPerAsset", self.DEFAULT_PARALLEL_FILE_UPLOAD_PER_ASSET)
            self.environment_variables = data.get("environmentVariables", {})
            self.http_timeout = data.get("httpTimeout", self.DEFAULT_HTTP_TIMEOUT)

    def to_json(self):
        return rf"""{{
    "parallelCreationEdit": {self.parallel_creation_edit},
    "parallelAssetUpload": {self.parallel_asset_upload},
    "parallelFileUploadPerAsset": {self.parallel_file_upload_per_asset},
    "environmentVariables": {self.environment_variables},
    "featureFlags": {self.feature_flags}
}}
"""


class FileInfo(object):
    def __init__(self, path: PurePath, cloud_path: PurePosixPath):
        self.path = path
        self.cloud_path = cloud_path

    def to_csv(self):
        return f'{self.path} : {self.cloud_path}'


class AssetInfo(object):
    def __init__(self, name):
        self.name = name
        self.files = []
        self.am_id = ""
        self.unity_id = ""
        self.dependencies = []
        self.unresolved_dependencies = []
        self.already_in_cloud = False
        self.version = ""
        self.preview_files = []
        self.is_frozen_in_cloud = False
        self.customization = AssetCustomization()

    def to_csv_row(self, metadata_columns: []) -> [str]:
        files_csv = "\n".join([f.to_csv() for f in self.files])
        preview_files_csv = "\n".join([f.to_csv() for f in self.preview_files])
        dependencies_csv = ",".join([f'{dependency + 2}' for dependency in self.dependencies]) # +2 because of the headers in the csv
        tags_csv = ",".join(self.customization.tags)

        unity_info_csv = f"UnityId:{self.unity_id}\nUnityCloudId:{self.am_id}\nVersionId:{self.version}\nFrozen:{self.is_frozen_in_cloud}"

        collections_csv = ",".join(self.customization.collections)
        asset_csv = ["", self.name, unity_info_csv, f'{files_csv}', f'{dependencies_csv}',
                     self.customization.description, collections_csv,
                     f'{tags_csv}', f'{preview_files_csv}']

        for metadata_column in metadata_columns:
            metadata_value = next((metadata.field_value for metadata in self.customization.metadata if metadata.field_definition == metadata_column), "")
            if metadata_value == "":
                asset_csv.append("")
                continue
            asset_csv.append(f"\"{metadata_value}\"" if isinstance(metadata_value, str) else metadata_value)

        return asset_csv

    def from_csv(self, csv_row: {}):
        self.name = csv_row.get("Name", "")
        self.unity_id = csv_row.get("Unity ID", "")

        unity_infos_csv = csv_row.get("Unity Infos", "")
        unity_infos_rows = unity_infos_csv.split("\n")

        if len(unity_infos_rows) == 4:
            unity_id_row = unity_infos_rows[0].split(":")
            self.unity_id = unity_id_row[1] if len(unity_id_row) == 2 else ""

            am_id_row = unity_infos_rows[1].split(":")
            self.am_id = am_id_row[1] if len(am_id_row) == 2 and am_id_row[1] != "" else ""

            version_row = unity_infos_rows[2].split(":")
            self.version = version_row[1] if len(version_row) == 2 and version_row[1] != "" else ""

            frozen_row = unity_infos_rows[3].split(":")
            self.is_frozen_in_cloud = frozen_row[1] == "True" if len(frozen_row) == 2 else False

            self.already_in_cloud = self.am_id is not None and self.version is not None and self.am_id != "" and self.version != ""

        files_csv = csv_row.get("Files").split('\n')
        for file_csv in files_csv:
            files_csv = file_csv.split(" : ")
            if len(files_csv) != 2:
                continue
            self.files.append(FileInfo(PurePath(files_csv[0]), PurePosixPath(files_csv[1])))

        dependency_csv = csv_row.get("Dependencies", "")
        if dependency_csv != "":
            self.dependencies = [int(dependency) - 2 for dependency in dependency_csv.split(",")]

        self.customization.collections = csv_row.get("Collection", "").split(",")
        self.customization.description = csv_row.get("Description", "")

        tags_csv = csv_row.get("Tags", "")
        self.customization.tags = tags_csv.split(",")

        preview_files_csv = csv_row.get("Preview","").split('\n')
        for preview_file_csv in preview_files_csv:
            preview_file_csv = preview_file_csv.split(" : ")
            if len(preview_file_csv) != 2:
                continue
            self.preview_files.append(FileInfo(PurePath(preview_file_csv[0]), PurePosixPath(preview_file_csv[1])))

        for key, value in csv_row.items():
            if key in ["Input", "Name", "Unity Infos", "Frozen", "Files", "Dependencies", "Collection", "Tags",
                       "Preview", "Description"]:
                continue

            if value == "" or value is None:
                continue

            metadata = Metadata()
            metadata.field_definition = key

            if value.startswith("\"") and value.endswith("\""):
                metadata.field_value = value[1:-1]
            elif value.startswith("[") and value.endswith("]"):
                metadata.field_value = [v.replace("'", "") for v in value[1:-1].split("', '")]
            elif value.lower() == "true" or value.lower() == "false":
                metadata.field_value = value.lower() == "true"
            else:
                metadata.field_value = float(value) if value.replace(".", "", 1).isdigit() else value

            self.customization.metadata.append(metadata)

    def get_files_size(self):
        return sum([os.stat(f.path.__str__()).st_size for f in self.files])

    def is_audio_asset(self):
        if len(self.files) == 1:
            return self.is_audio_extension(self.files[0].path.suffix)
        elif len(self.files) == 2:
            return any(self.is_audio_extension(f.path.suffix) for f in self.files) \
                    and any(f.path.suffix in [".meta"] for f in self.files)
        return False

    @staticmethod
    def is_audio_extension(extension: str):
        return extension.lower() in [".wav", ".mp3", ".ogg", ".aiff", ".aif"]


class AssetCustomization(object):
    def __init__(self):
        self.tags = []
        self.metadata: list[Metadata] = []
        self.description = ""
        self.collections = []


class Metadata(object):
    def __init__(self):
        self.field_definition = ""
        self.field_value = ""

    def to_csv(self):
        return f"{self.field_definition}={self.field_value}"


class CollectionInfo(object):
    def __init__(self, path: PurePosixPath):
        self.path = path
        self.assets = []
        self.exists_in_cloud = False

    def add_asset(self, asset: AssetInfo):
        self.assets.append(asset)
        if self.path.__str__() not in asset.customization.collections:
            asset.customization.collections.append(self.path.__str__())

    def get_name(self):
        return self.path.name

    def get_parent(self):
        parent = self.path.parent
        if parent.__str__() == ".":
            return ""
        return parent.__str__()