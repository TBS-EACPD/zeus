from collections import defaultdict

import graphene
from graphene import Int, List, Boolean, DateTime

from zeus.graphql.internal_query_executor_base import InternalQueryExecutorBase


from zeus.changelog.graphql.types import (
    VersionComparisonEntry,
    ChangelogPage,
    ChangelogEntry,
)
from zeus.changelog.graphql.util import (
    create_model_enum_type,
    create_model_field_enum_type,
    convert_enum_list_to_dict,
)
from zeus.changelog.consecutive_versions_fetcher import (
    ConsecutiveVersionsFetcher,
    SingleRecordConsecutiveVersionsFetcher,
)
from zeus.changelog.arbitrary_version_pair_fetcher import ArbitraryVersionPairFetcher

from django_sample.models import Author, Book

PAGE_SIZE = 250


def get_changelog_page_size():
    return PAGE_SIZE


diffable_models = [
    Author,
    Book,
]

diffable_models_by_name = {cls.__name__: cls for cls in diffable_models}


ModelFieldsEnum = create_model_field_enum_type(diffable_models)
ModelNameEnum = create_model_enum_type(diffable_models)


class ModelNameIntPair(graphene.InputObjectType):
    model = graphene.Field(ModelNameEnum, required=True)
    id = graphene.Int(required=True)


class RootQuery(graphene.ObjectType):
    changelog = graphene.Field(
        ChangelogPage,
        page_num=Int(required=True),
        models=List(ModelNameEnum, required=False),
        user_ids=List(Int, required=False),
        fields=List(ModelFieldsEnum, required=False),
        exclude_create=Boolean(required=False),
        only_creates=Boolean(required=False),
        start_date=DateTime(required=False),
        end_date=DateTime(required=False),
    )

    @staticmethod
    def resolve_changelog(
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

        page_size = get_changelog_page_size()

        fetcher = ConsecutiveVersionsFetcher(
            page_size=page_size,
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


schema = graphene.Schema(query=RootQuery, auto_camelcase=False)


class QueryExecutor(InternalQueryExecutorBase):
    schema = schema
