import asyncio
import subprocess
import json
import logging as log
from collections import defaultdict
import os.path

from galaxy.api.types import LocalGameState

from consts import LAUNCHER_INSTALLED_PATH, SYSTEM, System, LAUNCHER_PROCESS_IDENTIFIER
from process_watcher import ProcessWatcher

if SYSTEM == System.WINDOWS:
    import winreg
    from consts import EPIC_WINREG_LOCATION
elif SYSTEM == System.MACOS:
    from consts import EPIC_MAC_INSTALL_LOCATION


class LauncherInstalledParser:
    def __init__(self):
        self._path = LAUNCHER_INSTALLED_PATH
        self._last_modified = None

    def file_has_changed(self):
        try:
            stat = os.stat(self._path)
        except FileNotFoundError:
            return False
        except Exception as e:
            log.exception(f'Stating {self._path} has failed: {str(e)}')
            raise RuntimeError('Stating failed:' + str(e))
        else:
            if stat.st_mtime != self._last_modified:
                self._last_modified = stat.st_mtime
                return True
            return False

    def _load_file(self):
        content = {}
        try:
            with open(self._path, 'r') as f:
                content = json.load(f)
        except FileNotFoundError as e:
            log.debug(str(e))
        return content

    def parse(self):
        installed_games = {}
        content = self._load_file()
        game_list = content.get('InstallationList', [])
        for entry in game_list:
            app_name = entry.get('AppName', None)
            if not app_name or app_name.startswith('UE'):
                continue
            installed_games[entry['AppName']] = entry['InstallLocation']
        return installed_games


class LocalGamesProvider:
    def __init__(self):
        self._parser = LauncherInstalledParser()
        self._ps_watcher = ProcessWatcher(LAUNCHER_PROCESS_IDENTIFIER)
        self._games = defaultdict(lambda: LocalGameState.None_)
        self._updated_games = set()
        self._was_installed = dict()
        self._was_running = set()
        self._first_run = True
        self._status_updater = None

    @property
    def first_run(self):
        return self._first_run

    @property
    def games(self):
        return self._games

    async def search_process(self, game_id, timeout):
        await self._ps_watcher.pool_until_game_start(game_id, timeout, sint=0.5, lint=2)

    def is_game_running(self, game_id):
        return self._ps_watcher._is_app_tracked_and_running(game_id)

    def consume_updated_games(self):
        tmp = self._updated_games.copy()
        self._updated_games.clear()
        return tmp

    def setup(self):
        log.info('Running local games provider setup')
        self.check_for_installed()
        self.check_for_running()
        loop = asyncio.get_event_loop()
        self._status_updater = loop.create_task(self._endless_status_checker())
        self._first_run = False

    async def _endless_status_checker(self):
        log.info('Starting endless status checker')
        counter = 0
        while True:
            try:
                self.check_for_installed()
                if 0 == counter % 21:
                    await self.parse_all_procs_if_needed()
                elif 0 == counter % 7:
                    self.check_for_running(check_for_new=True)
                self.check_for_running()
            except Exception as e:
                log.error(e)
            finally:
                counter += 1
                await asyncio.sleep(1)

    def check_for_installed(self):
        if not self._parser.file_has_changed():
            return
        log.debug(f'{self._parser._path} file has been found/changed. Parsing')
        installed = self._parser.parse()
        self._update_game_statuses(set(self._was_installed), set(installed), LocalGameState.Installed)
        self._ps_watcher.watched_games = installed
        self._was_installed = installed

    async def parse_all_procs_if_needed(self):
        if local_client._is_installed is True:
            if len(self._was_installed) > 0 and len(self._was_running) == 0:
                await self._ps_watcher._serach_in_all_slowly(interval=0.015)

    def check_for_running(self, check_for_new=False):
        running = self._ps_watcher.get_running_games(check_under_launcher=check_for_new)
        self._update_game_statuses(self._was_running, running, LocalGameState.Running)
        self._was_running = running

    def _update_game_statuses(self, previous, current, status):
        for id_ in (current - previous):
            self._games[id_] |= status
            if not self._first_run:
                self._updated_games.add(id_)

        for id_ in (previous - current):
            self._games[id_] ^= status
            if not self._first_run:
                self._updated_games.add(id_)


class ClientNotInstalled(Exception):
    pass


class _MacosLauncher:
    _OPEN = 'open'

    def __init__(self):
        self._was_client_installed = None

    @property
    def _is_installed(self):
        """:returns:     bool or None if not known """
        # in case we have tried to run it previously
        if self._was_client_installed is not None:
            return self._was_client_installed

        # else we assume that is installed under /Applications
        if os.path.exists(EPIC_MAC_INSTALL_LOCATION):
            return True
        else:  # probably not but we don't know for sure
            return None

    async def exec(self, cmd):
        cmd = f"{self._OPEN} {cmd}"
        log.info(f"Executing shell command: {cmd}")
        proc = await asyncio.create_subprocess_shell(cmd)
        status = None
        try:
            status = await asyncio.wait_for(proc.wait(), timeout=2)
        except asyncio.TimeoutError:
            log.warn('Calling Epic Launcher timeouted. Probably it is fresh installed w/o executable permissions.')
        else:
            if status != 0:
                log.debug(f'Calling Epic Launcher failed with code {status}. Assuming it is not installed')
                self._was_client_installed = False
                raise ClientNotInstalled
            else:
                self._was_client_installed = True


class _WindowsLauncher:
    _OPEN = 'start'

    @staticmethod
    def _parse_winreg_path(path):
        return path.replace('"', '').partition('%')[0].strip()

    @property
    def _is_installed(self):
        try:
            reg = winreg.ConnectRegistry(None, winreg.HKEY_CLASSES_ROOT)
            with winreg.OpenKey(reg, EPIC_WINREG_LOCATION) as key:
                path = self._parse_winreg_path(winreg.QueryValueEx(key, "")[0])
            return os.path.exists(path)
        except OSError:
            return False

    async def exec(self, cmd):
        if not self._is_installed:
            raise ClientNotInstalled

        cmd = f"{self._OPEN} {cmd}"
        log.info(f"Executing shell command: {cmd}")
        subprocess.Popen(cmd, shell=True)


if SYSTEM == System.WINDOWS:
    local_client = _WindowsLauncher()
elif SYSTEM == System.MACOS:
    local_client = _MacosLauncher()
