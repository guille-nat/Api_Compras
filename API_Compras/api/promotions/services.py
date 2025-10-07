from django.db import transaction, models
from django.contrib.auth import get_user_model
from .models import Promotion, PromotionRule, PromotionScopeCategory, PromotionScopeProduct, PromotionScopeLocation
from api.storage_location.models import StorageLocation as Location
from api.products.models import Category
from api.products.models import Product
from api.inventories.models import InventoryRecord
from decimal import Decimal
from datetime import datetime, date
from api.utils import validate_id
from django.utils import timezone
from django.shortcuts import get_object_or_404


# === Funciones de creación ===#

@transaction.atomic
def create_promotion(name: str, active: bool, user_id: int) -> Promotion:
    """
    Crea una nueva promoción en el sistema de forma transaccional.

    Permite la creación de promociones validando los datos de entrada,
    normalizando el nombre y verificando la unicidad del mismo. La operación
    se ejecuta dentro de una transacción atómica para garantizar la consistencia
    de datos en caso de errores.

    Args:
        name (str): Nombre de la promoción
            Debe ser una cadena no vacía con máximo 180 caracteres
            Se normaliza automáticamente (strip + lowercase)
        active (bool): Estado de activación de la promoción
            True para activa, False para inactiva
        user_id (int): ID del usuario que crea la promoción
            Debe ser un entero positivo mayor a 0

    Returns:
        Promotion: Instancia de la promoción creada con los datos persistidos

    Raises:
        ValueError: Cuando los parámetros son inválidos o faltan datos requeridos
            - Parámetros name o user_id son None
            - active no es booleano
            - name no es string válido o excede 180 caracteres
            - user_id no es entero positivo
            - Ya existe una promoción con el mismo nombre

    """
    if name is None or user_id is None:
        raise ValueError("Name and user must be provided")

    if not isinstance(active, bool):
        raise ValueError("Active status must be a boolean")

    if not isinstance(name, str):
        raise ValueError("Name must be a string")

    name_normalized = name.strip().lower()
    if len(name_normalized) == 0 or len(name_normalized) > 180:
        raise ValueError(
            "Name must be a non-empty string with a maximum length of 180 characters")

    validate_id(user_id, "User")

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise ValueError("User not found")
    try:
        existing_promotion = Promotion.objects.get(name=name_normalized)
        raise ValueError("A promotion with this name already exists")
    except Promotion.DoesNotExist:
        pass

    promotion = Promotion.objects.create(
        name=name_normalized,
        active=active,
        created_by=user
    )
    return promotion


@transaction.atomic
def create_rule(promotion_id: int, type: str, value: Decimal, priority: int,
                start_date: date, end_date: date, acumulable: bool, user_id: int) -> PromotionRule:
    """
    Crea una nueva regla de promoción asociada a una promoción existente.

    Permite la creación de reglas que definen el comportamiento y condiciones
    de aplicación de una promoción. Valida todos los parámetros de entrada,
    verifica la existencia de la promoción padre y garantiza la consistencia
    temporal de las fechas.

    Args:
        promotion_id (int): ID de la promoción padre
            Debe ser un entero positivo y corresponder a una promoción existente
        type (str): Tipo de regla de promoción
            Debe ser uno de los valores válidos en PromotionRule.Type.values
        value (Decimal): Valor asociado a la regla
            Debe ser un Decimal no negativo (ej: porcentaje de descuento)
        priority (int): Prioridad de aplicación de la regla
            Debe ser un entero no negativo, mayor prioridad = mayor precedencia
        start_date (date): Fecha de inicio de vigencia de la regla
            Debe ser una fecha válida
        end_date (date): Fecha de fin de vigencia de la regla
            Debe ser una fecha válida posterior a start_date
        acumulable (bool): Indica si la regla es acumulable con otras reglas
        user_id (int): ID del usuario que crea la regla
            Debe ser un entero positivo mayor a 0

    Returns:
        PromotionRule: Instancia de la regla de promoción creada

    Raises:
        ValueError: Cuando los parámetros son inválidos
            - promotion_id no es entero positivo o promoción no existe
            - type no es string válido o no está en valores permitidos
            - value no es Decimal no negativo
            - priority no es entero no negativo
            - fechas inválidas o end_date <= start_date
            - user_id no es entero positivo

    """
    validate_id(promotion_id, "Promotion")
    validate_id(user_id, "User")

    if (type is None or not isinstance(type, str) or
            len(type.strip()) == 0 or type not in PromotionRule.Type.values):
        raise ValueError(
            f"Type must be one of the following: {', '.join(PromotionRule.Type.values)}")

    if value is None or not isinstance(value, Decimal) or value < 0:
        raise ValueError("Value must be a non-negative decimal")

    if priority is None or not isinstance(priority, int) or priority < 0:
        raise ValueError("Priority must be a non-negative integer")

    if start_date is None or not isinstance(start_date, date):
        raise ValueError("Start date must be a valid date")

    if (end_date is None or not isinstance(end_date, date) or
            end_date <= start_date):
        raise ValueError(
            "End date must be a valid date and after the start date")
    if acumulable is None or not isinstance(acumulable, bool):
        raise ValueError("Acumulable must be a boolean")

    try:
        promotion = Promotion.objects.get(id=promotion_id)
    except Promotion.DoesNotExist:
        raise ValueError("Promotion not found")

    tz = timezone.get_current_timezone()
    exact_start_datetime = timezone.make_aware(
        datetime.combine(start_date, datetime.min.time()), tz)
    exact_end_datetime = timezone.make_aware(
        datetime.combine(end_date, datetime.max.time()), tz)

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise ValueError("User not found")

    rule = PromotionRule.objects.create(
        promotion=promotion,
        type=type,
        value=value,
        priority=priority,
        start_at=exact_start_datetime,
        end_at=exact_end_datetime,
        acumulable=acumulable,
        created_by=user
    )
    return rule


@transaction.atomic
def create_promotion_category(promotion_id: int, category_id: int, user_id: int) -> PromotionScopeCategory:
    """
    Asocia una categoría a una promoción para definir su alcance de aplicación.

    Permite establecer el alcance de una promoción a nivel de categoría de productos,
    validando la existencia de ambas entidades y verificando que no exista una
    asociación previa entre la promoción y la categoría.

    Args:
        promotion_id (int): ID de la promoción
            Debe ser un entero positivo y corresponder a una promoción existente
        category_id (int): ID de la categoría
            Debe ser un entero positivo y corresponder a una categoría existente
        user_id (int): ID del usuario que crea la asociación
            Debe ser un entero positivo mayor a 0

    Returns:
        PromotionScopeCategory: Instancia de la asociación promoción-categoría creada

    Raises:
        ValueError: Cuando los parámetros son inválidos o las entidades no existen
            - promotion_id no es entero positivo
            - category_id no es entero positivo
            - user_id no es entero positivo
            - Promoción no encontrada
            - Categoría no encontrada
            - Ya existe asociación entre promoción y categoría
    """
    validate_id(promotion_id, "Promotion")
    validate_id(user_id, "User")
    validate_id(category_id, "Category")

    try:
        promotion = Promotion.objects.get(id=promotion_id)
    except Promotion.DoesNotExist:
        raise ValueError("Promotion not found")

    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        raise ValueError("Category not found")

    try:
        existing_promotion_category = PromotionScopeCategory.objects.get(
            promotion=promotion, category=category)
        raise ValueError(
            "This category is already associated with the promotion")
    except PromotionScopeCategory.DoesNotExist:
        pass

    # resolve user instance
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise ValueError("User not found")

    promotion_category = PromotionScopeCategory.objects.create(
        promotion=promotion,
        category=category,
        created_by=user
    )
    return promotion_category


