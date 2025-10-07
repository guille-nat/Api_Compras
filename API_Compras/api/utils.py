from .models import NotificationTemplate
from django.shortcuts import get_object_or_404


def validate_id(id: int, name: str = "ID") -> None:
    if id is None or not isinstance(id, int) or id <= 0:
        raise ValueError(f"{name} ID must be a positive integer")


def get_notification_by_code(code: str) -> NotificationTemplate:
    if not code or not isinstance(code, str):
        raise ValueError("Code must be a non-empty string")
    return get_object_or_404(NotificationTemplate, code=code, active=True)
