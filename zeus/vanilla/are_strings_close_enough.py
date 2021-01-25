import string


def are_strings_close_enough(s1, s2):
    """
    tests that both strings are equal if you remove punctuation, space characters and ignore case
  """
    remove = string.punctuation + string.whitespace
    translate_table = str.maketrans(dict.fromkeys(remove))

    return s1.lower().translate(translate_table) == s2.lower().translate(translate_table)
