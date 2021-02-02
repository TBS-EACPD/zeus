import os

from zeus.i18n.text_maker import TextMakerCreator

path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)
yaml_file = os.path.join(dir_path, "changelog_text.text.yaml")

tm = TextMakerCreator({"en": {}, "fr": {}}, [yaml_file]).get_tm_func()
