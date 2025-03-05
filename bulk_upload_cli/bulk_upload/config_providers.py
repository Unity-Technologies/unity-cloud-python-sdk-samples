import json
import os

from abc import ABC, abstractmethod
from InquirerPy import inquirer
from shared.utils import log_info, execute_prompt

import unity_cloud as uc
from bulk_upload.models import ProjectUploaderConfig, Strategy, DependencyStrategy, AppSettings, FileSource


class ConfigProvider(ABC):
    @abstractmethod
    def get_config(self) -> ProjectUploaderConfig:
        pass


class UndoException(Exception):
    pass


class InteractiveConfigProvider(ConfigProvider):
    possible_actions = ["Upload local assets", "Update assets' metadata"]
    actual_step = 0
    last_step = 0

    def __init__(self, app: AppSettings):
        self.app = app
        self.selected_action = None
        self.assets_location = None
        self.config = None
        self.actual_step = 0
        self.last_step = 0
        self.using_service_account = False

    def execute_prompt_and_increment_step(self, prompt, force_mandatory=False):
        prompt._mandatory = force_mandatory
        value = execute_prompt(prompt)

        if value is None:
            raise UndoException()
        else:
            self.increment_steps()

        return value

    def execute_prompt_auto(self, prompt, value, force_mandatory=False):
        if self.must_skip():
            return value
        return self.execute_prompt_and_increment_step(prompt, force_mandatory)

    def increment_steps(self):
        self.last_step = self.actual_step

    def must_skip(self):
        must_skip = self.actual_step < self.last_step
        self.actual_step += 1
        return must_skip

    def get_config(self) -> ProjectUploaderConfig:
        key_id, key = self.ask_for_login()
        self.login(key_id, key)
        self.config = ProjectUploaderConfig()
        while True:
            try:
                self._get_config()
                return self.config
            except UndoException:
                log_info("\nUndoing last step.\n")
                self.actual_step = 0
                self.last_step -= 1
                pass

    def _get_config(self) -> ProjectUploaderConfig:
        self.ask_for_organization()
        self.ask_for_project()
        self.ask_for_action()

        if self.selected_action == self.possible_actions[1]:
            return self.get_cloud_asset_config()

        self.ask_for_assets_location()

        if self.assets_location == "in a .unitypackage file":
            return self.get_unity_package_config()
        elif self.assets_location == "in a local unity project":
            self.config.strategy = Strategy.SINGLE_FILE_ASSET_UNITY
            return self.get_folder_config(Strategy.SINGLE_FILE_ASSET_UNITY)
        elif self.assets_location == "in a folder":
            self.ask_for_folder_strategy()
            return self.get_folder_config(self.config.strategy)
        elif self.assets_location == "listed in a csv respecting the CLI tool template":
            return self.get_csv_config()

    def ask_for_organization(self):
        if self.must_skip():
            return

        if self.using_service_account:
            self.config.org_id = self.execute_prompt_and_increment_step(inquirer.text(message="Enter the organization ID:"), force_mandatory=True)
            return

        organizations = uc.identity.get_organization_list()
        if len(organizations) == 0:
            print("No organizations found. Please create an organization first. Application will exit.")
            exit(1)

        org_selected = self.execute_prompt_and_increment_step(
            inquirer.select(message="Select an organization:", choices=[org.name for org in organizations],
                            mandatory_message="Cannot redo login. Please press Ctrl+Q to exit and restart."),
            force_mandatory=True)
        self.config.org_id = [org.id for org in organizations if org.name == org_selected][0]

    def ask_for_project(self):
        if self.must_skip():
            return

        projects = uc.identity.get_project_list(self.config.org_id)
        if len(projects) == 0:
            print("No projects found in this organization. Please create a project first. Application will exit.")
            exit(1)

        selected_project = self.execute_prompt_and_increment_step(
            inquirer.select(message="Select a project:", choices=[project.name for project in projects]))
        self.config.project_id = [project.id for project in projects if project.name == selected_project][0]

    def ask_for_action(self):
        if self.must_skip():
            return

        selected_actions_choices = self.possible_actions

        self.selected_action = self.execute_prompt_and_increment_step(inquirer.select(message="Select an action:", choices=selected_actions_choices))

    def ask_for_assets_location(self):
        if self.must_skip():
            return
        self.assets_location = self.execute_prompt_and_increment_step(
            inquirer.select(message="Where are the assets located?",
                            choices=[
                                "listed in a csv respecting the CLI tool template",
                                "in a .unitypackage file",
                                "in a local unity project",
                                "in a folder"]))

    def ask_for_folder_strategy(self):
        if self.must_skip():
            return

        strategy = self.execute_prompt_and_increment_step(inquirer.select(message="Select a strategy:",
                                                                          choices=["group files by name",
                                                                                   "group files by folder",
                                                                                   "One file = one asset"]))

        if strategy == "group files by name":
            self.config.strategy = Strategy.NAME_GROUPING
        elif strategy == "group files by folder":
            self.config.strategy = Strategy.FOLDER_GROUPING
        elif strategy == "One file = one asset":
            self.config.strategy = Strategy.SINGLE_FILE_ASSET

    def get_folder_config(self, strategy: Strategy) -> ProjectUploaderConfig:

        if not self.must_skip():
            while True:
                path = self.execute_prompt_and_increment_step(
                    inquirer.filepath(message="Enter the path to the root folder of the assets:")).strip('\"').strip(
                    "\'")
                if not os.path.isdir(path):
                    self.last_step -= 1
                    print("The path must point to a directory.")
                    continue

                self.config.assets_path = self.sanitize_string(path)
                break

        if strategy == Strategy.FOLDER_GROUPING:
            self.config.hierarchical_level = self.execute_prompt_auto(inquirer.number(
                message="Enter the depth of directory grouping (for example, 1 to group by top folders in your asset directory)"),
                self.config.hierarchical_level)
            self.config.preview_detection = self.execute_prompt_auto(inquirer.confirm(
                message="Would you like to enable automatic preview detection (see documentation to see how it is detected)?"),
                self.config.preview_detection)

        if strategy == Strategy.NAME_GROUPING or strategy == Strategy.SINGLE_FILE_ASSET or strategy == Strategy.FOLDER_GROUPING:
            if not self.must_skip():
                excluded_file_extensions = self.execute_prompt_and_increment_step(inquirer.text(
                    message="Enter the file extensions to exclude (comma separated; leave empty to include everything in the search):"))

                self.config.excluded_file_extensions = self.sanitize_extension(excluded_file_extensions)

        if strategy == Strategy.NAME_GROUPING:
            self.config.case_sensitive = self.execute_prompt_auto(
                inquirer.confirm(message="Is the asset name case sensitive?"), self.config.case_sensitive)
            if not self.must_skip():
                self.config.files_common_to_every_assets = self.execute_prompt_and_increment_step(inquirer.text(
                    message="Enter the files that are common to every asset (comma separated; leave empty if there are none):")).split(
                    ",")
                self.config.files_common_to_every_assets = list(filter(None, self.config.files_common_to_every_assets))

        if strategy == Strategy.SINGLE_FILE_ASSET_UNITY:
            self.ask_for_dependency_strategy()

            self.config.preview_detection = self.execute_prompt_auto(inquirer.confirm(
                message="Would you like to enable automatic preview detection (see documentation to see how it is detected)?"),
                self.config.preview_detection)

        return self.config

    def get_unity_package_config(self) -> ProjectUploaderConfig:
        self.config.strategy = Strategy.UNITY_PACKAGE

        if not self.must_skip():
            while True:
                assets_path = self.execute_prompt_and_increment_step(
                    inquirer.filepath(message="Enter the path to the Unity package:")).strip('\"').strip("\'")
                if not assets_path.endswith(".unitypackage"):
                    print("The path must point to a .unitypackage file.")
                    self.last_step -= 1
                    continue
                if not os.path.isfile(assets_path):
                    print("The file does not exist.")
                    self.last_step -= 1
                    continue
                self.config.assets_path = self.sanitize_string(assets_path)
                break

        self.ask_for_dependency_strategy()

        self.config.update_files = self.execute_prompt_auto(inquirer.confirm(
            "Would you like to enable automatic preview detection (see documentation to see how it is detected)?"),
            self.config.update_files)

        return self.config

    def get_csv_config(self) -> ProjectUploaderConfig:
        self.config.strategy = Strategy.CSV_FILE

        if not self.must_skip():
            while True:
                csv_path = self.execute_prompt_and_increment_step(
                    inquirer.filepath(message="Enter the path to the CSV file:", only_files=True)).strip('\"').strip(
                    "\'")
                if not csv_path.endswith(".csv"):
                    self.last_step -= 1
                    print("The path must point to a .csv file.")
                    continue
                if not os.path.isfile(csv_path):
                    self.last_step -= 1
                    print("The file does not exist.")
                    continue
                self.config.assets_path = self.sanitize_string(csv_path)
                break

        self.config.update_files = self.execute_prompt_auto(inquirer.confirm(
            message="Would you like to update the files of existing assets ? (This will delete the current ones.)"),
            self.config.update_files)

        return self.config

    def get_cloud_asset_config(self) -> ProjectUploaderConfig:
        self.config.strategy = Strategy.CLOUD_ASSET
        self.config.assets_path = f"https://cloud.unity.com/home/organizations/{self.config.org_id}/projects/{self.config.project_id}/"
        return self.config

    @staticmethod
    def ask_for_login():
        login_type = execute_prompt(inquirer.select(message="Choose authentication method?",
                                                    choices=["User login", "Service account"]))

        if login_type == "Service account":
            key_id = execute_prompt(inquirer.text(message="Enter your key ID:"))
            key = execute_prompt(inquirer.secret(message="Enter your key:"))

            return key_id, key

        return "", ""

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

    def ask_for_dependency_strategy(self):
        if self.must_skip():
            return

        choice = self.execute_prompt_and_increment_step(inquirer.select(message="Select a dependency strategy:",
                                                                        choices=["No dependencies", "Embedded",
                                                                                 "Asset reference"]))
        if choice == "No dependencies":
            self.config.dependency_strategy = DependencyStrategy.NONE
        elif choice == "Embedded":
            self.config.dependency_strategy = DependencyStrategy.EMBEDDED
        elif choice == "Asset reference":
            self.config.dependency_strategy = DependencyStrategy.ASSET_REFERENCE

    def login(self, key_id=None, key=None):
        if key is not None and key_id != "" and key_id is not None and key != "":
            uc.identity.service_account.use(key_id, key)
            self.using_service_account = True
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
        config_files = [f for f in os.listdir() if f.endswith(".json") and f != "app_settings.json"]
        if len(config_files) == 0:
            print("No configuration files found in the current directory. Please create a configuration file first.")
            exit(1)

        config_file = execute_prompt(inquirer.select(message="Select a configuration file:", choices=config_files))

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