from django.db import models
from django.conf import settings


class Category(models.Model):
    """_summary_

    Args:
        models (_type_): _description_
    """
    name = models.CharField(max_length=120, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="categories_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="categories_updated"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="uq_category_name")
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
