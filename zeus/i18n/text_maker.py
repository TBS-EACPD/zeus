import sys

from django.conf import settings
from django.utils.functional import lazy
from django.utils.safestring import mark_safe
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from zeus.markdown import markdown, sanitize_html

from .text_entry_manager import TextEntryManager


class TextMakerError(Exception):
    pass


class TextMakerCreator:
    def __init__(self, global_keys, text_files):
        self.validate_text_files(text_files)

        self.entry_manager = TextEntryManager(text_files)
        self.entry_manager.load()
        self.global_keys = global_keys

    @staticmethod
    def validate_text_files(text_files):
        for path in text_files:
            if path.startswith("."):
                raise TextMakerError(f"don't start paths with './' offender: {path}")
            if not path.endswith(".text.yaml"):
                raise TextMakerError("files must have the '.text.yaml' extension")

    def get_tm_func(self):
        return lazy(self._tm, str)

    def _tm(self, key, allow_md=True, extra_keys={}):
        lang = (
            get_language() or "en"
        )  # when called from a non-localized URL (e.g. admin), get_language() is None
        global_keys = self.global_keys[lang]

        if key in global_keys:
            return global_keys[key]

        elif self.entry_manager.has_entry(key):
            entry = self.entry_manager.get_entry(key)

        else:
            raise TextMakerError(f"text key {key} doesn't exist")

        if allow_md is False and entry.get("md", False):
            raise TextMakerError("requested key contains markdown")

        # having unsafe: True on a yaml entry allows weird characters (such as &) to be unescaped
        # note that HTML sanitization will still occur in this case
        # this should be used anytime we interpolate user-input into a yaml template string
        should_mark_safe = True
        if entry.get("unsafe", None):
            should_mark_safe = False

        try:
            if lang in entry:
                text = entry[lang] or f"FIXME: {key}"
            else:
                text = f"FIXME: {entry['en']}"

            if entry.get("md"):
                text = markdown(text)

            template_args = {**global_keys, **extra_keys}

            text = text % template_args

            sanitized = sanitize_html(text, allow_weird_characters=not (should_mark_safe))

            if should_mark_safe:
                return mark_safe(sanitized)
            else:
                return sanitized
        except Exception as e:
            raise TextMakerError(
                f"text_key {key} with arguments: {extra_keys} had the following error \n {e}"
            )


class WatchingTextMakerCreator(TextMakerCreator):
    def __init__(self, global_keys, text_files):
        super().__init__(global_keys, text_files)

        if settings.DEBUG and sys.argv[1] in ("runserver", "rs"):
            self.start_watch()

    def start_watch(self):
        # prevent
        # pylint: disable="import-outside-toplevel relative-beyond-top-level"
        from .text_watcher import text_watcher

        text_watcher.add_entry_watcher(self.entry_manager)
        text_watcher.start_watching()
