import os.path
import shutil
import sys
import urllib.request
import re
import glob
import subprocess
from enum import Enum

sdk_version = "0.10.0"

class OperationSystem(Enum):
    windows = 'windows'
    macos = 'macos'


def get_platform_name(system: str, machine: str) -> str:
    name: str
    if system == "windows":
        if machine == "amd64" or machine == "x86_64":
            name = "win_amd64"
        elif machine == "arm64":
            name = "win_arm64"
    elif system == "darwin":
        name = "macosx_13_0_universal2"
    else:
        raise Exception(f"Unsupported configuration: {system}-{machine}")
    return name

sdk_version = "0.10.0"
protocol = "https://"
domain = "transformation.unity.com"
url_format = f"{protocol}{domain}/downloads/pythonsdks/release/{sdk_version}/unity_cloud-{sdk_version}-py3-none-{{0}}.whl"

wheel_names = {
    OperationSystem.macos: f"unity_cloud-{sdk_version}-py3-none-macosx_13_0_universal2.whl",
    OperationSystem.windows: f"unity_cloud-{sdk_version}-py3-none-win_amd64.whl",
}

operation_systems = {
    OperationSystem.macos: url_format.format("macosx_13_0_universal2"),
    OperationSystem.windows: url_format.format("win_amd64")
}


colors = {
    "reset": "\x1b[0m",
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "cyan": "\x1b[36m",
}


def __log(color: str, msg: str):
    print(f"{__c(color, msg)}")


def __is_windows():
    return sys.platform == "win32" and os.name == "nt"


def __c(color: str, msg: str) -> str:
    if __is_windows():
        return msg
    else:
        return colors[color] + msg + colors["reset"]


def log_ok(msg: str):
    __log("green", msg)


def log_warning(msg: str):
    __log("yellow", f"WARNING: {msg}")


def log_error(msg: str):
    __log("red", f"ERROR: {msg}")


def copy_wheels(source_folder: str, destination_folder: str, systems: list[OperationSystem],
                skip_missing: bool) -> bool:
    if not os.path.exists(source_folder):
        return False
    else:
        os.makedirs(destination_folder, exist_ok=True)
        for system in systems:
            wheel_details = operation_systems[system]
            for platform_name in wheel_details:
                matching_files = glob.glob(f"{source_folder}/unity_cloud*-py3-none-{platform_name}.whl")
                if len(matching_files) == 0:
                    msg = f"Could not find wheel file for {platform_name}"
                    if skip_missing:
                        log_warning(msg)
                    else:
                        log_error(msg)
                        return False
                for source_file in matching_files:
                    destination_file = os.path.join(destination_folder, os.path.basename(source_file))
                    if source_file != destination_file:
                        shutil.copy(source_file, destination_file)
                        print(f"\"{source_file}\" copied to \"{destination_file}\"")
    return True


def __download_file(download_path: str, file_url: str) -> bool:
    try:
        response = urllib.request.urlopen(file_url)
    except Exception as err:
        log_error(f"Failed to download from {file_url}. Exception: {err}")
        return False

    if response.code != 200:
        log_error(f"Failed to download from {file_url}. Status code: {response.code}")
        return False

    decoded_filename: str
    if 'Content-Disposition' in response.headers:
        content_disposition = response.headers['Content-Disposition']
        filename_match = re.search(r'filename\*=(?:UTF-8\'\'|utf-8\'\'|\'\'|"")?([^\'"]+)', content_disposition)

        if not filename_match:
            log_error(f"Failed to download from {file_url}: Downloaded data has unexpected format")
            return False

        utf8_encoded_filename = filename_match.group(1)
        decoded_filename = utf8_encoded_filename
    else:
        decoded_filename = file_name = os.path.basename(file_url)
    with open(os.path.join(download_path, decoded_filename), "wb") as file:
        file.write(response.read())
    return True


def download_wheel(download_path: str, system: str, skip_missing: bool,
                   overwrite=False, write_log=True, ) -> bool:
    os.makedirs(download_path, exist_ok=True)
    if write_log:
        print("Downloading unity-cloud wheel files...")

    wheel_name = operation_systems[system]
    path = os.path.join(download_path, wheel_name)
    if not os.path.exists(path) or overwrite:
        if write_log:
            print(f"Downloading wheel file for {wheel_name}...")
        __download_file(download_path,  wheel_name)

    else:
        print(f"Skipping \"{path}\". The file already exists")
    return True


def pip_install_wheel(download_path: str, system: str):

    #check if wheel is installed with a recent version
    try:
        version_check_command = [sys.executable, "-m", "pip", "show","unity_cloud"]
        version_check_output = subprocess.run(version_check_command, check=True, capture_output=True, text=True)
        version = re.search(r"Version: (\d+\.\d+\.\d+)", version_check_output.stdout).group(1)
        if version >= sdk_version:
            print(f"Unity Cloud SDK is already installed and up to date.")
        return

    except Exception:
        pass

    install_command = [sys.executable, "-m", "pip", "install", "wheel"]
    try:
        subprocess.run(install_command, check=True)
    except subprocess.CalledProcessError:
        sys.stderr.write(f"Failed to install wheel package\n")
        return False

    wheel_name = wheel_names[system]
    wheel_path = os.path.join(download_path, wheel_name)
    install_command = [sys.executable, "-m", "pip", "install", wheel_path, "--force-reinstall"]
    try:
        subprocess.run(install_command, check=True)
        print(f"Wheel {wheel_path} installed successfully.")
    except subprocess.CalledProcessError:
        sys.stderr.write(f"Failed to install wheel {wheel_path}\n")


def pip_install_other_libraries():
    install_command = [sys.executable, "-m", "pip", "install", "InquirerPy"]
    try:
        subprocess.run(install_command, check=True)
        print(f"Other libraries installed successfully.")
    except subprocess.CalledProcessError:
        sys.stderr.write(f"Failed to install other libraries\n")

def check_python_version():
    if sys.version_info < (3, 10):
        return False
    return True

def check_install_requirements():
    try:
        from InquirerPy import prompt
        from InquirerPy.base.control import Choice
        import unity_cloud
    except ImportError:
        return False
    return True