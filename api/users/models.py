from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class CustomUser(AbstractUser):
    def save(self, *args, **kwargs):
        self.username = self.username.lower()
        self.email = self.email.lower()
        self.first_name = self.first_name.lower()
        self.last_name = self.last_name.lower()
        self.last_login = timezone.now()
        super().save(*args, **kwargs)
