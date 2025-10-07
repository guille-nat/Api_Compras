from django.db import transaction
from django.core import exceptions
from .models import Category
from api.promotions.services import get_active_promotions_category
from api.promotions.models import Promotion, PromotionRule, PromotionScopeCategory
from django.utils import timezone
from django.db import models


@transaction.atomic
def create_category(*, user, name: str) -> dict:
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
        "data": category
    }


@transaction.atomic
def rename_category(*, user, category: Category, new_name: str) -> dict:
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


def get_all_categories_with_promotions() -> dict:
    """
    Obtiene todas las categorías con sus promociones activas y reglas vigentes asociadas.

    Recupera todas las categorías del sistema junto con sus promociones activas
    y reglas vigentes de forma optimizada, evitando el problema N+1 mediante
    estrategia de consultas separadas con select_related y prefetch_related.
    Estructura los datos para facilitar su uso en APIs y interfaces de usuario,
    incluyendo categorías sin promociones asociadas.

    Proceso:
        - Ejecuta consulta optimizada para obtener todas las categorías
        - Pre-carga promociones activas mediante tabla intermedia PromotionScopeCategory
        - Pre-carga reglas vigentes de cada promoción (filtradas por fechas)
        - Agrupa datos en memoria para evitar consultas N+1
        - Estructura los datos en formato diccionario para fácil consumo

    Optimizaciones aplicadas:
        - select_related para relaciones ForeignKey (promotion, category)
        - prefetch_related para relaciones inversas 1:N (promotion → rules)
        - Filtrado temporal en base de datos usando timezone.now()
        - Agrupación en memoria con diccionario para acceso O(1)
        - Estructura de datos eficiente para serialización

    Validaciones realizadas:
        - Filtrado automático por promociones activas (promotion__active=True)
        - Filtrado temporal de reglas vigentes (start_at <= now <= end_at)
        - Manejo seguro de categorías sin promociones asociadas
        - Inclusión de todas las categorías independientemente de promociones

    Returns:
        dict: Respuesta estándar con información de la operación
            - success (bool): True si la operación fue exitosa
            - message (str): Mensaje descriptivo de la operación
            - data (list): Lista de categorías con sus promociones activas y reglas vigentes
                - category (dict): Datos de la categoría
                    - id (int): ID de la categoría
                    - name (str): Nombre de la categoría
                - active_promotions (list): Lista de promociones activas asociadas a la categoría
                    - id (int): ID de la promoción
                    - name (str): Nombre de la promoción
                    - active (bool): Estado activo de la promoción
                    - rules (list): Lista de reglas vigentes asociadas a la promoción
                        - id (int): ID de la regla
                        - type (str): Tipo de regla
                        - value (Decimal): Valor de la regla
                        - priority (int): Prioridad de la regla
                        - start_at (datetime): Fecha y hora de inicio de la regla
                        - end_at (datetime): Fecha y hora de fin de la regla
                        - acumulable (bool): Indica si la regla es acumulable con otras

    """

    # 1. Obtener todas las categorías (sin filtros para incluir todas)
    categories = Category.objects.all()

    # 2. Crear diccionario para mapear promociones por categoría
    promotions_by_category = {}

    # 3. Consulta optimizada usando select_related y prefetch_related correctamente
    promotions_scopes = PromotionScopeCategory.objects.select_related(
        'promotion',  # ForeignKey - usar select_related para JOIN en SQL
        'category'    # ForeignKey - usar select_related para JOIN en SQL
    ).prefetch_related(
        models.Prefetch(
            'promotion__promotionrule_set',  # Relación inversa 1:N - usar prefetch_related
            queryset=PromotionRule.objects.filter(
                start_at__lte=timezone.now(),
                end_at__gte=timezone.now()
            ),
            to_attr='active_rules'  # Almacenar en atributo personalizado
        )
    ).filter(
        promotion__active=True  # Solo promociones activas
    )

    # 4. Agrupar promociones por categoría ID para acceso O(1)
    for promo_scope in promotions_scopes:
        category_id = promo_scope.category.pk
        if category_id not in promotions_by_category:
            promotions_by_category[category_id] = []
        promotions_by_category[category_id].append(promo_scope.promotion)

    # 5. Construir resultado final con todas las categorías
    categories_with_promotions = []
    for category in categories:
        # Obtener promociones de la categoría (si existen)
        category_promotions = promotions_by_category.get(category.pk, [])

        # Inicializar lista de promociones activas
        active_promotions = []

        # Procesar promociones si existen
        for promotion in category_promotions:
            promotion_data = {
                'id': promotion.pk,
                'name': promotion.name,
                'active': promotion.active,
                'rules': []
            }

            # Estructurar reglas vigentes (ya pre-cargadas y filtradas en to_attr)
            for rule in promotion.active_rules:  # Usar el to_attr personalizado
                rule_data = {
                    'id': rule.pk,
                    'type': rule.type,
                    'value': rule.value,
                    'priority': rule.priority,
                    'start_at': rule.start_at,
                    'end_at': rule.end_at,
                    'acumulable': rule.acumulable
                }
                promotion_data['rules'].append(rule_data)

            active_promotions.append(promotion_data)

        category_data = {
            'id': category.pk,
            'name': category.name,
        }

        # Agregar categoría al resultado (con o sin promociones)
        categories_with_promotions.append({
            'category': category_data,
            'active_promotions': active_promotions  # Lista vacía si no hay promociones
        })

    return {"success": True,
            "message": "Categories retrieved successfully.",
            "data": categories_with_promotions
            }
