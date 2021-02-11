from django.conf import settings

import yaml


class TextEntryManager:
    def __init__(self, paths):
        self.paths = paths
        self.base_dir = settings.BASE_DIR
        self._text_entries = None

    def load(self):
        self._text_entries = {}
        for filename in self.paths:
            f = open(filename, "r")
            yaml_dict = yaml.load(f, Loader=yaml.SafeLoader)
            self._add_text_entries(yaml_dict)
            f.close()

    def _add_text_entries(self, to_add):
        for key in to_add.keys():
            if key in self._text_entries:
                raise Exception(f"text key: {key} is already defined")
        self._text_entries.update(to_add)

    def get_entry(self, key):
        return self._text_entries.get(key)

    def has_entry(self, key):
        return key in self._text_entries
