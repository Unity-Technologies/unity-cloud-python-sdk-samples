import os.path
import sys
import re
import subprocess
from enum import Enum


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
    "green": "\033[4m\033[1m\x1b[32m",
    "yellow": "\x1b[33m",
    "cyan": "\x1b[36m",
}


def __log(color: str, msg: str):
    print(f"{__c(color, msg)}")


def __is_windows():
    return sys.platform == "win32" and os.name == "nt"


def __c(color: str, msg: str) -> str:
    if __is_windows():
        os.system('color')
        return colors[color] + msg + colors["reset"]
    else:
        return colors[color] + msg + colors["reset"]


def log_ok(msg: str):
    __log("green", msg)


def log_warning(msg: str):
    __log("yellow", f"WARNING: {msg}")


def log_error(msg: str):
    __log("red", f"ERROR: {msg}")


def log_info(msg: str):
    __log("cyan", msg)


def pip_install_requirements():
    install_command = [sys.executable, "-m", "pip", "install", "-r", "./requirements.txt", "--force-reinstall"]

    try:
        subprocess.run(install_command, check=True)
        sys.stderr.write(f"Unity Cloud SDK installed successfully.")
    except subprocess.CalledProcessError:
        sys.stderr.write(f"Failed to install Unity Cloud SDK\n")

def check_python_version():
    if sys.version_info < (3, 10):
        return False
    return True

def check_install_requirements():
    try:
        from InquirerPy import prompt
        from InquirerPy.base.control import Choice
        import unity_cloud
        return True
    except ImportError:
        return False


def execute_prompt(prompt, force_mandatory=False):
    @prompt.register_kb("c-q")
    def _handle_kb(event):
        prompt._mandatory = False
        prompt._handle_skip(event)
        exit(1)
    return prompt.execute()