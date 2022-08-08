from django.utils.safestring import mark_safe

import bleach
import mistune

ALLOWED_TAGS = ["a", "b", "em", "i", "li", "ol", "p", "strong", "ul", "br", "div"]


def sanitize_html(html_str, allow_weird_characters=False):
    with_terrible_replacements = bleach.clean(html_str, tags=ALLOWED_TAGS)
    # see https://github.com/mozilla/bleach/issues/192
    if allow_weird_characters:
        return with_terrible_replacements.replace("&amp;", "&")
    else:
        return with_terrible_replacements


def is_md_valid(md_str):
    markdown_from_src = mistune.create_markdown()
    unsanitized = markdown_from_src(str(md_str))
    sanitized = sanitize_html(unsanitized)
    return unsanitized == sanitized


def markdown(md_str):
    """
    mark_safe being run through bleach
    """
    markdown = mistune.create_markdown()
    return mark_safe(sanitize_html(markdown(str(md_str))))