@transaction.atomic
def create_promotion_product(promotion_id: int, product_id: int, user_id: int) -> PromotionScopeProduct:
    """
    Asocia un producto específico a una promoción para definir su alcance de aplicación.

    Permite establecer el alcance de una promoción a nivel de producto individual,
    validando la existencia de ambas entidades y verificando que no exista una
    asociación previa entre la promoción y el producto.

    Args:
        promotion_id (int): ID de la promoción
            Debe ser un entero positivo y corresponder a una promoción existente
        product_id (int): ID del producto
            Debe ser un entero positivo y corresponder a un producto existente
        user_id (int): ID del usuario que crea la asociación
            Debe ser un entero positivo mayor a 0

    Returns:
        PromotionScopeProduct: Instancia de la asociación promoción-producto creada

    Raises:
        ValueError: Cuando los parámetros son inválidos o las entidades no existen
            - promotion_id no es entero positivo
            - product_id no es entero positivo
            - user_id no es entero positivo
            - Promoción no encontrada
            - Producto no encontrado
            - Ya existe asociación entre promoción y producto
    """
    validate_id(promotion_id, "Promotion")
    validate_id(product_id, "Product")
    validate_id(user_id, "User")

    try:
        promotion = Promotion.objects.get(id=promotion_id)
    except Promotion.DoesNotExist:
        raise ValueError("Promotion not found")

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise ValueError("Product not found")

    try:
        existing_promotion_product = PromotionScopeProduct.objects.get(
            promotion=promotion, product=product)
        raise ValueError(
            "This product is already associated with the promotion")
    except PromotionScopeProduct.DoesNotExist:  # Corregido: era Promotion.DoesNotExist
        pass

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise ValueError("User not found")

    promotion_product = PromotionScopeProduct.objects.create(
        promotion=promotion,
        product=product,
        created_by=user
    )
    return promotion_product


@transaction.atomic
def create_promotion_location(promotion_id: int, location_id: int, user_id: int) -> PromotionScopeLocation:
    """
    Asocia una ubicación de almacenamiento a una promoción para definir su alcance geográfico.

    Permite establecer el alcance de una promoción a nivel de ubicación específica,
    validando la existencia de ambas entidades y verificando que no exista una
    asociación previa entre la promoción y la ubicación.
    Args:
        promotion_id (int): ID de la promoción
            Debe ser un entero positivo y corresponder a una promoción existente
        location_id (int): ID de la ubicación de almacenamiento
            Debe ser un entero positivo y corresponder a una ubicación existente
        user_id (int): ID del usuario que crea la asociación
            Debe ser un entero positivo mayor a 0

    Returns:
        PromotionScopeLocation: Instancia de la asociación promoción-ubicación creada

    Raises:
        ValueError: Cuando los parámetros son inválidos o las entidades no existen
            - promotion_id no es entero positivo
            - location_id no es entero positivo
            - user_id no es entero positivo
            - Promoción no encontrada
            - Ubicación no encontrada
            - Ya existe asociación entre promoción y ubicación

    """

    validate_id(promotion_id, "Promotion")
    validate_id(user_id, "User")
    validate_id(location_id, "Location")

    try:
        promotion = Promotion.objects.get(id=promotion_id)
    except Promotion.DoesNotExist:
        raise ValueError("Promotion not found")

    try:
        location = Location.objects.get(id=location_id)
    except Location.DoesNotExist:
        raise ValueError("Location not found")

    try:
        existing_promotion_location = PromotionScopeLocation.objects.get(
            promotion=promotion, location=location)
        raise ValueError(
            "This location is already associated with the promotion")
    except PromotionScopeLocation.DoesNotExist:
        pass

    # resolve user instance
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise ValueError("User not found")

    promotion_location = PromotionScopeLocation.objects.create(
        promotion=promotion,
        location=location,
        created_by=user
    )
    return promotion_location


@transaction.atomic
def create_promotion_and_rule(data: dict, user_id: int) -> dict:
    """
    Crea una promoción completa con su regla y alcances asociados de forma transaccional.

    Función de alto nivel que orquesta la creación de una promoción completa incluyendo
    la promoción base, su regla de aplicación y los alcances específicos (categorías,
    productos o ubicaciones). Todas las operaciones se ejecutan dentro de una transacción
    atómica para garantizar consistencia de datos.

    Args:
        data (dict): Diccionario con datos de la promoción y regla
            Campos requeridos:
            - name (str): Nombre de la promoción
            - type (str): Tipo de regla (valores válidos en PromotionRule.Type)
            - value (str/Decimal): Valor de la regla
            - start_date (str): Fecha de inicio en formato 'YYYY-MM-DD'
            - end_date (str): Fecha de fin en formato 'YYYY-MM-DD'

            Campos opcionales:
            - active (bool): Estado de la promoción, default True
            - priority (int): Prioridad de la regla, default 0
            - acumulable (bool): Si la regla es acumulable, default False
            - categories_ids (list[int]): Lista de IDs de categorías
            - products_ids (list[int]): Lista de IDs de productos
            - locations_ids (list[int]): Lista de IDs de ubicaciones

        user_id (int): ID del usuario que crea la promoción
            Debe ser un entero positivo mayor a 0

    Returns:
        dict: Estructura completa con promoción, regla y alcances creados
            {
                "promotion": {
                    "id": int, "name": str, "active": bool,
                    "created_at": datetime, "updated_at": datetime
                },
                "rule": {
                    "id": int, "type": str, "value": Decimal, "priority": int,
                    "start_date": datetime, "end_date": datetime, "acumulable": bool,
                    "created_at": datetime, "updated_at": datetime
                },
                "categories": list[PromotionScopeCategory] | {},
                "products": list[PromotionScopeProduct] | {},
                "locations": list[PromotionScopeLocation] | {}
            }

    Raises:
        ValueError: Cuando los datos de entrada son inválidos
            - data no es diccionario válido o está vacío
            - Faltan campos requeridos
            - Formato de fechas inválido
            - user_id no es entero positivo
            - Errores propagados desde funciones create_* individuales

        DatabaseError: Por errores de base de datos durante las operaciones
        IntegrityError: Por violaciones de restricciones de integridad

    """
    # Validaciones de entrada
    if not isinstance(data, dict) or not data:
        raise ValueError("Data must be a non-empty dictionary")

    validate_id(user_id, "User")

    # Validar campos requeridos
    required_fields = ['name', 'type', 'value', 'start_date', 'end_date']
    missing_fields = [
        field for field in required_fields if not data.get(field)]
    if missing_fields:
        raise ValueError(
            f"Missing required fields: {', '.join(missing_fields)}")

    # Crear promoción base
    promotion = create_promotion(
        name=str(data['name']),
        active=bool(data.get('active', True)),
        user_id=user_id
    )

    try:
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    except ValueError as e:
        raise ValueError(f"Invalid date format. Expected YYYY-MM-DD: {str(e)}")

    rule = create_rule(
        promotion_id=promotion.pk,
        type=str(data['type']),
        value=Decimal(str(data['value'])),
        priority=int(data.get('priority', 0)),
        start_date=start_date,
        end_date=end_date,
        acumulable=bool(data.get('acumulable', False)),
        user_id=user_id
    )

    scope_results = _process_promotion_scopes(
        promotion_id=promotion.pk,
        categories_ids=data.get('categories_ids', []),
        products_ids=data.get('products_ids', []),
        locations_ids=data.get('locations_ids', []),
        user_id=user_id
    )

    response = {
        "promotion": {
            "id": promotion.pk,
            "name": promotion.name,
            "active": promotion.active,
            "created_at": promotion.created_at,
            "updated_at": promotion.updated_at
        },
        "rule": {
            "id": rule.pk,
            "type": rule.type,
            "value": rule.value,
            "priority": rule.priority,
            "start_date": rule.start_at,
            "end_date": rule.end_at,
            "acumulable": rule.acumulable,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at
        },
        **scope_results
    }

    return response


