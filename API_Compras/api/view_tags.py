"""Utilities to standardize OpenAPI/Swagger tags across the project.

Use tags in the format: "<Category> - <Level>"
Examples: "Products - Public", "Products - Admin", "Products - Authenticated"

This module exposes small helpers that return lists suitable for both
drf-yasg (`swagger_auto_schema`) and drf-spectacular (`extend_schema`).
"""

from typing import List


def tag_name(category: str, level: str) -> str:
    """Return a single tag name following the project's convention.

    Args:
        category: High-level category name, e.g. 'Products'
        level: Sub-level like 'Public', 'Admin' or 'Authenticated'

    Returns:
        A tag string like 'Products - Public'
    """
    return f"{category} - {level}"


def tags(category: str, level: str) -> List[str]:
    """Return a list with a single tag element (convenience for decorators).

    Both drf-yasg and drf-spectacular accept a list of tag strings. Using
    this helper keeps tag names consistent across the codebase.
    """
    return [tag_name(category, level)]


def products_public() -> List[str]:
    return tags('Products', 'Public')


def products_admin() -> List[str]:
    return tags('Products', 'Admin')


def products_authenticated() -> List[str]:
    return tags('Products', 'Authenticated')


def storage_admin() -> List[str]:
    return tags('Storage Locations', 'Admin')


def promotions_public() -> List[str]:
    return tags('Promotions', 'Public')


def promotions_admin() -> List[str]:
    return tags('Promotions', 'Admin')


def purchases_status_management() -> List[str]:
    return tags('Purchases', 'Status Management')


def purchases_installments_management() -> List[str]:
    return tags('Purchases', 'Installments Management')


def purchases_discounts() -> List[str]:
    return tags('Purchases', 'Discount Management')


def purchases_admin() -> List[str]:
    return tags('Purchases', 'Admin')


def purchases_user_management() -> List[str]:
    return tags('Purchases', 'User Management')


def purchases_crud() -> List[str]:
    return tags('Purchases', 'CRUD')


def categories_public() -> List[str]:
    return tags('Categories', 'Public')


def categories_admin() -> List[str]:
    return tags('Categories', 'Admin')


def payments_public() -> List[str]:
    return tags('Payments', 'Public')


def payments_authenticated() -> List[str]:
    return tags('Payments', 'Authenticated')


def payments_admin() -> List[str]:
    return tags('Payments', 'Admin')


def payments_user_management() -> List[str]:
    return tags('Payments', 'User Management')


def inventories_admin() -> List[str]:
    return tags('Inventories', 'Admin')


def installments_user_management() -> List[str]:
    return tags('Installments', 'User Management')


def installments_admin() -> List[str]:
    return tags('Installments', 'Admin')


def notification_templates_admin() -> List[str]:
    return tags('Notification Templates', 'Admin')


def cache_admin() -> List[str]:
    return tags('Cache', 'Admin')
