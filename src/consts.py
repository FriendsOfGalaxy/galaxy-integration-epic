import os
import sys
import re
from enum import EnumMeta


class System(EnumMeta):
    WINDOWS = 1
    MACOS = 2
    LINUX = 3


_program_data = ''

SYSTEM = None

if sys.platform == 'win32':
    SYSTEM = System.WINDOWS
    _program_data = os.getenv('PROGRAMDATA')
    EPIC_WINREG_LOCATION = r"com.epicgames.launcher\shell\open\command"
    LAUNCHER_WINREG_LOCATION = r"Computer\HKEY_CLASSES_ROOT\com.epicgames.launcher\shell\open\command"
    LAUNCHER_PROCESS_IDENTIFIER = 'EpicGamesLauncher.exe'

elif sys.platform == 'darwin':
    SYSTEM = System.MACOS
    _program_data = os.path.expanduser('~/Library/Application Support')
    EPIC_MAC_INSTALL_LOCATION = "/Applications/Epic Games Launcher.app"
    LAUNCHER_PROCESS_IDENTIFIER = 'Epic Games Launcher'

LAUNCHER_INSTALLED_PATH = os.path.join(_program_data, 'Epic', 'UnrealEngineLauncher', 'LauncherInstalled.dat')
GAME_MANIFESTS_PATH = os.path.join(_program_data, 'Epic', 'EpicGamesLauncher', 'Data' 'Manifests')

AUTH_URL = r"https://www.epicgames.com/id/login"
AUTH_REDIRECT_URL = r"https://epicgames.com/account/personal"


def regex_pattern(regex):
    return ".*" + re.escape(regex) + ".*"


AUTH_PARAMS = {
    "window_title": "Login to Epic\u2122",
    "window_width": 580,
    "window_height": 750,
    "start_uri": AUTH_URL,
    "end_uri_regex": regex_pattern(AUTH_REDIRECT_URL)
}