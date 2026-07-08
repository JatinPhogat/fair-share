from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)

    USERNAME_FIELD: str = "email"
    REQUIRED_FIELDS: list[str] = ["username"]

    class Meta:
        db_table = "users"
        ordering = ["username"]

    def __str__(self) -> str:
        return self.username
