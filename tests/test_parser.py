import pytest

from local import LauncherInstalledParser


@pytest.fixture
def load_file():
    def func():
        return {
            "InstallationList": [
                {
                    "InstallLocation": "C:\\Program Files\\Epic Games\\Transistor",
                    "AppName": "Dill",
                    "AppID": 0,
                    "AppVersion": "1.50473-x64"
                }
            ]
        }
    return func


def test_launcher_installed_parser(load_file):
    parser = LauncherInstalledParser()
    parser._load_file = load_file
    assert parser.parse() == {'Dill': 'C:\\Program Files\\Epic Games\\Transistor'}