def _process_promotion_scopes(promotion_id: int, categories_ids: list,
                              products_ids: list, locations_ids: list,
                              user_id: int) -> dict:
    """
    Procesa y crea los alcances (scopes) de una promoción de forma optimizada.

    Función auxiliar que maneja la creación de alcances múltiples para una promoción,
    permitiendo asociar categorías, productos y ubicaciones simultáneamente.
    Optimiza la creación mediante validación previa de IDs y manejo eficiente de errores.

    Args:
        promotion_id (int): ID de la promoción a asociar
        categories_ids (list): Lista de IDs de categorías
        products_ids (list): Lista de IDs de productos
        locations_ids (list): Lista de IDs de ubicaciones
        user_id (int): ID del usuario que crea las asociaciones

    Returns:
        dict: Diccionario con los alcances creados
            {
                "categories": list[PromotionScopeCategory] | {},
                "products": list[PromotionScopeProduct] | {},
                "locations": list[PromotionScopeLocation] | {}
            }
    """
    result = {
        'categories': {},
        'products': {},
        'locations': {}
    }

    if categories_ids:
        category_scopes = []
        for category_id in categories_ids:
            scope = create_promotion_category(
                promotion_id=promotion_id,
                category_id=int(category_id),
                user_id=user_id
            )
            category_scopes.append(scope)
        result['categories'] = category_scopes

    elif products_ids:
        product_scopes = []
        for product_id in products_ids:
            scope = create_promotion_product(
                promotion_id=promotion_id,
                product_id=int(product_id),
                user_id=user_id
            )
            product_scopes.append(scope)
        result['products'] = product_scopes

    elif locations_ids:
        location_scopes = []
        for location_id in locations_ids:
            scope = create_promotion_location(
                promotion_id=promotion_id,
                location_id=int(location_id),
                user_id=user_id
            )
            location_scopes.append(scope)
        result['locations'] = location_scopes

    return result


@transaction.atomic
def auto_deactivate_expired_promotions() -> int:
    """
    Desactiva automáticamente promociones cuyas reglas han expirado.

    Función utilitaria para mantenimiento automático del sistema que identifica
    promociones activas con reglas expiradas y las desactiva para mantener la
    consistencia del estado de promociones. Utiliza transacciones atómicas para
    garantizar la integridad de datos durante las actualizaciones masivas.

    Returns:
        int: Número de promociones que fueron desactivadas
            0 si no hay promociones expiradas
            >0 indica la cantidad de promociones desactivadas

    Raises:
        DatabaseError: Por errores de conexión o transaccionales durante las actualizaciones
        IntegrityError: Por violaciones de restricciones de base de datos

    Notes:
        Esta función está diseñada para ser ejecutada por tareas programadas
        (cron jobs, Celery tasks) o como parte de procesos de mantenimiento
        automático del sistema. Se recomienda ejecutar periódicamente para
        mantener la consistencia del estado de promociones.
    """
    now = timezone.now()
    expired_rules = PromotionRule.objects.select_for_update().filter(
        end_at__lt=now, promotion__active=True)
    affected_promotions = set()
    for rule in expired_rules:
        affected_promotions.add(rule.promotion)
    for promotion in affected_promotions:
        promotion.active = False
        promotion.save()
    return len(affected_promotions)


@transaction.atomic
def update_promotion(promotion_id: int, user_id: int, name: str | None = None, active: bool | None = None) -> dict:
    """
    Actualiza los campos modificables de una promoción existente de forma transaccional.

    Permite la actualización selectiva de los campos name y active de una promoción,
    validando los datos de entrada, verificando cambios reales y aplicando normalización
    cuando corresponda. La operación se ejecuta dentro de una transacción atómica para
    garantizar consistencia de datos.

    Args:
        promotion_id (int): ID de la promoción a actualizar
            Debe ser un entero positivo correspondiente a una promoción existente
        user_id (int): ID del usuario que realiza la actualización
            Debe ser un entero positivo mayor a 0, se registra para auditoría
        name (str | None, optional): Nuevo nombre para la promoción
            Si se proporciona debe ser string válido (1-180 chars después de normalización)
            Se normaliza automáticamente (strip + lowercase) antes de comparar y guardar
            None para mantener el nombre actual sin cambios
        active (bool | None, optional): Nuevo estado de activación
            True para activar, False para desactivar, None para mantener estado actual

    Returns:
        dict: Estructura con resultado de la actualización según estándares del proyecto
            {
                "success": bool,
                "message": str,
                "data": {
                    "data": {
                        "id": int,
                        "name": str,
                        "active": bool,
                        "created_at": datetime,
                        "updated_at": datetime,
                        "updated_by": int
                    }
                }
            }

    Raises:
        ValueError: Cuando los parámetros son inválidos o no hay cambios a realizar
            - promotion_id no es entero positivo
            - user_id no es entero positivo
            - name no es string válido o excede límites después de normalización
            - active no es booleano cuando se proporciona
            - No se detectan cambios reales en los valores proporcionados
            - Ya existe otra promoción con el mismo nombre normalizado

        Http404: Cuando la promoción especificada no existe
            Propagado desde get_object_or_404() siguiendo patrones de Django
    """
    validate_id(promotion_id, "Promotion")
    validate_id(user_id, "User")
    if name is not None and not isinstance(name, str):
        raise ValueError("Name must be a string")
    if active is not None and not isinstance(active, bool):
        raise ValueError("Active must be a boolean")
    if name is None and active is None:
        raise ValueError("At least one field to update must be provided")

    promotion = Promotion.objects.select_for_update().filter(id=promotion_id).first()
    if promotion is None:
        raise ValueError("Promotion not found")

    changes_made = False
    update_fields = []

    if name is not None:
        name_normalized = name.strip().lower()

        if len(name_normalized) == 0 or len(name_normalized) > 180:
            raise ValueError(
                "Name must be a non-empty string with a maximum length of 180 characters"
            )

        if promotion.name != name_normalized:
            if Promotion.objects.filter(name=name_normalized).exclude(id=promotion_id).exists():
                raise ValueError(
                    "A promotion with this name already exists")

            promotion.name = name_normalized
            update_fields.append('name')
            changes_made = True

    if active is not None:
        if promotion.active != active:
            promotion.active = active
            update_fields.append('active')
            changes_made = True

    if not changes_made:
        raise ValueError(
            "No changes detected. All provided values are the same as current values")

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise ValueError("User not found")

    promotion.updated_by = user
    update_fields.extend(['updated_by', 'updated_at'])
    promotion.save(update_fields=update_fields)

    promotion.refresh_from_db()

    response = {
        "success": True,
        "message": "Promotion updated successfully",
        "data": {
            "id": promotion.pk,
            "name": promotion.name,
            "active": promotion.active,
            "created_at": promotion.created_at,
            "updated_at": promotion.updated_at
        }
    }
    return response


