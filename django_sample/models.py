from django.conf import settings
from django.db import models
from django.utils import timezone

from zeus.versioning import VersionModel


class CustomVersionModel(VersionModel):
    class Meta:
        abstract = True
        ordering = ["business_date"]
        get_latest_by = "business_date"

    business_date = models.DateTimeField(
        default=timezone.now, verbose_name="hypothetical last edit date",
    )

    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+",
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


class Book(models.Model):
    author = models.ForeignKey(Author, related_name="books", on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    tags = models.ManyToManyField(Tag)


class BookVersion(CustomVersionModelWithEditor):
    live_model = Book
