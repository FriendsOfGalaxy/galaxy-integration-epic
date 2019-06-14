from process_watcher import WatchedApp


def test_watched_games_setter(process_watcher):
    process_watcher._watched_apps = {
        WatchedApp("Dill", "C:\\Games\\Transtor"): set(),
        WatchedApp("Min", "C:\\Games\\Minit"): set([1, 2])
    }
    process_watcher.watched_games = {"Min": "C:\\Games\\Minit", "Abu": "D:\\Games\\Rome"}
    expected = {
        WatchedApp("Min", "C:\\Games\\Minit"): set([1, 2]),
        WatchedApp("Abu", "D:\\Games\\Rome"): set()
    }
    assert expected == process_watcher.watched_games
