import unity_cloud as uc
import os
import traceback

import unity_cloud.errors

from shared.utils import log_error, log_ok, log_warning, log_info, execute_prompt
from bulk_upload.config_providers import InteractiveConfigProvider, FileConfigProvider, SelectConfigProvider
from bulk_upload.models import ProjectUploaderConfig, Strategy, DependencyStrategy, AppSettings, AssetInfo
from bulk_upload.asset_mappers import NameGroupingAssetMapper, FolderGroupingAssetMapper, UnityPackageAssetMapper, \
    UnityProjectAssetMapper, SingleFileAssetMapper, CsvAssetMapper, CloudAssetMapper
from bulk_upload.assets_uploaders import AssetUploader, CloudAssetUploader
from bulk_upload.assets_customization_providers import AssetCustomizationProvider, InteractiveAssetCustomizer, \
    HeadlessAssetCustomizer, DefaultCustomizationProvider, CsvAssetCustomizer
from bulk_upload.dependency_resolving import DependencyResolver, EmbeddedDependencyResolver, \
    AssetReferenceDependencyResolver, DefaultDependencyResolver
from bulk_upload.validation_providers import ValidationProvider, InteractiveCSVValidationProvider, \
    HeadlessCSVValidationProvider
from bulk_upload.file_explorers import FileExplorer, LocalFileExplorer


class PipelineState:

    def __init__(self, config: ProjectUploaderConfig = None, assets: [AssetInfo] = None):
        self.config = config
        self.assets = assets


