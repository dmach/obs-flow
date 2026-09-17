from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")
        user = self.model(username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.password = None
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser):
    class AccountType(models.TextChoices):
        HUMAN = "human", "Human"
        BOT = "bot", "Bot"
        SYSTEM = "system", "System"

    username = models.CharField(max_length=150, unique=True)
    username_lower = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    oidc_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    is_local_account = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    account_type = models.CharField(
        max_length=10,
        choices=AccountType.choices,
        default=AccountType.HUMAN,
    )

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_local_account=True) | models.Q(is_local_account=False, password__isnull=True),
                name="external_users_must_have_null_password"
            )
        ]

    def has_usable_password(self):
        if self.password is None:
            return False
        return super().has_usable_password()

    def check_password(self, raw_password):
        if self.password is None:
            return False
        return super().check_password(raw_password)

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