@transaction.atomic
def update_rule(rule_id: int, user_id: int, type: str | None = None, value: Decimal | None = None,
                priority: int | None = None, start_date: date | None = None, end_date: date | None = None,
                acumulable: bool | None = None) -> dict:
    """
    Actualiza los campos modificables de una regla de promoción existente de forma transaccional.

    Permite la actualización selectiva de cualquier campo de una regla de promoción,
    validando los datos de entrada, verificando cambios reales y manteniendo la consistencia
    temporal entre fechas. La operación se ejecuta dentro de una transacción atómica para
    garantizar consistencia de datos durante la actualización.

    Args:
        rule_id (int): ID de la regla de promoción a actualizar
            Debe ser un entero positivo correspondiente a una regla existente
        user_id (int): ID del usuario que realiza la actualización
            Debe ser un entero positivo mayor a 0, se registra para auditoría
        type (str | None, optional): Nuevo tipo de regla de promoción
            Debe ser uno de los valores válidos en PromotionRule.Type.values
            None para mantener el tipo actual sin cambios
        value (Decimal | None, optional): Nuevo valor asociado a la regla
            Debe ser un Decimal no negativo (ej: porcentaje, monto fijo)
            None para mantener el valor actual sin cambios
        priority (int | None, optional): Nueva prioridad de aplicación
            Debe ser un entero no negativo, mayor número = mayor prioridad
            None para mantener la prioridad actual sin cambios
        start_date (date | None, optional): Nueva fecha de inicio de vigencia
            Debe ser una instancia date válida
            None para mantener la fecha actual sin cambios
        end_date (date | None, optional): Nueva fecha de fin de vigencia
            Debe ser una instancia date válida
            None para mantener la fecha actual sin cambios
        acumulable (bool | None, optional): Nuevo estado de acumulabilidad
            True si es acumulable con otras reglas, False si no
            None para mantener el estado actual sin cambios

    Returns:
        dict: Estructura con resultado de la actualización según estándares del proyecto
            {
                "success": bool,
                "message": str,
                "data": {
                    "rule": {
                        "id": int,
                        "type": str,
                        "value": Decimal,
                        "priority": int,
                        "start_at": datetime,
                        "end_at": datetime,
                        "acumulable": bool,
                        "updated_by": int,
                        "updated_at": datetime
                    }
                }
            }

    Raises:
        ValueError: Cuando los parámetros son inválidos o no hay cambios a realizar
            - rule_id no es entero positivo
            - user_id no es entero positivo
            - type no es string válido o no está en valores permitidos
            - value no es Decimal no negativo cuando se proporciona
            - priority no es entero no negativo cuando se proporciona
            - start_date o end_date no son instancias date válidas cuando se proporcionan
            - acumulable no es booleano cuando se proporciona
            - No se detectan cambios reales en los valores proporcionados

        Http404: Cuando la regla especificada no existe
            Propagado desde get_object_or_404() siguiendo patrones de Django

    Notes:
        Esta función sigue las mejores prácticas de Django ORM utilizando update_fields
        para optimizar las operaciones de base de datos, actualizando solo los campos
        que realmente han cambiado según la documentación oficial de Django.
    """

    validate_id(rule_id, "Rule")
    validate_id(user_id, "User")

    if type is not None and (not isinstance(type, str) or type not in PromotionRule.Type.values):
        raise ValueError(
            f"Type must be one of the following: {', '.join(PromotionRule.Type.values)}")

    if value is not None and (not isinstance(value, Decimal) or value < 0):
        raise ValueError("Value must be a non-negative Decimal")

    if priority is not None and (not isinstance(priority, int) or priority < 0):
        raise ValueError("Priority must be a non-negative integer")

    if start_date is not None and not isinstance(start_date, date):
        raise ValueError("Start date must be a date")

    if end_date is not None and not isinstance(end_date, date):
        raise ValueError("End date must be a date")

    if acumulable is not None and not isinstance(acumulable, bool):
        raise ValueError("Acumulable must be a boolean")

    if all(param is None for param in [type, value, priority, start_date, end_date, acumulable]):
        raise ValueError("At least one field to update must be provided")

    rule = PromotionRule.objects.select_for_update().filter(id=rule_id).first()

    if rule is None:
        raise ValueError("Rule not found")

    changes_made = False
    update_fields = []

    if type is not None and rule.type != type:
        rule.type = type
        update_fields.append('type')
        changes_made = True

    if value is not None and rule.value != value:
        rule.value = value
        update_fields.append('value')
        changes_made = True

    if priority is not None and rule.priority != priority:
        rule.priority = priority
        update_fields.append('priority')
        changes_made = True

    if start_date is not None and rule.start_at.date() != start_date:
        # Create timezone-aware datetime for start_date
        tz = timezone.get_current_timezone()
        exact_start_datetime = timezone.make_aware(
            datetime.combine(start_date, datetime.min.time()), tz)
        rule.start_at = exact_start_datetime
        update_fields.append('start_at')
        changes_made = True

    if end_date is not None and rule.end_at.date() != end_date:
        tz = timezone.get_current_timezone()
        exact_end_datetime = timezone.make_aware(
            datetime.combine(end_date, datetime.max.time()), tz)
        rule.end_at = exact_end_datetime
        update_fields.append('end_at')
        changes_made = True

    if acumulable is not None and rule.acumulable != acumulable:
        rule.acumulable = acumulable
        update_fields.append('acumulable')
        changes_made = True

    if not changes_made:
        raise ValueError(
            "No changes detected. All provided values are the same as current values")

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise ValueError("User not found")

    rule.updated_by = user
    update_fields.extend(['updated_by', 'updated_at'])
    rule.save(update_fields=update_fields)

    rule.refresh_from_db()

    response = {
        "success": True,
        "message": "Promotion rule updated successfully",
        "data": {
            "rule": {
                "id": rule.pk,
                "type": rule.type,
                "value": rule.value,
                "priority": rule.priority,
                "start_at": rule.start_at,
                "end_at": rule.end_at,
                "acumulable": rule.acumulable,
                "updated_by": rule.updated_by,
                "updated_at": rule.updated_at
            }
        }
    }

    return response


