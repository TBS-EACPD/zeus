from collections import defaultdict


def group_by_iteritems(iterable, key=lambda x: x):
    d = defaultdict(list)
    for item in iterable:
        d[key(item)].append(item)
    return d.items()


def group_by(iterable, key):
    return dict(group_by_iteritems(iterable, key))
