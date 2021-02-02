def get_excluded_fields_for_model(live_model):
    if not hasattr(live_model, "excluded_diff_fields"):
        return ["id"]

    return ["id", *live_model.excluded_diff_fields]


def get_diffable_fields_for_model(live_model):
    all_fields = [*live_model._meta.fields, *live_model._meta.many_to_many]

    excluded = get_excluded_fields_for_model(live_model)

    ret = []
    for f in all_fields:
        if f.name in excluded:
            continue
        ret.append(f)

    return ret
