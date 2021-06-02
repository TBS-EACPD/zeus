from django.contrib.auth.models import User
from django.urls import reverse

import pytest

from django_sample.models import Author, Book


def test_edit_book_has_edited_by_prop(client):
    user = User.objects.create(username="abc")
    client.force_login(user)
    author = Author.objects.create(first_name="john")
    a_book = Book.objects.create(author=author, title="name1")
    a_book.reset_version_attrs()

    url = reverse("edit-book", args=[a_book.pk])
    client.post(url, data={"title": "name2"})

    assert a_book.versions.count() == 2
    assert a_book.versions.first().edited_by is None
    assert a_book.versions.last().edited_by == user
