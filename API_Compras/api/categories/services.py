from django.db import transaction
from django.core import exceptions
from .models import Category


@transaction.atomic
def create_category(*, user, name: str) -> Category:
    """
    Crea Categoría.

    Args:
        user (User): Usuario que crea la categoría.
        name (str): Nombre de la nueva categoría.

    Raises:
        exceptions.ValidationError: Validación de existencia.

    Returns:
        dict: Respuesta estándar con información de la operación
            - success (bool): True si la operación fue exitosa
            - message (str): Mensaje descriptivo de la operación
            - data (dict): Datos de la operación
                - category (Category): Objeto de la nueva categoría creada
                - name (str): Nombre de la categoría creada
    """
    name_norm = name.strip().lower()
    # unicidad case-sensitive
    exist = Category.objects.filter(name__iexact=name_norm).exists()
    if exist:
        raise exceptions.ValidationError(
            "Ya existe una categoría con ese nombre.")
    category = Category.objects.create(
        name=name_norm,
        created_by=user,
        updated_by=user
    )
    return {
        "success": True,
        "message": f"Categoría '{name_norm}' creada exitosamente.",
        "data": {
            "category": category,
            "name": category.name
        }
    }


@transaction.atomic
def rename_category(*, user, category: Category, new_name: str) -> Category:
    """
    Actualiza el nombre de la categoría.

    Args:
        user (User): Usuario que hce la modificación.
        category (Category): Registro completo de la categoría que se va a actualizar.
        new_name (str): Nuevo nombre de la categoría.

    Raises:
        exceptions.ValidationError: Excepción a la hora de validar existencia del nuevo nombre en otra categoría

    Returns:
        dict: Respuesta estándar con información de la operación
            - success (bool): True si la operación fue exitosa
            - message (str): Mensaje descriptivo de la operación
            - data (dict): Datos de la operación
                - category (Category): Objeto de la categoría actualizada
                - old_name (str): Nombre anterior de la categoría
                - new_name (str): Nuevo nombre de la categoría
    """
    old_name = category.name
    new_name = new_name.strip().lower()
    if Category.objects.exclude(pk=category.pk).filter(name__iexact=new_name).exists():
        raise exceptions.ValidationError(
            "Ya existe otra categoría con ese nombre.")
    category.name = new_name
    category.updated_by = user
    category.save(update_fields=["name", "updated_by", "updated_at"])
    return {
        "success": True,
        "message": f"Categoría renombrada de '{old_name}' a '{new_name}' exitosamente.",
        "data": {
            "category": category,
            "old_name": old_name,
            "new_name": new_name
        }
    }
