from django.conf import settings
from django.db import models
from django.utils import timezone

from zeus.graphql.dataloader import SingletonDataLoader
from zeus.versioning import VersionModel


class CustomVersionModel(VersionModel):
    class Meta:
        abstract = True
        ordering = ["business_date"]
        get_latest_by = "business_date"

    business_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="hypothetical last edit date",
    )

    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )


class CustomVersionModelWithEditor(CustomVersionModel):
    class Meta(CustomVersionModel.Meta):
        abstract = True

    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_DEFAULT,
        related_name="+",
    )


class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)


class AuthorVersion(CustomVersionModel):
    live_model = Author


class Tag(models.Model):
    name = models.CharField(max_length=250)

    def __str__(self):
        return self.name


class BookNameLoader(SingletonDataLoader):
    @staticmethod
    def batch_load(book_ids):
        books_with_authors = Book.objects.filter(id__in=book_ids).select_related("author")
        by_id = {b.id: b for b in books_with_authors}
        name_for_book = (
            lambda b: f"{b.title} ({b.author.first_name} {b.author.last_name})"
        )
        return [name_for_book(by_id[book_id]) for book_id in book_ids]


class Book(models.Model):

    changelog_live_name_loader_class = BookNameLoader

    author = models.ForeignKey(Author, related_name="books", on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    tags = models.ManyToManyField(Tag)


class BookVersion(CustomVersionModelWithEditor):
    live_model = Book
