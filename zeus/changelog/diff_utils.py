import difflib
from itertools import groupby

ADD_HTML_CLASS = "diff_add"
RM_HTML_CLASS = "diff_sub"


class DiffAdd(str):
    @staticmethod
    def combine_to_html(strings):
        return f"<span class='{ADD_HTML_CLASS}'>{' '.join(strings)}</span>"


class DiffRemove(str):
    @staticmethod
    def combine_to_html(strings):
        return f"<span class='{RM_HTML_CLASS}'>{' '.join(strings)}</span>"


class DiffNull(str):
    # these are normal, non-diff strings
    # class is just here for interface's sake
    @staticmethod
    def combine_to_html(strings):
        return " ".join(strings)


def text_compare_inline(before, after):
    """returns a 3-tuple of text"""
    joint = []
    old = []
    new = []

    for word in list(difflib.ndiff(before.split(), after.split())):
        if word.startswith("+ "):
            addition = DiffAdd(word[2:])
            new.append(addition)
            joint.append(addition)
        elif word.startswith("- "):
            removal = DiffRemove(word[2:])
            old.append(removal)
            joint.append(removal)
        elif word.startswith("?"):
            pass
        else:
            word = DiffNull(word)
            old.append(word)
            new.append(word)
            joint.append(word)

    # we want consecutive removes/adds to be in the same <span>,
    # recall that groupby groups consecutive elements together
    joint_formated = " ".join(
        cls.combine_to_html(strings)
        for (cls, strings) in groupby(joint, lambda diffstr: diffstr.__class__)
    )
    old_formated = " ".join(
        cls.combine_to_html(strings)
        for (cls, strings) in groupby(old, lambda diffstr: diffstr.__class__)
    )
    new_formated = " ".join(
        cls.combine_to_html(strings)
        for (cls, strings) in groupby(new, lambda diffstr: diffstr.__class__)
    )

    return (
        joint_formated,
        old_formated,
        new_formated,
    )


def list_diff(before_list, after_list):
    """
        expects 2 lists of strings whose intersections are sorted identically
        This only ever makes sense if lists contain unique elements
    """

    added = set(after_list) - set(before_list)
    removed = set(before_list) - set(after_list)
    combined_list = list({*before_list, *after_list})

    annotated_before_list = []
    annotated_after_list = []
    annotated_combined_list = []

    for string in combined_list:
        is_removed = is_added = False

        if string in added:
            html_class = ADD_HTML_CLASS
            is_added = True
        elif string in removed:
            html_class = RM_HTML_CLASS
            is_removed = True
        else:
            html_class = ""

        annotated_str = f"<p class='{html_class}'>{string}</p>"

        annotated_combined_list.append(annotated_str)

        if is_added:
            annotated_after_list.append(annotated_str)
        elif is_removed:
            annotated_before_list.append(annotated_str)
        else:
            # in both groups -> add it to both
            annotated_before_list.append(annotated_str)
            annotated_after_list.append(annotated_str)

    return (
        "".join(annotated_combined_list),
        "".join(annotated_before_list),
        "".join(annotated_after_list),
    )
