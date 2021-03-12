import os
import re

from django.conf import settings


class TextWatcher:
    def __init__(self):
        self._observer = None
        self._entry_managers_to_watch = []
        self._is_watching = False

    def get_all_watched_files(self):
        files = set()
        for entry_manager in self._entry_managers_to_watch:
            files.update({*entry_manager.paths})
        return files

    def is_file_in_watch_scope(self, suspected_file):
        for watched_file in self.get_all_watched_files():
            if watched_file in suspected_file:
                return True

        return False

    def start_watching(self):
        if not os.environ.get("RUN_MAIN", None):
            # runserver spawns two processes, the initial one watches code and reloads files
            # the other one changes PID and has an env RUN_MAIN=True
            return

        from watchdog.events import RegexMatchingEventHandler
        from watchdog.observers import Observer

        watcher = self

        class RestartOnModifiedEventHandler(RegexMatchingEventHandler):
            def on_modified(self, event):
                # TODO check that the eveng matches a file in get_all_watched_files()

                if watcher.is_file_in_watch_scope(event.src_path):
                    print("=========== reloading yaml text ===========")
                    try:
                        for entry_manager in watcher._entry_managers_to_watch:
                            entry_manager.load()
                    except Exception as e:
                        print(e)
                        print(
                            "text will not work until the above exception is fixed"
                            "\n"
                            "==========="
                        )

        self._observer = Observer()
        self._observer.daemon = True
        event_handler = RestartOnModifiedEventHandler(
            regexes=[r".*.text.yaml"], ignore_directories=True
        )
        self._observer.schedule(
            event_handler, os.path.abspath(settings.BASE_DIR), recursive=True
        )
        self._observer.start()

    def add_entry_watcher(self, entry_manager):
        if self._observer:
            # if already watching, restart the watcher with the new entry manager
            self._stop_watching()
            self._entry_managers_to_watch.append(entry_manager)
            self.start_watching()

        else:
            self._entry_managers_to_watch.append(entry_manager)

    def _stop_watching(self):
        if self._observer:
            self._observer.stop()
            self._observer = None


text_watcher = TextWatcher()
