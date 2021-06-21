from django_sample.models import Author, Book, Tag
from zeus.changelog.simple_changelog import create_simple_changelog


def test_simple_changelog():
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

    changelog = create_simple_changelog(models=[Author, Book], page_size=2)

    data = changelog.get_page(1)
    edit_entries = data["changelog_entries"]
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

    assert data["has_next_page"] == True
