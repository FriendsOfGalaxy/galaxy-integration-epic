import asyncio
import psutil
import logging as log
import time
from typing import Dict, Iterable
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class WatchedApp:
    id: str
    dir: str
    is_game: bool = True

    def __eq__(self, other):
        if isinstance(other, WatchedApp):
            return self.id == other.id
        elif type(other) == str:
            return self.id == other
        else:
            raise TypeError(f"Trying to compare {type(self)} with {type(other)}")

    def __hash__(self):
        return hash(self.id)


class _ProcessWatcher:
    """Low level methods"""
    def __init__(self):
        self._watched_apps = defaultdict(set)  # {WatchedApp: set([proc1, proc2, ...])}
        self._cache = {}

    @property
    def watched_games(self):
        return {k: v for k, v in self._watched_apps.items() if k.is_game}

    @watched_games.setter
    def watched_games(self, to_watch: Dict[str, str]):
        # remove games not present in to_watch
        for app in list(self._watched_apps.keys()):
            if app.is_game and app.id not in to_watch:
                del self._watched_apps[app]
        # add games from to_watch keeping its processes if already present
        for game_id, path in to_watch.items():
            self._watched_apps.setdefault(WatchedApp(game_id, path), set())

    def _get_running_games(self):
        self.__remove_processes_if_dead()
        return set([game.id for game, procs in self.watched_games.items() if procs])

    def _is_app_tracked_and_running(self, app):
        if app in self._watched_apps:
            for proc in self._watched_apps[app]:
                if proc.is_running:
                    return True
        return False

    def _serach_in_all(self):
        """Fat check"""
        log.debug(f'Performing check for all processes')
        for proc in psutil.process_iter(ad_value=''):
            self.__match_process(proc)

    async def _serach_in_all_slowly(self, interval=0.02):
        """Fat check with async intervals; 0.02 lasts a few seconds"""
        log.debug(f'Performing async check in all processes; interval: {interval}')
        for proc in psutil.process_iter(ad_value=''):
            self.__match_process(proc)
            await asyncio.sleep(interval)

    def _search_in_children(self, procs: Iterable[psutil.Process], recursive=True):
        """Cache only child processes because process_iter has its own module level cache"""
        found = False
        for proc in procs.copy():
            try:
                for child in proc.children(recursive=recursive):
                    if child in self._cache:
                        found |= self.__match_process(self._cache[child])
                    else:
                        found |= self.__match_process(child)
                        self._cache[child] = child
            except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                log.warn(f'Getting children of {proc} has failed: {e}')
        return found

    def __match_process(self, proc):
        for game in self._watched_apps:
            try:
                path = proc.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            else:
                if not path:
                    return False
                elif game.dir in path:
                    self._watched_apps[game].add(proc)
                    return True
        return False

    def __remove_processes_if_dead(self):
        for game, processes in self._watched_apps.items():
            # work on copy to avoid adding processes during iteration
            for proc in processes.copy():
                if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                    log.debug(f'Process {proc} is dead')
                    self._watched_apps[game].remove(proc)


class ProcessWatcher(_ProcessWatcher):
    _LAUNCHER_ID = '__launcher__'

    def __init__(self, launcher_identifier):
        super().__init__()
        self._watched_apps[WatchedApp(self._LAUNCHER_ID, launcher_identifier, False)]
        self._launcher_children_cache = set()

    @property
    def _launcher(self):
        return self._watched_apps[self._LAUNCHER_ID]

    def _is_launcher_running(self):
        return self._is_app_tracked_and_running(self._LAUNCHER_ID)

    async def _pool_until_launcher_start(self, timeout, long_interval):
        start = time.time()
        while time.time() - start < timeout:
            if self._is_launcher_running():
                return True
            self._serach_in_all()
            await asyncio.sleep(long_interval)
        return False

    async def pool_until_game_start(self, game_id, timeout, sint, lint):
        """
        :param sint     interval between checking launcher children
        :param lint     (longer) interval between checking if launcher exists
        """
        log.debug(f'Starting wait for game {game_id} process')
        start = time.time()
        while time.time() - start < timeout:
            found = await self._pool_until_launcher_start(timeout, lint)
            if found:
                self._search_in_children(self._launcher)
                if self._watched_apps[game_id]:
                    log.debug(f'Game process found in {time.time() - start}s')
                    return True
                await asyncio.sleep(sint)

        self._serach_in_all()
        if self._watched_apps[game_id]:
            log.debug(f'Game process found in the final fallback parsing all processes')
            return True

    def get_running_games(self, check_under_launcher):
        """Return set of ids of currently running games.
        Note: does not actively look for launcher
        """
        if check_under_launcher and self._is_launcher_running():
            self._search_in_children(self._launcher, recursive=True)
        return self._get_running_games()
