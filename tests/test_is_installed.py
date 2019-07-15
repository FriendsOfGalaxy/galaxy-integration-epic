from src.local import _WindowsLauncher


def test_parse_winreg_paths():
    possible_winreg_values = {  # reg val : only path
        r'"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe" %1':
            r'C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe',
        r'"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe" %1':
            r"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe",
        r'D:\EpicGames\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe %1':
            r"D:\EpicGames\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe",
        r'"C:\Program Files (x86)\moreargs.exe" %1 %2':
            r"C:\Program Files (x86)\moreargs.exe",
        r'"D:\noargs.exe"':
            r"D:\noargs.exe"
    }
    for val, should_be in possible_winreg_values.items():
        path = _WindowsLauncher._parse_winreg_path(val)
        assert path == should_be
