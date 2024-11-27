import json
import os

from abc import ABC, abstractmethod
from InquirerPy import inquirer

import bulk_upload.bulk_upload_pipeline
from bulk_upload.models import ProjectUploaderConfig, Strategy, DependencyStrategy
from bulk_upload import bulk_upload_pipeline


class ConfigProvider(ABC):
    @abstractmethod
    def get_config(self) -> ProjectUploaderConfig:
        pass


class InteractiveConfigProvider(ConfigProvider):
    def get_config(self) -> ProjectUploaderConfig:
        key_id, key = self.ask_for_login()
        bulk_upload.bulk_upload_pipeline.BulkUploadPipeline.login(key_id, key)

        has_csv = inquirer.confirm("Do you have a CSV file respecting the template with the assets information?").execute()

        if has_csv:
            return self.get_csv_config()

        assets_location = inquirer.select(message="Where are the assets located?",
                                          choices=["in a .unitypackage file", "in a local unity project",
                                                   "in Unity Cloud", "in a folder"]).execute()
        if assets_location == "in a .unitypackage file":
            return self.get_unity_package_config()
        elif assets_location == "in a local unity project":
            return self.get_folder_config(Strategy.SINGLE_FILE_ASSET_UNITY)
        elif assets_location == "in Unity Cloud":
            return self.get_cloud_asset_config()
        elif assets_location == "in a folder":
            strategy = inquirer.select(message="Select a strategy:",
                                       choices=["group files by name", "group files by folder", "One file = one asset"]).execute()
            if strategy == "group files by name":
                return self.get_folder_config(Strategy.NAME_GROUPING)
            elif strategy == "group files by folder":
                return self.get_folder_config(Strategy.FOLDER_GROUPING)
            elif strategy == "One file = one asset":
                return self.get_folder_config(Strategy.SINGLE_FILE_ASSET)

    def get_folder_config(self, strategy: Strategy) -> ProjectUploaderConfig:
        config = ProjectUploaderConfig()
        config.strategy = strategy

        path = inquirer.filepath(message="Enter the path to the root folder of the assets:").execute()
        config.assets_path = self.sanitize_string(path)

        if strategy == Strategy.FOLDER_GROUPING:
            config.hierarchical_level = inquirer.text(
                message="Enter the depth of directory grouping (for example, 1 to group by top folders in your asset directory)").execute()
            config.preview_detection = inquirer.confirm(
                message="Would you like to enable automatic preview detection (see documentation to see how it is detected)?").execute()

        if strategy == Strategy.NAME_GROUPING or strategy == Strategy.SINGLE_FILE_ASSET or strategy == Strategy.FOLDER_GROUPING:
            excluded_file_extensions = inquirer.text(
                message="Enter the file extensions to exclude (comma separated; leave empty to include everything in the search):").execute()

            config.excluded_file_extensions = self.sanitize_extension(excluded_file_extensions)

        if strategy == Strategy.NAME_GROUPING:
            config.case_sensitive = inquirer.confirm(message="Is the asset name case sensitive?").execute()
            config.files_common_to_every_assets = inquirer.text(
                message="Enter the files that are common to every asset (comma separated; leave empty if there are none):").execute().split(
                ",")
            config.files_common_to_every_assets = list(filter(None, config.files_common_to_every_assets))

        if strategy == Strategy.SINGLE_FILE_ASSET_UNITY:
            config.dependency_strategy = self.ask_for_dependency_strategy()
            config.preview_detection = inquirer.confirm(
                message="Would you like to enable automatic preview detection (see documentation to see how it is detected)?").execute()

        config = self.ask_common_questions(config)

        return config

    def get_unity_package_config(self) -> ProjectUploaderConfig:
        config = ProjectUploaderConfig()
        config.strategy = Strategy.UNITY_PACKAGE
        assets_path = inquirer.filepath(message="Enter the path to the Unity package:", only_files=True).execute()
        config.assets_path = self.sanitize_string(assets_path)
        config = self.ask_common_questions(config)
        config.dependency_strategy = self.ask_for_dependency_strategy()

        return config

    def get_csv_config(self) -> ProjectUploaderConfig:
        config = ProjectUploaderConfig()
        config.strategy = Strategy.CSV_FILE
        csv_path = inquirer.filepath(message="Enter the path to the CSV file:", only_files=True).execute()
        config.assets_path = self.sanitize_string(csv_path)
        config = self.ask_common_questions(config)

        return config

    def get_cloud_asset_config(self) -> ProjectUploaderConfig:
        config = ProjectUploaderConfig()
        config.strategy = Strategy.CLOUD_ASSET
        config = self.ask_common_questions(config)
        config.assets_path = f"https://cloud.unity.com/home/organizations/{config.org_id}/projects/{config.project_id}/"
        return config

    @staticmethod
    def ask_common_questions(config: ProjectUploaderConfig) -> ProjectUploaderConfig:
        config.org_id = inquirer.text(message="Enter your organization ID:").execute()
        config.project_id = inquirer.text(message="Enter your project ID:").execute()
        config.update_files = inquirer.confirm(
            message="Would you like to update the files of existing assets ? (This will delete the current ones.)").execute()

        return config

    @staticmethod
    def ask_for_login():
        login_type = inquirer.select(message="Choose authentication method?", choices=["User login", "Service account"]).execute()

        if login_type == "Service account":

            key_id = inquirer.text(message="Enter your key ID:").execute()
            key = inquirer.secret(message="Enter your key:").execute()

            return key_id, key

        return "", ""

    @staticmethod
    def write_config_file(config: ProjectUploaderConfig):
        config_name = inquirer.text(message="Enter the name to save the configuration file:").execute()
        file_name = config_name if config_name.endswith(".json") else config_name + ".json"
        with open(file_name, "w") as f:
            f.write(config.to_json())
        print("Configuration saved to", file_name)

    @staticmethod
    def get_config_select():
        config_files = [f for f in os.listdir() if f.endswith(".json")]
        if len(config_files) == 0:
            print("No configuration files found in the current directory. Please create a configuration file first.")
            return

        config_file = inquirer.select(message="Select a configuration file:", choices=config_files).execute()
        return config_file

    def sanitize_extension(self, extension_string: str) -> list[str]:
        extensions = [ext for ext in extension_string.split(",") if ext != ""]
        return_extensions = []
        for ext in extensions:
            if ext == "":
                continue
            ext = self.sanitize_string(ext)
            if not ext.startswith("."):
                ext = "." + ext
            return_extensions.append(ext)
        return return_extensions

    @staticmethod
    def sanitize_string(value: str) -> str:
        while value.startswith(" ") or value.endswith(" "):
            if value.startswith(" "):
                value = value[1:]
            if value.endswith(" "):
                value = value[:-1]

        return value

    @staticmethod
    def ask_for_dependency_strategy():
        choice = inquirer.select(message="Select a dependency strategy:",
                                 choices=["None", "Embedded", "Asset reference"]).execute()
        if choice == "None":
            return DependencyStrategy.NONE
        elif choice == "Embedded":
            return DependencyStrategy.EMBEDDED
        elif choice == "Asset reference":
            return DependencyStrategy.ASSET_REFERENCE




class SelectConfigProvider(ConfigProvider):
    def get_config(self) -> ProjectUploaderConfig:
        config_files = [f for f in os.listdir() if f.endswith(".json")]
        if len(config_files) == 0:
            print("No configuration files found in the current directory. Please create a configuration file first.")
            return

        config_file = inquirer.select(message="Select a configuration file:", choices=config_files).execute()

        config = ProjectUploaderConfig()
        with open(config_file, "r") as f:
            config.load_from_json(json.load(f))

        return config


class FileConfigProvider(ConfigProvider):
    def __init__(self, config_file: str):
        self.config_file = config_file

    def get_config(self) -> ProjectUploaderConfig:
        config = ProjectUploaderConfig()
        with open(self.config_file, "r") as f:
            config.load_from_json(json.load(f))

        return config