@transaction.atomic
def delete_promotion(promotion_id: int, user_id: int) -> dict:
    """
    Elimina una promoción y todas sus relaciones asociadas de forma transaccional.

    Elimina completamente una promoción del sistema junto con todas sus relaciones
    asociadas (reglas, alcances por categoría, producto y ubicación) utilizando
    el comportamiento CASCADE definido en los modelos. La operación se ejecuta
    dentro de una transacción atómica para garantizar consistencia de datos.

    Args:
        promotion_id (int): ID de la promoción a eliminar
            Debe ser un entero positivo correspondiente a una promoción existente
        user_id (int): ID del usuario que realiza la eliminación

    Returns:
        dict: Estructura con resultado de la eliminación según estándares del proyecto
            {
                "success": bool,
                "message": str,
                "data": {
                    "promotion_id": int,
                    "deleted_at": datetime,
                    "deleted_by": int
                }
            }

    Raises:
        ValueError: Si promotion_id no es un entero positivo válido
        Http404: Si la promoción especificada no existe
    """
    validate_id(promotion_id, "Promotion")
    validate_id(user_id, "User")

    try:
        promotion = Promotion.objects.select_for_update().filter(id=promotion_id).first()
        if promotion is None:
            raise ValueError("Promotion not found")
        promotion_name = promotion.name
        promotion.delete()

        return {
            "success": True,
            "message": f"Promoción '{promotion_name}' eliminada exitosamente",
            "data": {
                "promotion_id": promotion_id,
                "deleted_at": timezone.now(),
                "deleted_by": user_id
            }
        }

    except Promotion.DoesNotExist:
        return {
            "success": False,
            "message": f"Promoción con ID {promotion_id} no encontrada",
            "data": {
                "promotion_id": promotion_id,
                "deleted_by": user_id
            }
        }


@transaction.atomic
def delete_rule(rule_id: int, user_id: int) -> dict:
    """
    Elimina una regla de promoción específica de forma transaccional.

    Permite la eliminación de una regla de promoción identificada por su ID,
    validando la existencia de la regla antes de proceder con la eliminación.
    La operación se ejecuta dentro de una transacción atómica para garantizar
    consistencia de datos.
    Args:
        rule_id (int): ID de la regla de promoción a eliminar
            Debe ser un entero positivo correspondiente a una regla existente
        user_id (int): ID del usuario que realiza la eliminación
    Returns:
        dict: Estructura con resultado de la eliminación según estándares del proyecto
            {
                "success": bool,
                "message": str,
                "data": {
                    "rule_id": int,
                    "deleted_at": datetime,
                    "deleted_by": int
                }
            }
    Raises:
        ValueError: Si rule_id no es un entero positivo válido
        Http404: Si la regla especificada no existe
    """
    validate_id(rule_id, "Rule")
    validate_id(user_id, "User")

    try:
        rule = PromotionRule.objects.select_for_update().filter(id=rule_id).first()
        if rule is None:
            raise ValueError("Rule not found")
        rule_type = rule.type
        rule.delete()

        return {
            "success": True,
            "message": f"Regla de promoción '{rule_type}' eliminada exitosamente",
            "data": {
                "rule_id": rule_id,
                "deleted_at": timezone.now(),
                "deleted_by": user_id
            }
        }

    except PromotionRule.DoesNotExist:
        return {
            "success": False,
            "message": f"Regla de promoción con ID {rule_id} no encontrada",
            "data": {
                "rule_id": rule_id,
                "deleted_by": user_id
            }
        }


@transaction.atomic
def delete_promotion_category(promotion_id: int, category_id: int, user_id: int) -> dict:
    """
    Elimina la asociación entre una promoción y una categoría específica.

    Permite desasociar una categoría de una promoción, eliminando el alcance de
    aplicación de la promoción para esa categoría específica. La operación se
    ejecuta dentro de una transacción atómica para garantizar consistencia de datos.

    Args:
        promotion_id (int): ID de la promoción
            Debe ser un entero positivo correspondiente a una promoción existente
        category_id (int): ID de la categoría
            Debe ser un entero positivo correspondiente a una categoría existente
        user_id (int): ID del usuario que realiza la eliminación
            Se registra para auditoría

    Returns:
        dict: Estructura con resultado de la eliminación según estándares del proyecto
            {
                "success": bool,
                "message": str,
                "data": {
                    "promotion_id": int,
                    "category_id": int,
                    "deleted_at": datetime,
                    "deleted_by": int
                }
            }

    Raises:
        ValueError: Si los IDs no son enteros positivos válidos
        Http404: Si la asociación promoción-categoría no existe
    """
    validate_id(promotion_id, "Promotion")
    validate_id(category_id, "Category")
    validate_id(user_id, "User")

    promotion_category = get_object_or_404(
        PromotionScopeCategory.objects.select_for_update(),
        promotion_id=promotion_id,
        category_id=category_id
    )

    promotion_category.delete()

    return {
        "success": True,
        "message": f"Asociación promoción-categoría eliminada exitosamente",
        "data": {
            "promotion_id": promotion_id,
            "category_id": category_id,
            "deleted_at": timezone.now(),
            "deleted_by": user_id
        }
    }


@transaction.atomic
def delete_promotion_product(promotion_id: int, product_id: int, user_id: int) -> dict:
    """
    Elimina la asociación entre una promoción y un producto específico.

    Permite desasociar un producto de una promoción, eliminando el alcance de
    aplicación de la promoción para ese producto específico. La operación se
    ejecuta dentro de una transacción atómica para garantizar consistencia de datos.

    Args:
        promotion_id (int): ID de la promoción
            Debe ser un entero positivo correspondiente a una promoción existente
        product_id (int): ID del producto
            Debe ser un entero positivo correspondiente a un producto existente
        user_id (int): ID del usuario que realiza la eliminación
            Se registra para auditoría

    Returns:
        dict: Estructura con resultado de la eliminación según estándares del proyecto
            {
                "success": bool,
                "message": str,
                "data": {
                    "promotion_id": int,
                    "product_id": int,
                    "deleted_at": datetime,
                    "deleted_by": int
                }
            }

    Raises:
        ValueError: Si los IDs no son enteros positivos válidos
        Http404: Si la asociación promoción-producto no existe
    """
    validate_id(promotion_id, "Promotion")
    validate_id(product_id, "Product")
    validate_id(user_id, "User")

    try:
        promotion_product = get_object_or_404(PromotionScopeProduct.objects.select_for_update(),
                                              promotion_id=promotion_id,
                                              product_id=product_id)
        promotion_product.delete()

        return {
            "success": True,
            "message": f"Asociación promoción-producto eliminada exitosamente",
            "data": {
                "promotion_id": promotion_id,
                "product_id": product_id,
                "deleted_at": timezone.now(),
                "deleted_by": user_id
            }
        }

    except PromotionScopeProduct.DoesNotExist:
        return {
            "success": False,
            "message": f"Asociación entre promoción {promotion_id} y producto {product_id} no encontrada",
            "data": {
                "promotion_id": promotion_id,
                "product_id": product_id,
                "deleted_by": user_id
            }
        }