class BulkUploadPipeline:

    def __init__(self):
        self.config = None
        self.app_settings = AppSettings()
        self.pipeline_states = {}
        self.step = 0
        self.is_headless_run = False
        self.config_file = None
        self.select_config = False
        self.is_login = False

    def login(self, key_id=None, key=None):
        if self.is_login:
            return

        if key is not None and key_id != "" and key_id is not None and key != "":
            uc.identity.service_account.use(key_id, key)
        else:
            print("Logging in with user account in progress", flush=True)
            BulkUploadPipeline.login_with_user_account()

        self.is_login = True

    @staticmethod
    def login_with_user_account():
        uc.identity.user_login.use()
        auth_state = uc.identity.user_login.get_authentication_state()
        if auth_state != uc.identity.user_login.Authentication_State.LOGGED_IN:
            uc.identity.user_login.login()

    def run(self, config_file=None, select_config=False):
        self.app_settings.load_from_json()
        self.set_environment_variables(self.app_settings)
        self.is_headless_run = config_file is not None or select_config
        self.config_file = config_file
        self.select_config = select_config
        self.init_unity_cloud()
        self.is_login = not self.is_headless_run
        complete = False

        try:
            self.pipeline_states[self.step] = PipelineState()
            complete = self._execute_pipeline()
        except Exception as e:
            complete = False
            log_error(f"An error occurred at step {self.step + 1}.")
            log_error(type(e).__name__)
            if type(e).__name__ == unity_cloud.errors.AuthenticationFailedError.__name__:
                log_warning("Please validate your credentials and restart.")
                exit(1)
            else:
                print(traceback.format_exc())

        if not self.is_headless_run and not complete:
            self.ask_for_retry()

    def _execute_pipeline(self, pipeline_state: PipelineState = PipelineState()):
        assets = pipeline_state.assets
        config = pipeline_state.config

        if self.step == 0:
            # Step 1: Get base the configuration
            print("\n")
            log_ok("Step 1: Get the base configuration")

            config_provider = self.get_config_provider(self.select_config, self.config_file, self.app_settings)
            config = config_provider.get_config()

            self.login(config.key_id, config.key)

            self.step += 1
            self.pipeline_states[self.step] = PipelineState(config, assets)

        if self.step == 1:
            # Step 2: Map the assets and dependencies
            print("\n")
            log_ok("Step 2: Mapping the assets")

            asset_mapper = self.get_asset_mapper(config)
            assets = asset_mapper.map_assets(config)
            log_info(f"Total assets found: {len(assets)}")

            self.step += 1
            self.pipeline_states[self.step] = PipelineState(config, assets)

        if self.step == 2:
            # Step 3: Dependencies Resolving
            print("\n")
            log_ok("Step 3: Resolving dependencies")

            dependency_resolver = self.get_dependency_resolver(config)
            assets = dependency_resolver.resolve_dependencies(assets)

            self.step += 1
            self.pipeline_states[self.step] = PipelineState(config, assets)

        if self.step == 3:
            # Step 4: Customize ingestion
            print("\n")
            log_ok("Step 4: Customizing assets")
            customization_provider = self.get_asset_customizer(self.is_headless_run, config)
            assets = customization_provider.apply_asset_customization(assets, config)

            self.step += 1
            self.pipeline_states[self.step] = PipelineState(config, assets)

        if self.step == 4:
            # Step 5: Validation
            print("\n")
            log_ok("Step 5: Validating assets")
            if not self.is_headless_run:
                self.write_config(config)

            validation_provider = self.get_validation_provider(self.is_headless_run, config)
            assets = validation_provider.validate_assets(assets, config)

            self.step += 1
            self.pipeline_states[self.step] = PipelineState(config, assets)

        if self.step == 5:
            # Step 6: Upload
            print("\n")
            action = "Uploading"
            log_ok(f"Step 6: {action} assets")

            asset_uploader = self.get_asset_uploader(config)
            asset_uploader.upload_assets(assets, config, self.app_settings)

            self.step += 1
            self.pipeline_states[self.step] = PipelineState(config, assets)

        # Step 7: Post upload actions, Clean up
        log_ok("Step 7: Post upload actions")
        asset_mapper.clean_up()

        return True

    @staticmethod
    def set_environment_variables(app_settings: AppSettings):
        for key, value in app_settings.environment_variables.items():
            os.environ[key] = value

    def init_unity_cloud(self):
        try:
            uc.initialize()
            uc.set_timeout(self.app_settings.http_timeout)
        except Exception as e:
            pass

    @staticmethod
    def get_config_provider(select_config=False, config_file=None, app_settings: AppSettings = None):
        if select_config:
            return SelectConfigProvider()
        elif config_file is None:
            return InteractiveConfigProvider(app_settings)
        else:
            return FileConfigProvider(config_file)

    @staticmethod
    def get_asset_mapper(config: ProjectUploaderConfig):
        if config.strategy == Strategy.NAME_GROUPING:
            return NameGroupingAssetMapper(BulkUploadPipeline.get_file_explorer(config))
        elif config.strategy == Strategy.FOLDER_GROUPING:
            return FolderGroupingAssetMapper(BulkUploadPipeline.get_file_explorer(config))
        elif config.strategy == Strategy.UNITY_PACKAGE:
            return UnityPackageAssetMapper()
        elif config.strategy == Strategy.SINGLE_FILE_ASSET_UNITY:
            return UnityProjectAssetMapper(BulkUploadPipeline.get_file_explorer(config))
        elif config.strategy == Strategy.SINGLE_FILE_ASSET:
            return SingleFileAssetMapper(BulkUploadPipeline.get_file_explorer(config))
        elif config.strategy == Strategy.CSV_FILE:
            return CsvAssetMapper()
        elif config.strategy == Strategy.CLOUD_ASSET:
            return CloudAssetMapper()
        else:
            raise ValueError("Invalid asset mapper")

    @staticmethod
    def get_dependency_resolver(config: ProjectUploaderConfig):
        if config.dependency_strategy == DependencyStrategy.NONE:
            print("No dependencies to resolve")
            return DefaultDependencyResolver()
        elif config.dependency_strategy == DependencyStrategy.EMBEDDED:
            print("Resolving embedded dependencies")
            return EmbeddedDependencyResolver()
        elif config.dependency_strategy == DependencyStrategy.ASSET_REFERENCE:
            print("Mapping asset references")
            return AssetReferenceDependencyResolver()
        else:
            raise ValueError("Invalid dependency mapper")

    @staticmethod
    def get_asset_customizer(is_headless_run: bool, config: ProjectUploaderConfig):
        if config.strategy == Strategy.CLOUD_ASSET:
            return DefaultCustomizationProvider()
        elif config.strategy == Strategy.CSV_FILE:
            return CsvAssetCustomizer()
        elif is_headless_run:
            return HeadlessAssetCustomizer()
        else:
            return InteractiveAssetCustomizer()

    @staticmethod
    def get_asset_uploader(config: ProjectUploaderConfig):
        return CloudAssetUploader()

    @staticmethod
    def get_validation_provider(is_headless_run: bool, config: ProjectUploaderConfig):
        if is_headless_run:
            return HeadlessCSVValidationProvider()
        else:
            return InteractiveCSVValidationProvider()

    @staticmethod
    def get_file_explorer(config: ProjectUploaderConfig):
        return LocalFileExplorer()


    @staticmethod
    def write_config(config: ProjectUploaderConfig):
        from InquirerPy import inquirer

        write_config = execute_prompt(inquirer.confirm(message="Would you like to save your choices in a config file for a future headless usage?"))

        if write_config:
            config_name = execute_prompt(inquirer.text(message="Enter the name to save the configuration file:"))
            file_name = config_name if config_name.endswith(".json") else config_name + ".json"
            with open(file_name, "w") as f:
                f.write(config.to_json())
            print("Configuration saved to", file_name)
        else:
            print("Configuration not saved", flush=True)

    def ask_for_retry(self):
        from InquirerPy import inquirer

        steps = ["Get the base configuration", "Mapping the assets", "Resolving dependencies",
                 "Customizing assets", "Validating assets", "Uploading assets"]
        steps = steps[:self.step + 1]
        steps.append("Exit")

        selection = execute_prompt(inquirer.select(message="Choose the step to restart from:", choices=steps))

        if selection == steps[-1]:
            print("Exiting the pipeline")
            exit(1)
        else:
            if selection == steps[0]:
                self.is_login = False
                uc.uninitialize()
                self.init_unity_cloud()

            self.step = steps.index(selection)

            log_info(f"Restarting the pipeline at step {self.step}")
            complete = False
            try:
                complete = self._execute_pipeline(self.pipeline_states[self.step])
            except Exception as e:
                log_error(f"An error occurred during the pipeline at step {self.step + 1}.")
                log_error(type(e).__name__)
                if type(e).__name__ == unity_cloud.errors.AuthenticationFailedError.__name__:
                    log_warning("Please validate your credentials and restart.")
                    exit(1)
                else:
                    print(traceback.format_exc())

            if not complete:
                self.ask_for_retry()