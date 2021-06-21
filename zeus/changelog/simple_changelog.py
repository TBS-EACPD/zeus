import graphene

from zeus.changelog.graphql.util import (
    convert_enum_list_to_dict,
    create_model_enum_type,
    create_model_field_enum_type,
    create_standard_changelog_graphql_mixin,
)
from zeus.graphql.internal_query_executor_base import InternalQueryExecutorBase

base_query = """
    query ChangelogQuery(
        $page_num :Int!
        $user_ids: [Int]
        $models:[ChangelogModels]
        $fields: [ChangelogModelFields]
        $exclude_create: Boolean!
        $only_creates: Boolean!
        $start_date: DateTime
        $end_date: DateTime
    ) {
        changelog(
            page_num:$page_num,
            user_ids: $user_ids,
            models: $models,
            fields: $fields,
            exclude_create: $exclude_create,
            only_creates: $only_creates,
            start_date: $start_date,
            end_date: $end_date,
        ){
            num_pages
            has_next_page
            changelog_entries {
                model_name
                version {
                    instance
                    edited_by
                }
                eternal
                live_name
                diffs {
                    field
                    field_name
                    action
                    diffed_before
                    diffed_after
                    diffed_combined
                }
            }
        }
    }
"""


def create_simple_changelog(models, page_size=None):
    RootQuery = create_standard_changelog_graphql_mixin(
        diffable_models=models, page_size=page_size
    )
    changelog_schema = graphene.Schema(query=RootQuery, auto_camelcase=False)

    class QueryExecutor(InternalQueryExecutorBase):
        schema = changelog_schema

    query_executor = QueryExecutor()

    return ChangelogContainer(query_executor)


class ChangelogContainer:
    def __init__(self, query_executor):
        self.query_executor = query_executor

    def get_page(
        self,
        page_num,
        models=None,
        user_ids=None,
        fields=None,
        exclude_create=False,
        only_creates=False,
        start_date=None,
        end_date=None,
    ):

        page = self.query_executor.execute_query(
            base_query,
            variables={
                "page_num": page_num,
                "models": models,
                "user_ids": user_ids,
                "fields": fields,
                "exclude_create": exclude_create,
                "only_creates": only_creates,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        return page["changelog"]