@transaction.atomic
def delete_promotion_location(promotion_id: int, location_id: int, user_id: int) -> dict:
    """
    Elimina la asociación entre una promoción y una ubicación específica.

    Permite desasociar una ubicación de una promoción, eliminando el alcance
    geográfico de aplicación de la promoción para esa ubicación específica. 
    La operación se ejecuta dentro de una transacción atómica para garantizar 
    consistencia de datos.

    Args:
        promotion_id (int): ID de la promoción
            Debe ser un entero positivo correspondiente a una promoción existente
        location_id (int): ID de la ubicación de almacenamiento
            Debe ser un entero positivo correspondiente a una ubicación existente
        user_id (int): ID del usuario que realiza la eliminación
            Se registra para auditoría

    Returns:
        dict: Estructura con resultado de la eliminación según estándares del proyecto
            {
                "success": bool,
                "message": str,
                "data": {
                    "promotion_id": int,
                    "location_id": int,
                    "deleted_at": datetime,
                    "deleted_by": int
                }
            }

    Raises:
        ValueError: Si los IDs no son enteros positivos válidos
        Http404: Si la asociación promoción-ubicación no existe
    """
    validate_id(promotion_id, "Promotion")
    validate_id(location_id, "Location")
    validate_id(user_id, "User")

    try:
        promotion_location = get_object_or_404(PromotionScopeLocation.objects.select_for_update(),
                                               promotion_id=promotion_id,
                                               location_id=location_id)
        promotion_location.delete()

        return {
            "success": True,
            "message": f"Asociación promoción-ubicación eliminada exitosamente",
            "data": {
                "promotion_id": promotion_id,
                "location_id": location_id,
                "deleted_at": timezone.now(),
                "deleted_by": user_id
            }
        }

    except PromotionScopeLocation.DoesNotExist:
        return {
            "success": False,
            "message": f"Asociación entre promoción {promotion_id} y ubicación {location_id} no encontrada",
            "data": {
                "promotion_id": promotion_id,
                "location_id": location_id,
                "deleted_by": user_id
            }
        }


# === Funciones de obtención ===#


def get_active_promotions_category(category_id: int) -> list[dict]:
    """
    Obtiene promociones activas asociadas a una categoría específica con sus reglas vigentes.

    Recupera todas las promociones activas que están asociadas a una categoría determinada,
    incluyendo sus reglas de promoción que estén actualmente vigentes (dentro del rango
    de fechas start_date y end_date). Utiliza prefetch_related para optimizar las consultas
    y evitar el problema N+1, devolviendo los datos en formato estructurado.

    Args:
        category_id (int): ID de la categoría para filtrar promociones
            Debe ser un entero positivo correspondiente a una categoría existente
            Se valida automáticamente con validate_id()

    Returns:
        list[dict]: Lista de diccionarios con promociones y sus reglas vigentes
            Cada diccionario contiene:
            - id (int): ID único de la promoción
            - name (str): Nombre normalizado de la promoción
            - active (bool): Estado de activación (siempre True por filtro)
            - created_by (int): ID del usuario creador
            - rules (list[dict]): Lista de reglas vigentes con:
                - id (int): ID único de la regla
                - type (str): Tipo de regla (ej: PERCENTAGE_DISCOUNT)
                - promotion_id (int): ID de la promoción asociada
                - value (Decimal): Valor asociado a la regla
                - priority (int): Prioridad de aplicación
                - start_date (datetime): Fecha/hora de inicio de vigencia
                - end_date (datetime): Fecha/hora de fin de vigencia
                - acumulable (bool): Indica si es acumulable con otras reglas
                - created_by (int): ID del usuario creador de la regla

    Raises:
        ValueError: Si category_id no es un entero positivo válido
            Propagado desde validate_id() con mensaje descriptivo
    """
    validate_id(category_id, "Category")

    promotions_queryset = Promotion.objects.prefetch_related(
        models.Prefetch(
            "promotionrule_set",
            queryset=PromotionRule.objects.filter(
                start_at__lte=timezone.now(),
                end_at__gte=timezone.now()
            ).order_by('-priority', 'id'),
            to_attr='rules'
        )
    ).filter(
        active=True,
        promotionscopecategory__category__id=category_id
    )

    response = []
    for promotion in promotions_queryset:
        promotion_data = {
            'id': promotion.pk,
            'name': promotion.name,
            'active': promotion.active,
            'created_by': promotion.created_by,
            'rules': []
        }

        rules_iter = getattr(promotion, 'rules', None)
        if rules_iter is None:
            rules_iter = promotion.promotionrule_set.filter(start_at__lte=timezone.now(
            ), end_at__gte=timezone.now()).order_by('-priority', 'id')
        for rule in rules_iter:
            rule_data = {
                'id': rule.pk,
                'type': rule.type,
                'promotion_id': rule.promotion_id,
                'value': rule.value,
                'priority': rule.priority,
                'start_at': rule.start_at,
                'end_at': rule.end_at,
                'acumulable': rule.acumulable,
                'created_by': rule.created_by
            }
            promotion_data['rules'].append(rule_data)

        response.append(promotion_data)

    return response


