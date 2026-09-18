from django.db import models
from django.conf import settings


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=2000)

    class Meta:
        ordering = ["name"]
        unique_together = ("user", "name")

    def __str__(self):
        return f"{self.user.username}: {self.name} -> {self.url}"
