from collections import defaultdict

import graphene
from graphene import Boolean, DateTime, Int, List, String

from zeus.changelog.consecutive_versions_fetcher import ConsecutiveVersionsFetcher
from zeus.changelog.graphql.types import ChangelogPage
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


# as a function purely for mocking purposes
def get_changelog_page_size(page_size):
    return page_size


def create_standard_changelog_graphql_mixin(
    diffable_models,
    models_enum=None,
    model_fields_enum=None,
    page_size=50,
    field_name="changelog",
):
    # will use models_enum and model_fields_enum if provided, otherwise generates those

    if models_enum is None:
        model_enum = create_model_enum_type(diffable_models)
    if model_fields_enum is None:
        model_fields_enum = create_model_field_enum_type(diffable_models)

    field = graphene.Field(
        ChangelogPage,
        page_num=Int(required=True),
        models=List(model_enum, required=False),
        user_ids=List(Int, required=False),
        fields=List(model_fields_enum, required=False),
        exclude_create=Boolean(required=False),
        only_creates=Boolean(required=False),
        start_date=DateTime(required=False),
        end_date=DateTime(required=False),
    )

    def resolver(
        _parent,
        _info,
        page_num=None,
        models=None,
        user_ids=None,
        fields=None,
        exclude_create=False,
        only_creates=False,
        start_date=None,
        end_date=None,
    ):
        if models and fields:
            raise Exception(
                "use models or fields but not both - TODO: split this up in 2 different fields"
            )

        if models:
            model_classes = [m for m in diffable_models if m.__name__ in models]
        else:
            model_classes = [*diffable_models]

        if fields:
            fields_by_model = convert_enum_list_to_dict(model_classes, fields)
        else:
            fields_by_model = None

        fetcher = ConsecutiveVersionsFetcher(
            page_size=get_changelog_page_size(page_size),
            page_num=page_num,
            models=model_classes,
            user_ids=user_ids,
            exclude_create=exclude_create,
            only_creates=only_creates,
            fields_by_model=fields_by_model,
            start_date=start_date,
            end_date=end_date,
        )

        return {"fetcher": fetcher}

    return type(
        "StandardChangelogMixin",
        (graphene.ObjectType,),
        {field_name: field, f"resolve_{field_name}": staticmethod(resolver)},
    )
