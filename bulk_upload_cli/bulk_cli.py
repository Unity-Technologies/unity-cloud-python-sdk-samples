import argparse
import platform
import json

from shared.utils import OperationSystem, pip_install_unity_cloud, pip_install_other_libraries, \
    check_install_requirements, check_python_version
import os

source_folder = "../Source"
wheels_path = os.curdir + "/wheels"


def read_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="Install the requirements for the tool")
    parser.add_argument("--create", action="store_true", help="Bulk create assets in the cloud")
    parser.add_argument("--config-select", action="store_true",help="Select a configuration file to run. Use with --create.", default=False)
    parser.add_argument("--config", type=str, help="Path to the configuration file. Use with --create.", default=None)
    parser.add_argument("--delete", action="store_true", help="Delete assets in a specific project.")

    args = parser.parse_args()
    return args


def get_current_os():
    system = platform.system()
    if system == "Windows":
        return OperationSystem.windows
    elif system == "Linux":
        return "linux"
    elif system == "Darwin":  # macOS
        return OperationSystem.macos
    else:
        raise Exception("Unsupported operating system:" + system)


def install_requirements():
    current_os = get_current_os()
    pip_install_unity_cloud()
    pip_install_other_libraries()


def run_bulk_assets_creation(config=None, select_config=False):
    from bulk_upload import bulk_upload_pipeline
    pipeline = bulk_upload_pipeline.BulkUploadPipeline()
    pipeline.run(config, select_config)


if __name__ == "__main__":
    arguments = read_arguments()

    config = arguments.config
    config_select = arguments.config_select
    interactive = False

    if not check_python_version():
        print("Python version is not supported. Please use Python 3.9 or higher.")
        exit(1)

    if arguments.install:
        install_requirements()
        print("\n\n\n")
        print("===============================================")
        print("Requirements installed.")
        exit(0)

    if not check_install_requirements():
        print("It seems that the requirements are not installed. Please run the script with --install first")
        exit(1)

    if arguments.delete:
        import bulk_upload.asset_deleter as asset_deleter
        asset_deleter.delete_assets_in_project()
        exit(0)

    if not arguments.create and not arguments.install:
        print("No action specified. Use --create to start a bulk creation.")
        exit(1)

    if config is not None and not os.path.exists(config):
        raise Exception("Configuration file not found.")

    if arguments.create:
        run_bulk_assets_creation(config, config_select)
    else:
        print("No action specified. Use --create to start a bulk creation.")