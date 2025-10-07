from .models import Category


def list_categories_public():
    return Category.objects.only("id", "name").order_by("name")


def list_categories_admin():
    return Category.objects.select_related("created_by", "updated_by").order_by("name")
