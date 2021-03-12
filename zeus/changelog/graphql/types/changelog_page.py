import graphene
from graphene import Boolean, Int, List

from .changelog_entry import ChangelogEntry


class ChangelogPage(graphene.ObjectType):
    has_next_page = Boolean()
    total_version_count = Int()
    num_pages = Int()
    changelog_entries = List(ChangelogEntry)

    @staticmethod
    def resolve_changelog_entries(parent, _info):
        fetcher = parent["fetcher"]
        fields_by_model = fetcher.fields_by_model or {}
        return [
            {
                **data_record,
                "fields": fields_by_model.get(data_record["eternal"].__class__, None),
            }
            for data_record in fetcher.get_fully_fetched_edit_entries()
        ]

    @staticmethod
    def resolve_has_next_page(parent, _info):
        fetcher = parent["fetcher"]
        return fetcher.get_total_page_count() > fetcher.page_num

    @staticmethod
    def resolve_total_version_count(parent, _info):
        fetcher = parent["fetcher"]
        return fetcher.get_total_entry_count() > fetcher.page_num

    @staticmethod
    def resolve_num_pages(parent, _info):
        fetcher = parent["fetcher"]
        return fetcher.get_total_page_count()
