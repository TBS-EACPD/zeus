from django.urls import reverse
from django.views.generic import TemplateView


class AbstractChangelogView(TemplateView):
    """
        query must contain 
            changelog(page_num,...)
                num_pages
                has_next_page
                changelog_entries {
            
                }
            }

    """

    template_name = None
    graphql_query = None
    query_executor_class = None

    @classmethod
    def as_view(cls, *args, **kwargs):
        assert cls.template_name, "must define template_name"
        assert cls.graphql_query, "must define graphql_query"
        assert cls.query_executor_class, "must define query_executor_class"
        return super().as_view(*args, **kwargs)

    def get_graphql_variables(self):
        page_num = self.kwargs.get("page_num", 1)
        return {
            "page_num": page_num,
        }

    def get_changelog_data(self):
        page_num = self.kwargs.get("page_num", 1)
        variables = self.get_graphql_variables()
        query_executor = self.query_executor_class()
        data = query_executor.execute_query(self.graphql_query, variables=variables)

        edit_entries = data["changelog"]["changelog_entries"]
        has_next_page = data["changelog"]["has_next_page"]
        num_pages = data["changelog"]["num_pages"]

        entries_without_diffs = [entry for entry in edit_entries if not entry["diffs"]]

        prev_page = None
        next_page = None

        if page_num > 1:
            prev_page = page_num - 1

        if has_next_page:
            next_page = page_num + 1

        return {
            "entries_without_diffs": entries_without_diffs,
            "edit_entries": edit_entries,
            "prev_page_num": prev_page,
            "next_page_num": next_page,
            "num_pages": num_pages,
            "page_num": page_num,
        }

    def get_context_data(self, *args, **kwargs):
        changelog_context_data = self.get_changelog_data()
        return {
            **super().get_context_data(*args, **kwargs),
            **changelog_context_data,
        }