def get_active_promotions_product(product_id: int) -> list[dict]:
    """
    Obtiene promociones activas asociadas a un producto específico con sus reglas vigentes.

    Recupera todas las promociones activas que están asociadas a un producto determinado,
    incluyendo sus reglas de promoción que estén actualmente vigentes (dentro del rango
    de fechas start_date y end_date). Utiliza prefetch_related para optimizar las consultas
    y evitar el problema N+1, devolviendo los datos en formato estructurado.
        - Pre-carga reglas vigentes basadas en fechas de inicio y fin
        - Estructura los datos en formato de diccionario para fácil consumo
        - Incluye información completa de promociones y sus reglas aplicables

    Optimizaciones aplicadas:
        - prefetch_related("products") evita consultas N+1 para productos asociados
        - Prefetch personalizado con queryset filtrado para reglas vigentes únicamente
        - Filtrado temporal en base de datos usando timezone.now() para precisión
        - Carga eficiente de relaciones many-to-many y foreign-key en una sola consulta

    Validaciones realizadas:
        - product_id debe ser entero positivo mediante validate_id()
        - Filtrado automático por promociones activas (active=True)
        - Filtrado temporal de reglas vigentes (start_date <= now <= end_date)
        - Asociación válida entre promoción y producto mediante products__id

    Args:
        product_id (int): ID del producto para filtrar promociones
            Debe ser un entero positivo correspondiente a un producto existente
            Se valida automáticamente con validate_id()

    Returns:
        list[dict]: Lista de diccionarios con promociones y sus reglas vigentes
            Cada diccionario contiene:
            - id (int): ID único de la promoción
            - name (str): Nombre normalizado de la promoción
            - active (bool): Estado de activación (siempre True por filtro)
            - rules (list[dict]): Lista de reglas vigentes con:
                - id (int): ID único de la regla
                - type (str): Tipo de regla (ej: PERCENTAGE_DISCOUNT)
                - promotion_id (int): ID de la promoción asociada
                - value (Decimal): Valor asociado a la regla
                - priority (int): Prioridad de aplicación
                - start_date (datetime): Fecha/hora de inicio de vigencia
                - end_date (datetime): Fecha/hora de fin de vigencia
                - acumulable (bool): Indica si es acumulable con otras reglas
                - created_by (int): ID del usuario creador de la regla

    Raises:
        ValueError: Si product_id no es un entero positivo válido
            Propagado desde validate_id() con mensaje descriptivo

    """
    validate_id(product_id, "Product")
    promotions_queryset = Promotion.objects.prefetch_related(
        models.Prefetch(
            "promotionrule_set",
            queryset=PromotionRule.objects.filter(
                start_at__lte=timezone.now(),
                end_at__gte=timezone.now()
            ).order_by('-priority', 'id'),
            to_attr='rules'
        )
    ).filter(
        active=True,
        promotionscopeproduct__product__id=product_id
    )
    response = []
    for promotion in promotions_queryset:
        promotion_data = {
            'id': promotion.pk,
            'name': promotion.name,
            'active': promotion.active,
            'rules': []
        }

        rules_iter = getattr(promotion, 'rules', None)
        if rules_iter is None:
            rules_iter = promotion.promotionrule_set.filter(start_at__lte=timezone.now(
            ), end_at__gte=timezone.now()).order_by('-priority', 'id')
        for rule in rules_iter:
            rule_data = {
                'id': rule.pk,
                'type': rule.type,
                'promotion_id': rule.promotion_id,
                'value': rule.value,
                'priority': rule.priority,
                'start_at': rule.start_at,
                'end_at': rule.end_at,
                'acumulable': rule.acumulable,
                'created_by': rule.created_by
            }
            promotion_data['rules'].append(rule_data)
        response.append(promotion_data)
    return response


def get_active_promotions_location(location_id: int) -> list[dict]:
    """
    Obtiene promociones activas asociadas a una ubicación específica con sus reglas vigentes.

    Recupera todas las promociones activas que están asociadas a una ubicación de almacenamiento
    determinada, incluyendo sus reglas de promoción que estén actualmente vigentes. Utiliza
    consultas optimizadas con prefetch_related y select_related para minimizar las consultas
    a la base de datos y mejorar el rendimiento según las mejores prácticas de Django ORM.

    Args:
        location_id (int): ID de la ubicación de almacenamiento para filtrar promociones
            Se presupone que es un ID válido y que la ubicación existe

    Returns:
        list[dict]: Lista de diccionarios con promociones y sus reglas vigentes
            Cada diccionario contiene:
            - id (int): ID único de la promoción
            - name (str): Nombre normalizado de la promoción
            - active (bool): Estado de activación (siempre True por filtro)
            - created_by (int): ID del usuario creador
            - created_at (datetime): Fecha/hora de creación de la promoción
            - rules (list[dict]): Lista de reglas vigentes con:
                - id (int): ID único de la regla
                - type (str): Tipo de regla (ej: PERCENTAGE_DISCOUNT)
                - promotion_id (int): ID de la promoción asociada
                - value (Decimal): Valor asociado a la regla (como string para JSON)
                - priority (int): Prioridad de aplicación
                - start_date (datetime): Fecha/hora de inicio de vigencia
                - end_date (datetime): Fecha/hora de fin de vigencia
                - acumulable (bool): Indica si es acumulable con otras reglas
                - created_by (int): ID del usuario creador de la regla
    """
    now = timezone.now()

    promotions_queryset = Promotion.objects.select_related(
        'created_by'
    ).prefetch_related(
        models.Prefetch(
            "promotionrule_set",
            queryset=PromotionRule.objects.select_related('created_by').filter(
                start_at__lte=now,
                end_at__gte=now
            ).order_by('-priority', 'id'),
            to_attr='rules'
        )
    ).filter(
        active=True,
        promotionscopelocation__location__id=location_id
    ).distinct().order_by('id')
    promotions_data = []

    for promotion in promotions_queryset:
        promotion_data = {
            'id': promotion.pk,
            'name': promotion.name,
            'active': promotion.active,
            'created_by': promotion.created_by,
            'created_at': promotion.created_at,
            'rules': []
        }

        rules_iter = getattr(promotion, 'rules', None)
        if rules_iter is None:
            rules_iter = promotion.promotionrule_set.filter(
                start_at__lte=now, end_at__gte=now).order_by('-priority', 'id')
        for rule in rules_iter:
            rule_data = {
                'id': rule.pk,
                'type': rule.type,
                'promotion_id': rule.promotion_id,
                'value': rule.value,
                'priority': rule.priority,
                'start_at': rule.start_at,
                'end_at': rule.end_at,
                'acumulable': rule.acumulable,
                'created_by': rule.created_by
            }
            promotion_data['rules'].append(rule_data)

        promotions_data.append(promotion_data)

    return promotions_data


def _get_all_active_promotions_for_product(product: Product) -> list[dict]:
    """
    Obtiene todas las promociones activas aplicables a un producto en una sola consulta optimizada.

    Combina promociones directas del producto, de sus categorías y de sus ubicaciones
    utilizando una estrategia de consulta eficiente que minimiza las queries a la base de datos.

    Args:
        product (Product): Instancia del producto para obtener promociones

    Returns:
        list[dict]: Lista combinada de todas las promociones aplicables
    """
    product_id = product.pk

    category_ids = list(product.categories.values_list('id', flat=True))

    location_ids = list(InventoryRecord.objects.filter(
        product_id=product_id).values_list('location_id', flat=True).distinct())

    all_promotions = []

    all_promotions.extend(get_active_promotions_product(product_id))

    for category_id in category_ids:
        all_promotions.extend(get_active_promotions_category(category_id))

    for location_id in location_ids:
        all_promotions.extend(get_active_promotions_location(location_id))

    return all_promotions


