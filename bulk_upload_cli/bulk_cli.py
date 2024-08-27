import argparse
import platform
import json
from shared.utils import OperationSystem, download_wheel, pip_install_wheel, pip_install_other_libraries, \
    check_install_requirements, check_python_version
import os

source_folder = "../Source"
wheels_path = os.curdir + "/wheels"


def read_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="Install the requirements for the tool")
    parser.add_argument("--create", action="store_true", help="Bulk create assets in the cloud")
    parser.add_argument("--config-write", action="store_true",
                        help="Write the configuration file instead of running the action. Use with --create.", default=False)
    parser.add_argument("--config-select", action="store_true",help="Select a configuration file to run. Use with --create.", default=False)
    parser.add_argument("--config", type=str, help="Path to the configuration file. Use with --create.", default=None)

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
    download_wheel(wheels_path, current_os, False)
    pip_install_wheel(wheels_path, current_os)
    pip_install_other_libraries()


def run_bulk_assets_creation(interactive=False, config=None, write_config=False, config_select=False):

    if config_select:
        from bulk_assets_creation import interactive_runner
        interactive_runner.run_with_config_select()
    elif interactive or write_config:
        from bulk_assets_creation import interactive_runner
        interactive_runner.run(write_config=write_config)
    else:
        if config is None:
            raise Exception("Configuration file must be provided when running in non-interactive mode.")
        from bulk_assets_creation import models, assets_uploader
        creation_config = models.ProjectUploaderConfig()
        with open(config, "r") as f:
            creation_config.load_from_json(json.load(f))
        uploader = assets_uploader.ProjectUploader()
        uploader.run(creation_config)


if __name__ == "__main__":
    arguments = read_arguments()

    config = arguments.config
    write_config = arguments.config_write
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

    if not arguments.create and not arguments.install:
        print("No action specified. Please always use --create.")
        exit(1)

    if config is None and not write_config and not config_select:
        print("No config options provided. Interactive mode will be used.")
        interactive = True

    if config is not None and write_config:
        raise Exception("Both --config and --write-config cannot be used at the same time.")

    if config is not None and not os.path.exists(config):
        raise Exception("Configuration file not found.")

    if arguments.create:
        run_bulk_assets_creation(interactive, config, write_config, config_select)
    else:
        print("No action specified. Please always use --create.")