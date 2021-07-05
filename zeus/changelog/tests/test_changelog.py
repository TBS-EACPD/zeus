from unittest.mock import patch

import pytest
from pytest_django.asserts import assertInHTML

from django_sample.models import Author, Book, Tag

from .example_schema import QueryExecutor

base_query = QueryExecutor().build_query(
    """
    query ChangelogQuery($page_num :Int!) {
        changelog(
            page_num:$page_num,
        ){
            has_next_page
            changelog_entries {
                model_name
                version {
                    instance
                    edited_by
                }
                eternal
        
                live_name
                edit_date
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
)


def test_changelog():
    data = base_query(page_num=1)


def test_entire_graphql_changelog():
    author1 = Author.objects.create(first_name="john", last_name="smith")
    author2 = Author.objects.create(first_name="jane", last_name="smith")
    book1 = Book.objects.create(author=author1, title="john's diary")

    book1_v1 = book1.versions.last()

    # refresh a new copy of this record to avoid history-row re-use
    book1.reset_version_attrs()
    book1.title = "jane's diary"
    book1.author = author2
    book1.save()

    book1_v2 = book1.versions.last()

    with patch("zeus.changelog.graphql.util.get_changelog_page_size", lambda _: 2):
        data = base_query(page_num=1)

    edit_entries = data["changelog"]["changelog_entries"]
    assert len(edit_entries) == 2

    assert edit_entries[0]["version"]["instance"] == book1_v2
    assert len(edit_entries[0]["diffs"]) == 2
    diffs_by_fields = {diff["field_name"]: diff for diff in edit_entries[0]["diffs"]}

    # field-diffs might come in any order
    assert set(diffs_by_fields.keys()) == {
        "title",
        "author",
    }
    # they have field objects as well
    assert diffs_by_fields["title"]["field"] == Book._meta.get_field("title")

    assert edit_entries[1]["version"]["instance"] == book1_v1

    # this field returns a tm() result
    assert edit_entries[1]["diffs"][0]["action"] == "Created"

    assert edit_entries[0]["eternal"] == edit_entries[1]["eternal"] == book1
    assert edit_entries[0]["model_name"] == "book"

    assert data["changelog"]["has_next_page"] == True


def test_m2m_entries():
    t1 = Tag.objects.create(name="Tag1")
    t2 = Tag.objects.create(name="Tag2")
    t3 = Tag.objects.create(name="Tag3")

    book = Book.objects.create(
        author=Author.objects.create(first_name="john", last_name="smith"),
        title="john's diary",
    )
    book.tags.add(t1, t2)

    book_v1 = book.versions.last()
    book.reset_version_attrs()

    book.tags.add(t3)
    book.tags.remove(t1)
    book.save()

    book_v2 = book.versions.last()
    data = base_query(page_num=1)
    edit_entries = data["changelog"]["changelog_entries"]
    assert len(edit_entries) == 3

    assert edit_entries[0]["version"]["instance"] == book_v2
    assert len(edit_entries[0]["diffs"]) == 1

    m2m_diff = edit_entries[0]["diffs"][0]
    assert m2m_diff["action"] == "Edited"
    assert m2m_diff["field_name"] == "tags"
    # non-added/removed tag show up without class in both before/after
    assertInHTML("<p class=''>Tag2</p>", m2m_diff["diffed_before"])
    assertInHTML("<p class=''>Tag2</p>", m2m_diff["diffed_after"])

    assertInHTML("<p class='diff_sub'>Tag1</p>", m2m_diff["diffed_before"])
    assertInHTML("<p class='diff_add'>Tag3</p>", m2m_diff["diffed_after"])

    assertInHTML("<p class=''>Tag2</p>", m2m_diff["diffed_combined"])
    assertInHTML("<p class='diff_sub'>Tag1</p>", m2m_diff["diffed_combined"])
    assertInHTML("<p class='diff_add'>Tag3</p>", m2m_diff["diffed_combined"])
