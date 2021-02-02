from collections import defaultdict
import graphene

from zeus.changelog.util import get_diffable_fields_for_model


def create_model_enum_type(models, enum_name="ChangelogModels"):
    model_names = [m.__name__ for m in models]
    ModelNameEnum = graphene.Enum(enum_name, [(v, v) for v in model_names])
    return ModelNameEnum


def create_model_field_enum_type(models, enum_name="ChangelogModelFields"):
    model_field_enum_vals = []

    for model in models:
        for field in get_diffable_fields_for_model(model):
            if field.name == "id":
                continue

            model_field_enum_vals.append(f"{model.__name__}__{field.name}")

    ModelFieldsEnum = graphene.Enum(enum_name, [(v, v) for v in model_field_enum_vals])
    return ModelFieldsEnum


def convert_enum_list_to_dict(models, enum_list):
    if not enum_list or not models:
        return None
    models_by_name = {model.__name__: model for model in models}
    parsed_pairs = [enum_val.split("__") for enum_val in enum_list]
    fields_by_model = defaultdict(list)
    for (model_name, field_name) in parsed_pairs:
        model_cls = models_by_name[model_name]
        fields_by_model[model_cls].append(field_name)

    return fields_by_model
