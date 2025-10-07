from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    def save(self, *args, **kwargs):
        self.username = self.username.lower()
        self.email = self.email.lower()
        self.first_name = self.first_name.lower()
        self.last_name = self.last_name.lower()
        super().save(*args, **kwargs)

    def full_name(self):
        if not self.first_name and not self.last_name:
            return "N/A"
        return f"{self.first_name} {self.last_name}".title()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["email"], name="uq_customuser_email"),
            models.UniqueConstraint(
                fields=["username"], name="uq_customuser_username"),
        ]
        indexes = [
            models.Index(fields=["email"], name="idx_customuser_email"),
            models.Index(fields=["username"], name="idx_customuser_username"),
        ]
