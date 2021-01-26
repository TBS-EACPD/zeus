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


class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

class AuthorVersion(CustomVersionModel):
    live_model = Author

class Tag(models.Model):
    name = models.CharField(max_length=250)

class Book(models.Model):
    author = models.ForeignKey(Author, related_name="books", on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    tags = models.ManyToManyField(Tag)

class BookVersion(CustomVersionModel):
    live_model = Book