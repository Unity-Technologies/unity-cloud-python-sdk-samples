import json
import os

from abc import ABC, abstractmethod
from InquirerPy import inquirer

import unity_cloud as uc
from bulk_upload.models import ProjectUploaderConfig, Strategy, DependencyStrategy


class ConfigProvider(ABC):
    @abstractmethod
    def get_config(self) -> ProjectUploaderConfig:
        pass


class InteractiveConfigProvider(ConfigProvider):

    def __init__(self):
        self.using_service_account = False

    def get_config(self) -> ProjectUploaderConfig:
        key_id, key = self.ask_for_login()
        self.login(key_id, key)

        assets_location = inquirer.select(message="Where are the assets located?",
                                          choices=["listed in a csv respecting the CLI tool template","in a .unitypackage file", "in a local unity project",
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
        elif assets_location == "listed in a csv respecting the CLI tool template":
            return self.get_csv_config()

    def get_folder_config(self, strategy: Strategy) -> ProjectUploaderConfig:
        config = ProjectUploaderConfig()
        config.strategy = strategy

        while True:
            path = inquirer.filepath(message="Enter the path to the root folder of the assets:").execute()
            path = path.strip('"').strip("'")
            if not os.path.isdir(path):
                print("The path must point to a directory.")
                continue

            config.assets_path = self.sanitize_string(path)
            break

        if strategy == Strategy.FOLDER_GROUPING:
            config.hierarchical_level = inquirer.number(
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

        while True:
            assets_path = inquirer.filepath(message="Enter the path to the Unity package:").execute()
            assets_path = assets_path.strip('"').strip("'")
            if not assets_path.endswith(".unitypackage"):
                print("The path must point to a .unitypackage file.")
                continue
            if not os.path.isfile(assets_path):
                print("The file does not exist.")
                continue
            config.assets_path = self.sanitize_string(assets_path)
            break

        config = self.ask_common_questions(config)
        config.dependency_strategy = self.ask_for_dependency_strategy()

        return config

    def get_csv_config(self) -> ProjectUploaderConfig:
        config = ProjectUploaderConfig()
        config.strategy = Strategy.CSV_FILE
        while True:
            csv_path = inquirer.filepath(message="Enter the path to the CSV file:", only_files=True).execute()
            csv_path = csv_path.strip('"').strip("'")
            if not csv_path.endswith(".csv"):
                print("The path must point to a .csv file.")
                continue
            if not os.path.isfile(csv_path):
                print("The file does not exist.")
                continue
            config.assets_path = self.sanitize_string(csv_path)
            break
        config = self.ask_common_questions(config)

        return config

    def get_cloud_asset_config(self) -> ProjectUploaderConfig:
        config = ProjectUploaderConfig()
        config.strategy = Strategy.CLOUD_ASSET
        config = self.ask_common_questions(config)
        config.assets_path = f"https://cloud.unity.com/home/organizations/{config.org_id}/projects/{config.project_id}/"
        return config

    def ask_common_questions(self, config: ProjectUploaderConfig) -> ProjectUploaderConfig:
        if self.using_service_account:
            config.org_id = inquirer.text(message="Enter the organization ID:").execute()
        else:
            organizations = uc.identity.get_organization_list()
            if len(organizations) == 0:
                print("No organizations found. Please create an organization first.")
                exit(1)
            org_selected = inquirer.select(message="Select an organization:", choices=[org.name for org in organizations]).execute()
            config.org_id = [org.id for org in organizations if org.name == org_selected][0]

        projects = uc.identity.get_project_list(config.org_id)
        if len(projects) == 0:
            print("No projects found in this organization. Please create a project first.")
            exit(1)

        selected_project = inquirer.select(message="Select a project:", choices=[project.name for project in projects]).execute()
        config.project_id = [project.id for project in projects if project.name == selected_project][0]

        config.update_files = inquirer.confirm(
            message="Would you like to update the files of existing assets ? (This will delete the current ones.)").execute()

        return config

    def ask_for_login(self):
        login_type = inquirer.select(message="Choose authentication method?", choices=["User login", "Service account"]).execute()

        if login_type == "Service account":

            key_id = inquirer.text(message="Enter your key ID:").execute()
            key = inquirer.text(message="Enter your key:").execute()

            self.using_service_account = True
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

    @staticmethod
    def login(key_id=None, key=None):
        try:
            uc.initialize()
        except Exception as e:
            return

        if key is not None and key_id != "" and key_id is not None and key != "":
            uc.identity.service_account.use(key_id, key)
        else:
            print("Logging in with user account in progress", flush=True)
            InteractiveConfigProvider.login_with_user_account()

    @staticmethod
    def login_with_user_account():
        uc.identity.user_login.use()
        auth_state = uc.identity.user_login.get_authentication_state()
        if auth_state != uc.identity.user_login.Authentication_State.LOGGED_IN:
            uc.identity.user_login.login()


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