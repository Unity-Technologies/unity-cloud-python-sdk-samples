from abc import ABC, abstractmethod
from bulk_upload.models import AssetInfo, ProjectUploaderConfig, Strategy
import csv
import subprocess
import os
import platform


class ValidationProvider(ABC):
    @abstractmethod
    def validate_assets(self, assets: [AssetInfo], config: ProjectUploaderConfig) -> [AssetInfo]:
        pass


class InteractiveCSVValidationProvider(ValidationProvider):
    def validate_assets(self, assets: [AssetInfo], config: ProjectUploaderConfig) -> [AssetInfo]:
        from InquirerPy import inquirer


        create_csv = False if config.strategy == Strategy.CSV_FILE else inquirer.confirm("Do you want to generate a csv to edit the assets' metadata and infos?").execute()

        if not create_csv:
            self.validate_amount_of_assets(assets)
            return assets

        try:
            metadata_columns = []
            for asset in assets:
                for metadata in asset.customization.metadata:
                    if metadata.field_definition not in metadata_columns:
                        metadata_columns.append(metadata.field_definition)

            with open("validation.csv", mode="w", newline="") as file:
                file.truncate(0)
                writer = csv.writer(file)

                header_row = ["Input", "Name", "Unity Infos", "Files", "Dependencies", "Collection", "Tags", "Preview"]
                for metadata_column in metadata_columns:
                    header_row.append(metadata_column)
                writer.writerow(header_row)
                writer.writerow(
                    [f"{config.strategy.value}?{config.assets_path}", "The name the asset will have in Unity Cloud",
                     "The informations about the asset in Unity and Unity Cloud",
                     "The files that will be uploaded, with the format \"<file path on the computer>:<filepath in the cloud>\"",
                     "The dependencies of the asset. For embedded dependencies, use the file column instead.",
                     "The collection the asset will be linked to", "The tags that will be applied to the asset",
                     "The preview of the asset, with the format \"<file path on the computer>:<filepath in the cloud>\""])

                for asset in assets:
                    writer.writerow(asset.to_csv_row(metadata_columns))
        except Exception as e:
            print("An error occurred while writing the .csv file, the program will skip it.")
            print(e)
            return assets

        validate_csv = inquirer.confirm("Do you want to open the .csv file and review?").execute()

        if validate_csv:
            self.open_csv("validation.csv")
            validation_complete = inquirer.confirm("Have you reviewed the .csv file and are ready to proceed?").execute()

            if not validation_complete:
                print("Bulk creation canceled. The program will exit.")
                exit(0)

            # re-read csv file and update assets
            assets = []
            with open('validation.csv', mode='r') as file:
                dict_reader = csv.DictReader(file)
                next(dict_reader)  # skip header
                for row in dict_reader:
                    asset = AssetInfo(row.get("Name"))
                    asset.from_csv(row)
                    assets.append(asset)

        self.validate_amount_of_assets(assets)

        return assets

    @staticmethod
    def validate_amount_of_assets(assets: [AssetInfo]):
        from InquirerPy import inquirer

        total_size = sum([asset.get_files_size() for asset in assets])
        total_assets = len(assets)

        print(f"You're about to upload {total_assets} assets with a total size of {total_size} bytes.")
        proceed = inquirer.confirm("Do you want to proceed?").execute()
        if not proceed:
            print("Bulk creation canceled. The program will exit.")
            exit(0)

    @staticmethod
    def open_csv(filepath: str):
        if platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', filepath))
        elif platform.system() == 'Windows':  # Windows
            os.startfile(filepath)
        else:  # linux variants
            subprocess.call(('xdg-open', filepath))


class HeadlessCSVValidationProvider(ValidationProvider):
    def validate_assets(self, assets: [AssetInfo], config: ProjectUploaderConfig) -> [AssetInfo]:
        try:
            with open("validation.csv", mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Name", "Unity ID", "Files", "Dependencies", "Collection", "Tags"])
                for asset in assets:
                    writer.writerow(asset.to_csv_row())
        except Exception as e:
            print("An error occurred while writing the .csv file, the program will skip it.")

        return assets