def _separate_rules_by_acumulability(promotions: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Separa las reglas de promoción según su capacidad de acumulación.

    Args:
        promotions (list[dict]): Lista de promociones con sus reglas

    Returns:
        tuple[list[dict], list[dict]]: Tupla con (reglas_acumulables, reglas_no_acumulables)
    """
    acumulable_rules = []
    non_acumulable_rules = []

    for promotion in promotions:
        for rule in promotion['rules']:
            if rule['acumulable']:
                acumulable_rules.append(rule)
            else:
                non_acumulable_rules.append(rule)

    return acumulable_rules, non_acumulable_rules


def _determine_applicable_rules(acumulable_rules: list[dict], non_acumulable_rules: list[dict]) -> list[dict]:
    """
    Determina qué reglas aplicar basándose en la lógica de prioridades del negocio.

    Lógica implementada:
        - Si hay reglas no acumulables con mayor prioridad que las acumulables: aplica solo la de mayor prioridad
        - Si las reglas acumulables tienen prioridad mayor o igual: aplica todas las acumulables
        - En caso de no haber reglas de un tipo, aplica las del otro tipo

    Args:
        acumulable_rules (list[dict]): Lista de reglas acumulables
        non_acumulable_rules (list[dict]): Lista de reglas no acumulables

    Returns:
        list[dict]: Lista de reglas que deben aplicarse
    """
    if not acumulable_rules and not non_acumulable_rules:
        return []

    max_priority_acumulable = max(
        (rule['priority'] for rule in acumulable_rules),
        default=0
    )
    max_priority_non_acumulable = max(
        (rule['priority'] for rule in non_acumulable_rules),
        default=0
    )

    if not non_acumulable_rules or max_priority_acumulable >= max_priority_non_acumulable:

        return acumulable_rules
    else:
        highest_priority_rule = next(
            rule for rule in non_acumulable_rules
            if rule['priority'] == max_priority_non_acumulable
        )
        return [highest_priority_rule]


def get_categories_with_active_promotions() -> list[dict]:
    """
    Obtiene todas las categorías que tienen promociones activas vigentes.

    Recupera las categorías que están asociadas a promociones activas con reglas
    vigentes en el momento actual. Incluye información detallada de la categoría
    y las promociones aplicables, optimizada para evitar consultas N+1.

    Returns:
        list[dict]: Lista de categorías con promociones activas
            Cada elemento contiene:
            - id (int): ID de la categoría
            - name (str): Nombre de la categoría  
            - created_at (datetime): Fecha de creación de la categoría
            - updated_at (datetime): Fecha de última actualización
            - promotions (list): Lista de promociones activas aplicables
                Cada promoción incluye:
                - id (int): ID de la promoción
                - name (str): Nombre de la promoción
                - active (bool): Estado de la promoción
                - rules (list): Reglas vigentes de la promoción

    Raises:
        Exception: En caso de error interno del servidor o problema de conectividad con la base de datos
    """
    now = timezone.now()

    categories_with_promotions = Category.objects.prefetch_related(
        models.Prefetch(
            'promotionscopecategory_set__promotion',
            queryset=Promotion.objects.filter(active=True).prefetch_related(
                models.Prefetch(
                    'promotionrule_set',
                    queryset=PromotionRule.objects.filter(
                        start_at__lte=now,
                        end_at__gte=now
                    ).select_related('created_by').order_by('-priority', 'id')
                )
            ).select_related('created_by')
        )
    ).filter(
        promotionscopecategory__promotion__active=True,
        promotionscopecategory__promotion__promotionrule__start_at__lte=now,
        promotionscopecategory__promotion__promotionrule__end_at__gte=now
    ).distinct().order_by('name')

    categories_data = []

    for category in categories_with_promotions:
        category_data = {
            'id': category.pk,
            'name': category.name,
            'created_at': category.created_at,
            'updated_at': category.updated_at,
            'created_by': category.created_by,
            'updated_by': category.updated_by,
            'promotions': []
        }

        promotions_seen = set()

        scopes_iter = getattr(category, 'promotionscopecategory_set', None)
        if scopes_iter is None:
            scopes_iter = category.promotionscopecategory_set.all()
        for scope in scopes_iter:
            promotion = scope.promotion

            if promotion.pk in promotions_seen:
                continue

            promotions_seen.add(promotion.pk)

            promotion_data = {
                'id': promotion.pk,
                'name': promotion.name,
                'active': promotion.active,
                'created_by': promotion.created_by,
                'created_at': promotion.created_at,
                'rules': []
            }

            rules_iter = getattr(promotion, 'rules', None)
            if rules_iter is None:
                rules_iter = promotion.promotionrule_set.all()
            for rule in rules_iter:
                rule_data = {
                    'id': rule.pk,
                    'type': rule.type,
                    'value': rule.value,
                    'priority': rule.priority,
                    'start_at': rule.start_at,
                    'end_at': rule.end_at,
                    'acumulable': rule.acumulable,
                    'created_by': rule.created_by
                }
                promotion_data['rules'].append(rule_data)

            category_data['promotions'].append(promotion_data)

        if category_data['promotions']:
            categories_data.append(category_data)

    return categories_data


def calculate_discounted_price_product(product: Product) -> Decimal:
    """
    Calcula el precio con descuento aplicando promociones activas para un producto específico.

    Aplica la lógica de negocio para determinar qué promociones son aplicables a un producto
    considerando reglas acumulables y no acumulables, prioridades y diferentes alcances
    (producto directo, categorías y ubicaciones). Optimiza las consultas a base de datos
    mediante una sola consulta con prefetch_related.

    Lógica de prioridades:
        - Si existen reglas no acumulables con mayor prioridad: aplica solo la de mayor prioridad
        - Si reglas acumulables tienen prioridad mayor o igual: aplica todas las acumulables
        - En caso de empate, prevalecen las reglas acumulables

    Args:
        product (Product): Instancia del modelo Product para calcular descuentos
            Debe ser una instancia válida del modelo Product con id, unit_price y categories

    Returns:
        Decimal: Precio final con descuentos aplicados
            Nunca retorna valores negativos (mínimo Decimal('0.00'))
            Si no hay promociones aplicables retorna product.unit_price

    Raises:
        ValueError: Si product es None o no es una instancia de Product

    """

    if product is None or not isinstance(product, Product):
        raise ValueError("A valid Product instance must be provided")

    # Optimización: obtener todas las promociones en una sola consulta
    all_promotions = _get_all_active_promotions_for_product(product)

    if not all_promotions:
        return product.unit_price

    acumulable_rules, non_acumulable_rules = _separate_rules_by_acumulability(
        all_promotions)

    applicable_rules = _determine_applicable_rules(
        acumulable_rules, non_acumulable_rules)

    total_discount_amount = _calculate_total_discount(
        applicable_rules, product.unit_price)

    final_price = max(product.unit_price -
                      total_discount_amount, Decimal('0.00'))

    return final_price


def _calculate_total_discount(rules: list[dict], unit_price: Decimal) -> Decimal:
    """
    Calcula el monto total de descuento aplicando las reglas especificadas.

    Maneja diferentes tipos de descuento:
        - PERCENTAGE: aplica porcentaje sobre el precio unitario
        - AMOUNT: aplica monto fijo de descuento

    Args:
        rules (list[dict]): Lista de reglas a aplicar
        unit_price (Decimal): Precio unitario del producto

    Returns:
        Decimal: Monto total de descuento a aplicar
    """
    total_discount = Decimal('0.00')

    for rule in rules:
        if rule['type'] == PromotionRule.Type.PERCENTAGE:
            discount_amount = (rule['value'] / Decimal('100.00')) * unit_price
            total_discount += discount_amount
        elif rule['type'] == PromotionRule.Type.AMOUNT:
            total_discount += rule['value']

    return total_discount
