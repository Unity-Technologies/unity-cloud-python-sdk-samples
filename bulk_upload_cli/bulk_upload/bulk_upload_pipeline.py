import unity_cloud as uc

from bulk_upload.config_providers import InteractiveConfigProvider, FileConfigProvider, SelectConfigProvider
from bulk_upload.models import ProjectUploaderConfig, Strategy, DependencyStrategy
from bulk_upload.asset_mappers import NameGroupingAssetMapper, FolderGroupingAssetMapper, UnityPackageAssetMapper, \
    UnityProjectAssetMapper, SingleFileAssetMapper, CsvAssetMapper, CloudAssetMapper
from bulk_upload.assets_uploaders import AssetUploader, CloudAssetUploader
from bulk_upload.assets_customization_providers import AssetCustomizationProvider, InteractiveAssetCustomizer, \
    HeadlessAssetCustomizer, DefaultCustomizationProvider
from bulk_upload.dependency_resolving import DependencyResolver, EmbeddedDependencyResolver, \
    AssetReferenceDependencyResolver, DefaultDependencyResolver
from bulk_upload.validation_providers import ValidationProvider, InteractiveCSVValidationProvider, \
    HeadlessCSVValidationProvider


class BulkUploadPipeline:

    def __init__(self):
        self.config = None

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
            BulkUploadPipeline.login_with_user_account()

    @staticmethod
    def login_with_user_account():
        uc.identity.user_login.use()
        auth_state = uc.identity.user_login.get_authentication_state()
        if auth_state != uc.identity.user_login.Authentication_State.LOGGED_IN:
            uc.identity.user_login.login()

    def run(self, config_file=None, select_config=False):
        is_headless_run = config_file is not None or select_config

        # Step 1: Get base the configuration
        config_provider = self.get_config_provider(select_config, config_file)
        config = config_provider.get_config()

        # Step 2: Login
        self.login(config.key_id, config.key)

        # Step 3: Map the assets and dependencies
        asset_mapper = self.get_asset_mapper(config)
        assets = asset_mapper.map_assets(config)

        # Step 4: Dependencies Resolving
        dependency_resolver = self.get_dependency_resolver(config)
        assets = dependency_resolver.resolve_dependencies(assets)

        # Step 5: Customize ingestion
        customization_provider = self.get_asset_customizer(is_headless_run, config)
        assets = customization_provider.apply_asset_customization(assets, config)

        # Step 6: Validation
        validation_provider = self.get_validation_provider(is_headless_run, config)
        assets = validation_provider.validate_assets(assets, config)

        if not is_headless_run:
            self.write_config(config)

        # Step 7: Upload
        asset_uploader = self.get_asset_uploader(config)
        asset_uploader.upload_assets(assets, config)

        # Step 8: Post upload actions, Clean up
        asset_mapper.clean_up()

    @staticmethod
    def get_config_provider(select_config=False, config_file=None):
        if select_config:
            return SelectConfigProvider()
        elif config_file is None:
            return InteractiveConfigProvider()
        else:
            return FileConfigProvider(config_file)

    @staticmethod
    def get_asset_mapper(config: ProjectUploaderConfig):
        if config.strategy == Strategy.NAME_GROUPING:
            return NameGroupingAssetMapper()
        elif config.strategy == Strategy.FOLDER_GROUPING:
            return FolderGroupingAssetMapper()
        elif config.strategy == Strategy.UNITY_PACKAGE:
            return UnityPackageAssetMapper()
        elif config.strategy == Strategy.SINGLE_FILE_ASSET_UNITY:
            return UnityProjectAssetMapper()
        elif config.strategy == Strategy.SINGLE_FILE_ASSET:
            return SingleFileAssetMapper()
        elif config.strategy == Strategy.CSV_FILE:
            return CsvAssetMapper()
        elif config.strategy == Strategy.CLOUD_ASSET:
            return CloudAssetMapper()
        else:
            raise ValueError("Invalid asset mapper")

    @staticmethod
    def get_dependency_resolver(config: ProjectUploaderConfig):
        if config.dependency_strategy == DependencyStrategy.NONE:
            return DefaultDependencyResolver()
        elif config.dependency_strategy == DependencyStrategy.EMBEDDED:
            return EmbeddedDependencyResolver()
        elif config.dependency_strategy == DependencyStrategy.ASSET_REFERENCE:
            return AssetReferenceDependencyResolver()
        else:
            raise ValueError("Invalid dependency mapper")

    @staticmethod
    def get_asset_customizer(is_headless_run: bool, config: ProjectUploaderConfig):
        if config.strategy == Strategy.CSV_FILE or config.strategy == Strategy.CLOUD_ASSET:
            return DefaultCustomizationProvider()
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
    def write_config(config: ProjectUploaderConfig):
        from InquirerPy import inquirer

        write_config = inquirer.confirm(message="Would you like to save the configuration to a file?").execute()

        if write_config:
            config_name = inquirer.text(message="Enter the name to save the configuration file:").execute()
            file_name = config_name if config_name.endswith(".json") else config_name + ".json"
            with open(file_name, "w") as f:
                f.write(config.to_json())
            print("Configuration saved to", file_name)
        else:
            print("Configuration not saved", flush=True)