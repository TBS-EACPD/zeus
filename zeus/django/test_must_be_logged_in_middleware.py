from django.contrib.auth.models import User
from django.urls import reverse

import pytest

from django_sample.models import Author, Book


@pytest.fixture
def data_url():
    author = Author.objects.create(first_name="john")
    a_book = Book.objects.create(author=author, title="name1")
    url = reverse("edit-book", args=[a_book.pk])
    return url


def test_unauthenticated_request_redirects_to_login(client, data_url):
    resp = client.get(data_url, follow=True)
    assert resp.resolver_match.url_name == "login"


def test_authenticated_request_is_ok(client, data_url):
    user = User.objects.create(username="abc")
    client.force_login(user)
    resp = client.get(data_url)
    assert resp.status_code == 200
