from collections import defaultdict

import pytest
from promise import Promise

from django_sample.data_factories import AuthorFactory, BookFactory, TagFactory
from django_sample.models import Book, Tag
from zeus.django.query_counting import assert_max_queries
from zeus.graphql.dataloader import PrimaryKeyDataLoaderFactory, SingletonDataLoader
from zeus.vanilla import flatten, group_by


def test_pk_loader_factory(dataloader_test):
    b1 = BookFactory()
    b2 = BookFactory()
    dataloader_cache = {}
    BookLoaderCls = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(Book)
    with assert_max_queries(0):
        book1_prom = BookLoaderCls(dataloader_cache).load(b1.pk)
        book2_prom = BookLoaderCls(dataloader_cache).load(b2.pk)

    with assert_max_queries(1):
        resolved_b1, resolved_b2 = Promise.all([book1_prom, book2_prom]).get()

        assert b1 == resolved_b1
        assert b2 == resolved_b2


class BooksForAuthorLoader(SingletonDataLoader):
    def batch_load(self, author_ids):
        books = Book.objects.filter(author_id__in=author_ids)
        by_author = group_by(books, lambda b: b.author_id)
        return [by_author.get(id, []) for id in author_ids]


class TagsForBookLoader(SingletonDataLoader):
    def batch_load(self, book_ids):
        books = Book.objects.filter(id__in=book_ids).prefetch_related("tags")
        by_id = defaultdict(list)
        for b in books:
            by_id[b.id].extend(b.tags.all())

        return [by_id.get(id) for id in book_ids]


class TagsForAuthorLoader(SingletonDataLoader):
    def batch_load(self, author_ids):
        book_groups = yield BooksForAuthorLoader(
            self.dataloader_instance_cache
        ).load_many(author_ids)
        books = flatten(book_groups)
        book_ids_by_author = group_by(books, lambda b: b.author_id)
        book_ids = [b.id for b in books]

        tag_groups = yield TagsForBookLoader(self.dataloader_instance_cache).load_many(
            book_ids
        )
        tags_by_book_id = dict(zip(book_ids, tag_groups))

        tags_by_author_id = defaultdict(set)
        for b in books:
            tags = tags_by_book_id[b.id]
            tags_by_author_id[b.author_id].update(tags)

        return [tags_by_author_id[id] for id in author_ids]


def test_composed_dataloader(dataloader_test):
    a1 = AuthorFactory()
    a2 = AuthorFactory()
    a3 = AuthorFactory()

    t1 = TagFactory()
    t2 = TagFactory()
    t3 = TagFactory()

    b1_1 = BookFactory(author=a1, tags=[t1, t3])
    b1_2 = BookFactory(author=a1)
    b2_1 = BookFactory(author=a2, tags=[t2])
    b2_2 = BookFactory(author=a2, tags=[t1])

    dataloader_cache = {}

    with assert_max_queries(0):
        a1_prom = TagsForAuthorLoader(dataloader_cache).load(a1.pk)
        a2_prom = TagsForAuthorLoader(dataloader_cache).load(a2.pk)
        a3_prom = TagsForAuthorLoader(dataloader_cache).load(a3.pk)

    with assert_max_queries(3):
        resolved_a1, resolved_a2, resolved_a3 = Promise.all(
            [a1_prom, a2_prom, a3_prom]
        ).get()

        assert resolved_a1 == {t1, t3}
        assert resolved_a2 == {t1, t2}
        assert resolved_a3 == set()
