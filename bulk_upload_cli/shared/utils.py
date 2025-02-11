import os.path
import sys
import re
import subprocess
from enum import Enum

sdk_version = "0.10.3"

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


def pip_install_unity_cloud():
    try:
        version_check_command = [sys.executable, "-m", "pip", "show", "unity_cloud"]
        version_check_output = subprocess.run(version_check_command, check=True, capture_output=True, text=True)
        version = re.search(r"Version: (\d+\.\d+\.\d+)", version_check_output.stdout).group(1)
        if version > sdk_version:
            sys.stderr.write(f"Unity Cloud SDK already installed with the correct version.")
            return
    except subprocess.CalledProcessError:
        pass

    install_command = [sys.executable, "-m", "pip", "install", "--index-url",
                        "https://unity3ddist.jfrog.io/artifactory/api/pypi/am-pypi-prod-local/simple",
                        f"unity-cloud=={sdk_version}", "--force-reinstall"]
    try:
        subprocess.run(install_command, check=True)
        sys.stderr.write(f"Unity Cloud SDK installed successfully.")
    except subprocess.CalledProcessError:
        sys.stderr.write(f"Failed to install Unity Cloud SDK\n")


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
        # check if wheel is installed with a recent version
        try:
            version_check_command = [sys.executable, "-m", "pip", "show", "unity_cloud"]
            version_check_output = subprocess.run(version_check_command, check=True, capture_output=True, text=True)
            version = re.search(r"Version: (\d+\.\d+\.\d+)", version_check_output.stdout).group(1)
            return version >= sdk_version
        except subprocess.CalledProcessError:
            return False

    except ImportError:
        return False