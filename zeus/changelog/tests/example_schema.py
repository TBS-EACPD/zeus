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
    create_standard_changelog_graphql_mixin,
)
from zeus.changelog.consecutive_versions_fetcher import (
    ConsecutiveVersionsFetcher,
    SingleRecordConsecutiveVersionsFetcher,
)
from zeus.changelog.arbitrary_version_pair_fetcher import ArbitraryVersionPairFetcher

from django_sample.models import Author, Book


diffable_models = [
    Author,
    Book,
]
RootQuery = create_standard_changelog_graphql_mixin(diffable_models=diffable_models)

schema = graphene.Schema(query=RootQuery, auto_camelcase=False)


class QueryExecutor(InternalQueryExecutorBase):
    schema = schema
