import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class AccountType(models.TextChoices):
        HUMAN = "human", "Human"
        BOT = "bot", "Bot"
        SYSTEM = "system", "System"

    username_lower = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    oidc_sub = models.UUIDField(unique=True, null=True, blank=True)
    account_type = models.CharField(
        max_length=10,
        choices=AccountType.choices,
        default=AccountType.HUMAN,
    )

    def save(self, *args, **kwargs):
        self.username_lower = self.username.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class Group(models.Model):
    name = models.CharField(max_length=150)
    name_lower = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.name_lower = self.name.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class UserGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_groups")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="group_users")

    class Meta:
        unique_together = ("user", "group")

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"
