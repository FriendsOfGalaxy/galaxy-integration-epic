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
    EPIC_WINREG_LOCATION = "SOFTWARE\\WOW6432Node\\Epic Games\\EpicGamesLauncher"
    LAUNCHER_WINREG_LOCATION = r"Computer\HKEY_CLASSES_ROOT\com.epicgames.launcher\shell\open\command"
    LAUNCHER_PROCESS_IDENTIFIER = 'EpicGamesLauncher.exe'

elif sys.platform == 'darwin':
    SYSTEM = System.MACOS
    _program_data = os.path.expanduser('~/Library/Application Support')
    EPIC_MAC_INSTALL_LOCATION = "/Applications/Epic Games Launcher.app"
    LAUNCHER_PROCESS_IDENTIFIER = 'Epic Games Launcher'

LAUNCHER_INSTALLED_PATH = os.path.join(_program_data,
                                       'Epic',
                                       'UnrealEngineLauncher',
                                       'LauncherInstalled.dat')

AUTH_URL = r"https://launcher-website-prod07.ol.epicgames.com/epic-login"
AUTH_REDIRECT_URL = r"https://localhost/exchange?code="


def regex_pattern(regex):
    return ".*" + re.escape(regex) + ".*"


AUTH_PARAMS = {
    "window_title": "Login to Epic\u2122",
    "window_width": 700,
    "window_height": 600,
    "start_uri": AUTH_URL,
    "end_uri_regex": regex_pattern(AUTH_REDIRECT_URL)
}

AUTH_JS = {regex_pattern(r"login/showPleaseWait?"): [
    r'''
    [].forEach.call(document.scripts, function(script)
    {
        if (script.text && script.text.includes("loginWithExchangeCode"))
        {
            var codeMatch = script.text.match(/(?<=loginWithExchangeCode\(\')\S+(?=\',)/)
            if (codeMatch)
                window.location.replace("''' + AUTH_REDIRECT_URL + r'''" + codeMatch[0]);
        }
    });
    '''
], regex_pattern(r"login/launcher"): [
    r'''
    document.addEventListener('click', function (event) {

    if (!event.target.matches('#forgotPasswordLink')) return;

    event.preventDefault();

    window.open('https://accounts.epicgames.com/requestPasswordReset', '_blank');
    document.location.reload(true)

}, false);
    '''
]}
