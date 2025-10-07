from django.db import transaction, models
from api.promotions.services import calculate_discounted_price_product
from .models import Purchase, PurchaseDetail
from api.products.models import Product
from api.inventories.models import InventoryRecord
from api.inventories.services import exit_sale_inventory, return_entry_inventory
from django.shortcuts import get_object_or_404
from api.utils import validate_id
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth import get_user_model
from api.permissions import PermissionDenied, log_permission_attempt
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def validate_user_can_access_purchase(user_id: int, purchase_id: int, action: str = "access") -> Dict[str, Any]:
    """
    Valida si un usuario puede acceder a una compra específica.

    Args:
        user_id (int): ID del usuario que intenta acceder
        purchase_id (int): ID de la compra
        action (str): Acción que intenta realizar (access, modify, delete)

    Returns:
        Dict[str, Any]: Respuesta con validación exitosa o error de permisos

    Raises:
        PermissionError: Si el usuario no tiene permisos
    """
    validate_id(user_id, 'User')
    validate_id(purchase_id, 'Purchase')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return PermissionDenied.resource_not_found("user", user_id)

    try:
        purchase = Purchase.objects.get(id=purchase_id)
    except Purchase.DoesNotExist:
        return PermissionDenied.resource_not_found("purchase", purchase_id)

    is_admin = user.is_staff
    is_owner = purchase.user.pk == user_id

    if not is_admin and not is_owner:
        log_permission_attempt(user_id, user.username,
                               action, "purchase", purchase_id)
        return PermissionDenied.purchase_access_denied(user_id, purchase_id, action)

    return {
        "success": True,
        "can_access": True,
        "is_admin": is_admin,
        "is_owner": is_owner,
        "purchase": purchase,
        "user": user
    }


def get_single_purchase(user_id: int, purchase_id: int) -> Dict[str, Any]:
    """
    Obtiene una compra específica si el usuario tiene permisos.

    Args:
        user_id (int): ID del usuario que solicita la compra
        purchase_id (int): ID de la compra solicitada

    Returns:
        Dict[str, Any]: Respuesta estándar con los datos de la compra o error
    """
    # Validar permisos primero
    validation_result = validate_user_can_access_purchase(
        user_id, purchase_id, "view")

    if not validation_result.get("success", False):
        return validation_result

    purchase = validation_result["purchase"]

    # Obtener detalles completos de la compra
    purchase_query = Purchase.objects.select_related('user').prefetch_related(
        models.Prefetch(
            'details',
            queryset=PurchaseDetail.objects.select_related(
                'product').prefetch_related('product__categories')
        )
    ).filter(id=purchase_id).first()

    if not purchase_query:
        return PermissionDenied.resource_not_found("purchase", purchase_id)

    # Construir respuesta detallada
    user_data = {
        "id": purchase_query.user.id,
        "username": purchase_query.user.username,
        "email": purchase_query.user.email,
        "first_name": purchase_query.user.first_name,
        "last_name": purchase_query.user.last_name
    }

    details_data = []
    for detail in purchase_query.details.all():
        primary_category = detail.product.get_primary_category()
        category_name = primary_category.name if primary_category else None

        detail_data = {
            "id": detail.pk,
            "product": {
                "id": detail.product.pk,
                "name": detail.product.name,
                "brand": detail.product.brand,
                "model": detail.product.model,
                "description": detail.product.description,
                "unit_price": detail.product.unit_price,
                "main_category": category_name
            },
            "quantity": detail.quantity,
            "unit_price_at_purchase": detail.unit_price_at_purchase,
            "subtotal": detail.subtotal
        }
        details_data.append(detail_data)

    purchase_data = {
        "id": purchase_query.pk,
        "user": user_data,
        "purchase_date": purchase_query.purchase_date,
        "total_amount": purchase_query.total_amount,
        "total_installments_count": purchase_query.total_installments_count,
        "status": purchase_query.status,
        "discount_applied": purchase_query.discount_applied or Decimal('0.00'),
        "created_at": purchase_query.created_at,
        "updated_at": purchase_query.updated_at,
        "details": details_data
    }

    return {
        "success": True,
        "message": "Purchase retrieved successfully",
        "data": {
            "purchase": purchase_data
        }
    }


@transaction.atomic
def create_purchase_detail(purchase_id: int, product: Product, quantity: int, location_ids: list):
    """
    Crea un detalle de compra y descuenta el stock del inventario.

    Args:
        purchase_id: ID de la compra existente
        product: Instancia del producto
        quantity: Cantidad a comprar
        location_ids: Lista con un solo ID de ubicación

    Returns:
        dict: Respuesta con datos del detalle creado

    Raises:
        ValueError: Si no hay stock suficiente o datos inválidos
    """

    validate_id(purchase_id, 'Purchase')

    for location_id in location_ids:
        validate_id(location_id, f'Location{location_id}')
    if len(location_ids) != 1:
        raise ValueError("Only one location_id must be provided.")

    if not isinstance(quantity, int) or quantity <= 0 or not quantity:
        raise ValueError("Quantity must be a positive integer.")

    purchase = get_object_or_404(Purchase, id=purchase_id)

    inventory_record = InventoryRecord.objects.filter(
        product=product, location__in=location_ids)

    if not inventory_record.exists():
        raise ValueError("One or more provided location_ids do not exist.")

    sufficient_stock = False
    stock_in_location = None
    for ir in inventory_record:
        if ir.quantity >= quantity:
            sufficient_stock = True
            stock_in_location = ir
            break

    if not sufficient_stock or stock_in_location is None:
        raise ValueError("Insufficient stock in the specified location.")

    assert stock_in_location is not None, "stock_in_location should not be None at this point"

    unit_price_at_purchase = calculate_discounted_price_product(product)

    subtotal = (unit_price_at_purchase * quantity).quantize(Decimal('0.01'))
    discount_applied_at_product = (
        product.unit_price - unit_price_at_purchase).quantize(Decimal('0.01'))

    primary_category = product.get_primary_category()
    category_name = primary_category.name if primary_category else None

    purchase_detail = PurchaseDetail.objects.create(
        purchase=purchase,
        product=product,
        quantity=quantity,
        unit_price_at_purchase=unit_price_at_purchase,
        subtotal=subtotal
    )

    discount_stock = exit_sale_inventory(product=product, from_location=stock_in_location.pk,
                                         description=f"Purchase Detail ID: {purchase_detail.pk}",
                                         quantity=quantity, reference_id=purchase_detail.pk, user=purchase.user)

    if not discount_stock.get("success", False):
        raise ValueError("Failed to update inventory ")

    return {
        "success": True,
        "message": "Purchase detail created successfully.",
        "data": {
            "product_name": product.name,
            "product_brand": product.brand,
            "product_model": product.model,
            "main_category": category_name,
            "product_description": product.description,
            "unit_price": product.unit_price,
            "discount_applied_at_product": discount_applied_at_product,
            "unit_price_at_purchase": unit_price_at_purchase,
            "quantity": quantity,
            "subtotal": subtotal,
        }
    }


@transaction.atomic
def create_purchase(user_id: int, installments_count: int,
                    discount_applied: Decimal = Decimal('0.00'),
                    products_ids_quantity: list[tuple[int, int]] = [], location_ids: list = []):
    """
    Crea una compra completa con múltiples productos y sus detalles.

    Args:
        user_id: ID del usuario comprador
        installments_count: Número de cuotas para pagar
        discount_applied: Descuento adicional a aplicar (opcional)
        products_ids_quantity: Lista de tuplas (product_id, cantidad)
        location_ids: Lista de IDs de ubicaciones de inventario

    Returns:
        dict: Respuesta con datos de la compra y sus detalles

    Raises:
        ValueError: Si productos no existen o datos son inválidos
    """

    validate_id(user_id, 'User')

    now = timezone.now()
    purchase_date = timezone.localtime(now)

    total_amount = Decimal('0.00')

    if installments_count <= 0:
        raise ValueError(
            "Total installments count must be a positive integer.")

    if (discount_applied).quantize(Decimal('0.01')) < Decimal('0.00'):
        raise ValueError("Discount applied cannot be negative.")

    if not isinstance(location_ids, list) or len(location_ids) == 0:
        raise ValueError("Location IDs must be a non-empty list.")

    if not isinstance(products_ids_quantity, list) or len(products_ids_quantity) == 0:
        raise ValueError("Products list must be a non-empty list.")
    for item in products_ids_quantity:
        if (not isinstance(item, tuple) or len(item) != 2 or
                not all(isinstance(i, int) and i > 0 for i in item)):
            raise ValueError(
                "Each item in products list must be a tuple of two positive integers (product_id, quantity).")

    qs_products = Product.objects.prefetch_related('categories').filter(
        id__in=[item[0] for item in products_ids_quantity])
    if qs_products.count() != len(products_ids_quantity):
        raise ValueError(
            "One or more product IDs in products_list do not exist.")

    purchase_detail_l = []

    try:
        created_by_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise ValueError("User not found")

    purchase = Purchase.objects.create(
        user_id=user_id,
        purchase_date=purchase_date,
        total_amount=Decimal('0.00'),  # Temporal, se calculará después
        total_installments_count=installments_count,
        status=Purchase.Status.OPEN,
        discount_applied=discount_applied,
        created_by=created_by_user
    )
    for product in qs_products:
        quantity = next(
            (item[1] for item in products_ids_quantity if item[0] == product.pk), None)

        if quantity is None:
            raise ValueError(f"No quantity found for product ID {product.pk}")

        detail = create_purchase_detail(
            purchase_id=purchase.pk,
            product=product,
            quantity=quantity,
            location_ids=location_ids
        )
        if not detail.get("success", False):
            raise ValueError(
                f"Failed to create purchase detail for product ID {product.pk}: {detail.get('message', 'Unknown error')}")
        total_amount += detail['data']['subtotal']
        purchase_detail_l.append(detail['data'])

    purchase.total_amount = (
        total_amount - discount_applied).quantize(Decimal('0.01'))
    purchase.save()

    # PLANTILLA DE REFERENCIA DE RESPUESTA
    response_data = {
        "success": True,
        "message": "Purchase created successfully.",
        "data": {
            "purchase": {
                "user_id": user_id,
                "purchase_date": purchase.purchase_date,
                "total_amount": purchase.total_amount,
                "total_installments_count": purchase.total_installments_count,
                "status": purchase.status,
                "discount_applied": purchase.discount_applied,
                "created_by": user_id
            },
            "details": purchase_detail_l
        }
    }
    return response_data


def get_user_purchases(user_id: int, status: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene las compras de un usuario específico con su información completa.

    Permite a cada usuario acceder únicamente a sus propias compras, incluyendo
    información del usuario, detalles de productos, y datos relacionados. Las compras
    se ordenan por estado (OPEN primero, luego PAID, finalmente CANCELLED) y después
    por fecha de compra descendente (más recientes primero).

    La paginación se maneja automáticamente a nivel de vista mediante la configuración
    DEFAULT_PAGINATION_CLASS de Django REST Framework (100 elementos por página).

    Args:
        user_id (int): ID del usuario para filtrar sus compras
        status (Optional[str]): Estado específico para filtrar ['OPEN', 'PAID', 'CANCELLED']

    Returns:
        Dict[str, Any]: Respuesta estándar con las compras del usuario:
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (Dict): Información de las compras
                - purchases (List[Dict]): Lista de compras con información completa
                - count (int): Total de compras encontradas

    Raises:
        ValueError: Si user_id es inválido o status no es válido
    """
    validate_id(user_id, 'User')

    user = get_object_or_404(User, id=user_id)

    valid_statuses = [choice[0] for choice in Purchase.Status.choices]
    if status is not None and status not in valid_statuses:
        raise ValueError(
            f"Status must be one of {valid_statuses}, got: {status}")

    purchases_query = Purchase.objects.select_related(
        'user'
    ).prefetch_related(
        models.Prefetch(
            'details',
            queryset=PurchaseDetail.objects.select_related(
                'product'
            ).prefetch_related(
                'product__categories'
            )
        )
    ).filter(user_id=user_id)

    if status:
        purchases_query = purchases_query.filter(status=status)

    # Ordenar por estado (OPEN, PAID, CANCELLED) y fecha descendente
    status_order = models.Case(
        models.When(status=Purchase.Status.OPEN, then=models.Value(1)),
        models.When(status=Purchase.Status.PAID, then=models.Value(2)),
        models.When(status=Purchase.Status.CANCELLED, then=models.Value(3)),
        default=models.Value(4),
        output_field=models.IntegerField()
    )

    purchases_query = purchases_query.annotate(
        status_order=status_order
    ).order_by('status_order', '-purchase_date')

    purchases = list(purchases_query)

    purchases_data = []
    for purchase in purchases:
        user_data = {
            "id": purchase.user.id,
            "username": purchase.user.username,
            "email": purchase.user.email,
            "first_name": purchase.user.first_name,
            "last_name": purchase.user.last_name
        }

        details_data = []
        for detail in purchase.details.all():
            primary_category = detail.product.get_primary_category()
            category_name = primary_category.name if primary_category else None

            detail_data = {
                "id": detail.pk,
                "product": {
                    "id": detail.product.pk,
                    "name": detail.product.name,
                    "brand": detail.product.brand,
                    "model": detail.product.model,
                    "description": detail.product.description,
                    "unit_price": detail.product.unit_price,
                    "main_category": category_name
                },
                "quantity": detail.quantity,
                "unit_price_at_purchase": detail.unit_price_at_purchase,
                "subtotal": detail.subtotal
            }
            details_data.append(detail_data)

        purchase_data = {
            "id": purchase.pk,
            "user": user_data,
            "purchase_date": purchase.purchase_date,
            "total_amount": purchase.total_amount,
            "total_installments_count": purchase.total_installments_count,
            "status": purchase.status,
            "discount_applied": purchase.discount_applied,
            "created_at": purchase.created_at,
            "updated_at": purchase.updated_at,
            "details": details_data
        }
        purchases_data.append(purchase_data)

    return {
        "success": True,
        "message": "User purchases retrieved successfully.",
        "data": {
            "purchases": purchases_data,
            "count": len(purchases_data)
        }
    }


def get_admin_purchases_with_filters(**filters) -> Dict[str, Any]:
    """
    Obtiene todas las compras con filtros avanzados para usuarios administradores.

    Permite a los administradores acceder a todas las compras del sistema con capacidades
    de filtrado avanzadas por múltiples criterios. Incluye información completa de usuarios,
    productos y detalles de compra con optimizaciones de consultas.

    Args:
        **filters: Filtros opcionales para las compras:
            - user_id (int): ID del usuario específico
            - status (str): Estado de la compra ['OPEN', 'PAID', 'CANCELLED']
            - start_date (str): Fecha inicio en formato 'YYYY-MM-DD'
            - end_date (str): Fecha fin en formato 'YYYY-MM-DD'
            - min_amount (Decimal/str): Monto mínimo de la compra
            - max_amount (Decimal/str): Monto máximo de la compra
            - product_id (int): ID de producto específico en los detalles
            - brand (str): Marca de producto para filtrar
            - category_id (int): ID de categoría para filtrar por productos

    Returns:
        Dict[str, Any]: Respuesta estándar con las compras filtradas:
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (Dict): Información de las compras
                - purchases (List[Dict]): Lista de compras con información completa
                - count (int): Total de compras encontradas
                - filters_applied (Dict): Filtros que fueron aplicados

    Raises:
        ValueError: Si algún filtro tiene formato incorrecto o valores inválidos

    Nota:
        La paginación se maneja automáticamente a nivel de vista mediante la configuración
        DEFAULT_PAGINATION_CLASS de Django REST Framework (100 elementos por página).

    Ejemplo de uso:
        # Filtrar compras abiertas de un usuario específico
        get_admin_purchases_with_filters(user_id=1, status='OPEN')

        # Filtrar por rango de fechas y monto
        get_admin_purchases_with_filters(
            start_date='2024-01-01',
            end_date='2024-12-31',
            min_amount='100.00'
        )
    """
    from datetime import datetime
    from decimal import InvalidOperation

    VALID_FILTERS = {
        'user_id': int,
        'status': str,
        'start_date': str,
        'end_date': str,
        'min_amount': (str, Decimal),
        'max_amount': (str, Decimal),
        'product_id': int,
        'brand': str,
        'category_id': int
    }

    applied_filters = {}
    for key, value in filters.items():
        if key not in VALID_FILTERS:
            raise ValueError(
                f"Invalid filter: {key}. Valid filters are: {list(VALID_FILTERS.keys())}")

        expected_type = VALID_FILTERS[key]
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                raise ValueError(
                    f"Filter {key} must be of type {expected_type}, got {type(value)}")
        else:
            if not isinstance(value, expected_type):
                raise ValueError(
                    f"Filter {key} must be of type {expected_type}, got {type(value)}")

        applied_filters[key] = value

    if 'status' in applied_filters:
        valid_statuses = [choice[0] for choice in Purchase.Status.choices]
        if applied_filters['status'] not in valid_statuses:
            raise ValueError(
                f"Status must be one of {valid_statuses}, got: {applied_filters['status']}")

    if 'user_id' in applied_filters:
        validate_id(applied_filters['user_id'], 'User')

    if 'product_id' in applied_filters:
        validate_id(applied_filters['product_id'], 'Product')

    if 'category_id' in applied_filters:
        validate_id(applied_filters['category_id'], 'Category')

    date_fields = ['start_date', 'end_date']
    for date_field in date_fields:
        if date_field in applied_filters:
            try:
                datetime.strptime(applied_filters[date_field], '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"{date_field} must be in format YYYY-MM-DD")

    amount_fields = ['min_amount', 'max_amount']
    for amount_field in amount_fields:
        if amount_field in applied_filters:
            try:
                amount_value = Decimal(str(applied_filters[amount_field]))
                if amount_value < 0:
                    raise ValueError(f"{amount_field} cannot be negative")
                applied_filters[amount_field] = amount_value
            except (ValueError, InvalidOperation):
                raise ValueError(
                    f"{amount_field} must be a valid decimal number")

    purchases_query = Purchase.objects.select_related(
        'user'
    ).prefetch_related(
        models.Prefetch(
            'details',
            queryset=PurchaseDetail.objects.select_related(
                'product',
                'product__category'
            ).prefetch_related(
                'product__categories'
            )
        )
    )

    if 'user_id' in applied_filters:
        purchases_query = purchases_query.filter(
            user_id=applied_filters['user_id'])

    if 'status' in applied_filters:
        purchases_query = purchases_query.filter(
            status=applied_filters['status'])

    if 'start_date' in applied_filters:
        start_datetime = datetime.strptime(
            applied_filters['start_date'], '%Y-%m-%d')
        purchases_query = purchases_query.filter(
            purchase_date__date__gte=start_datetime.date())

    if 'end_date' in applied_filters:
        end_datetime = datetime.strptime(
            applied_filters['end_date'], '%Y-%m-%d')
        purchases_query = purchases_query.filter(
            purchase_date__date__lte=end_datetime.date())

    if 'min_amount' in applied_filters:
        purchases_query = purchases_query.filter(
            total_amount__gte=applied_filters['min_amount'])

    if 'max_amount' in applied_filters:
        purchases_query = purchases_query.filter(
            total_amount__lte=applied_filters['max_amount'])

    if any(key in applied_filters for key in ['product_id', 'brand', 'category_id']):
        if 'product_id' in applied_filters:
            purchases_query = purchases_query.filter(
                details__product_id=applied_filters['product_id'])

        if 'brand' in applied_filters:
            purchases_query = purchases_query.filter(
                details__product__brand__icontains=applied_filters['brand'])

        if 'category_id' in applied_filters:
            purchases_query = purchases_query.filter(
                details__product__categories__id=applied_filters['category_id'])

        purchases_query = purchases_query.distinct()

    # Ordenar por estado (OPEN, PAID, CANCELLED) y fecha descendente
    status_order = models.Case(
        models.When(status=Purchase.Status.OPEN, then=models.Value(1)),
        models.When(status=Purchase.Status.PAID, then=models.Value(2)),
        models.When(status=Purchase.Status.CANCELLED, then=models.Value(3)),
        default=models.Value(4),
        output_field=models.IntegerField()
    )

    purchases_query = purchases_query.annotate(
        status_order=status_order
    ).order_by('status_order', '-purchase_date')

    purchases = list(purchases_query)

    purchases_data = []
    for purchase in purchases:
        user_data = {
            "id": purchase.user.pk,
            "username": purchase.user.username,
            "email": purchase.user.email,
            "first_name": purchase.user.first_name,
            "last_name": purchase.user.last_name,
            "is_staff": purchase.user.is_staff,
            "is_active": purchase.user.is_active
        }

        details_data = []
        for detail in purchase.details.all():
            primary_category = detail.product.get_primary_category()
            category_name = primary_category.name if primary_category else None

            all_categories = [
                {"id": cat.id, "name": cat.name}
                for cat in detail.product.categories.all()
            ]

            detail_data = {
                "id": detail.pk,
                "product": {
                    "id": detail.product.pk,
                    "name": detail.product.name,
                    "brand": detail.product.brand,
                    "model": detail.product.model,
                    "description": detail.product.description,
                    "unit_price": detail.product.unit_price,
                    "main_category": category_name,
                    "all_categories": all_categories
                },
                "quantity": detail.quantity,
                "unit_price_at_purchase": detail.unit_price_at_purchase,
                "subtotal": detail.subtotal,
                "created_at": detail.created_at,
                "updated_at": detail.updated_at
            }
            details_data.append(detail_data)

        purchase_data = {
            "id": purchase.pk,
            "user": user_data,
            "purchase_date": purchase.purchase_date,
            "total_amount": purchase.total_amount,
            "total_installments_count": purchase.total_installments_count,
            "status": purchase.status,
            "discount_applied": purchase.discount_applied,
            "created_at": purchase.created_at,
            "updated_at": purchase.updated_at,
            "created_by": purchase.created_by,
            "updated_by": purchase.updated_by,
            "details": details_data,
            "details_count": len(details_data)
        }
        purchases_data.append(purchase_data)

    return {
        "success": True,
        "message": f"Admin purchases retrieved successfully. Found {len(purchases_data)} purchases.",
        "data": {
            "purchases": purchases_data,
            "count": len(purchases_data),
            "filters_applied": applied_filters
        }
    }


@transaction.atomic
def delete_purchase_admin(purchase_id: int, admin_user_id: int, force_delete: bool = False) -> Dict[str, Any]:
    """
    Elimina una compra del sistema (solo administradores).

    Permite a los administradores eliminar compras del sistema con validaciones de seguridad
    y manejo adecuado del inventario. Al eliminar una compra, se revierten automáticamente
    los movimientos de inventario asociados para restaurar el stock disponible.

    Reglas de Negocio:
        - Solo usuarios administradores pueden eliminar compras
        - Por defecto, solo se pueden eliminar compras con estado OPEN
        - Compras PAID solo se pueden eliminar con force_delete=True (casos excepcionales)
        - Compras CANCELLED pueden eliminarse normalmente
        - Se reversa automáticamente el inventario restoring stock
        - Se registran logs de auditoría para trazabilidad

    Args:
        purchase_id (int): ID de la compra a eliminar
        admin_user_id (int): ID del usuario administrador que realiza la operación
        force_delete (bool): Permite eliminar compras PAID (usar con precaución)

    Returns:
        Dict[str, Any]: Respuesta estándar de la operación:
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (Dict): Información de la eliminación
                - deleted_purchase_id (int): ID de la compra eliminada
                - original_status (str): Estado original de la compra
                - total_amount (Decimal): Monto total de la compra eliminada
                - details_count (int): Cantidad de detalles eliminados
                - inventory_reverted (bool): Si se revirtió el inventario
                - reverted_items (List[Dict]): Lista de productos cuyo stock se restauró

    Raises:
        ValueError: Si el purchase_id es inválido, usuario no es admin, o estado no permite eliminación
        PermissionError: Si el usuario no tiene permisos de administrador
        IntegrityError: Si hay problemas con la reversión de inventario

    Ejemplo de uso:
        # Eliminar compra abierta (normal)
        delete_purchase_admin(purchase_id=123, admin_user_id=1)

        # Eliminar compra pagada (excepcional)
        delete_purchase_admin(purchase_id=456, admin_user_id=1, force_delete=True)
    """
    validate_id(purchase_id, 'Purchase')
    validate_id(admin_user_id, 'User')

    admin_user = get_object_or_404(User, id=admin_user_id)
    if not admin_user.is_staff:
        log_permission_attempt(
            admin_user_id, admin_user.username, "delete", "purchase", purchase_id)
        raise PermissionError("Only staff users can delete purchases")

    purchase = get_object_or_404(
        Purchase.objects.prefetch_related('details__product'),
        id=purchase_id
    )

    if purchase.status == Purchase.Status.PAID and not force_delete:
        raise ValueError(
            "Cannot delete PAID purchase without force_delete=True. "
            "Use force_delete=True only for exceptional cases."
        )

    original_status = purchase.status
    original_total = purchase.total_amount
    original_user = purchase.user
    purchase_details = list(purchase.details.all())

    logger.info(
        f"Admin {admin_user.username} (ID: {admin_user_id}) is deleting purchase "
        f"{purchase_id} (status: {original_status}, amount: {original_total}, "
        f"user: {original_user.username}, force: {force_delete})"
    )

    reverted_items = []
    inventory_reverted = False

    if original_status in [Purchase.Status.OPEN, Purchase.Status.PAID]:
        try:
            from api.inventories.models import InventoryMovement
            from api.storage_location.models import StorageLocation

            for detail in purchase_details:
                related_movements = InventoryMovement.objects.filter(
                    product=detail.product,
                    reason=InventoryMovement.Reason.EXIT_SALE,
                    reference_type=InventoryMovement.RefType.SALE,
                    reference_id=detail.id  # Referencia al PurchaseDetail
                ).select_related('from_location').order_by('-occurred_at')

                if related_movements.exists():
                    last_movement = related_movements.first()

                    if last_movement is not None:
                        target_location = last_movement.from_location  # type: ignore

                        if target_location:
                            expiry_date = getattr(
                                last_movement, 'expiry_date', None)
                            batch_code = getattr(
                                last_movement, 'batch_code', None)

                            revert_result = return_entry_inventory(
                                product=detail.product,
                                to_location=target_location,
                                expiry_date=expiry_date,
                                batch_code=batch_code,
                                description=f"Stock return from deleted purchase ID: {purchase_id}",
                                quantity=detail.quantity,
                                reference_id=purchase_id,
                                user=admin_user  # type: ignore
                            )

                            if revert_result.get("success", False):
                                expiry_date_iso = expiry_date.isoformat() if expiry_date and hasattr(
                                    expiry_date, 'isoformat') else None
                                reverted_items.append({
                                    "product_id": detail.product.id,
                                    "product_name": detail.product.name,
                                    "quantity_restored": detail.quantity,
                                    "location": target_location.name,
                                    "batch_code": batch_code,
                                    "expiry_date": expiry_date_iso
                                })
                            else:
                                logger.error(
                                    f"Failed to revert inventory for product {detail.product.id} "
                                    f"from deleted purchase {purchase_id}: {revert_result.get('message', 'Unknown error')}"
                                )
                        else:
                            logger.warning(
                                f"No source location found for product {detail.product.id} in purchase {purchase_id}")
                else:
                    try:
                        # Obtener la primera ubicación disponible como fallback
                        default_location = StorageLocation.objects.first()
                        if default_location:
                            revert_result = return_entry_inventory(
                                product=detail.product,
                                to_location=default_location,
                                expiry_date=None,
                                batch_code=None,
                                description=f"Stock return from deleted purchase ID: {purchase_id} (fallback location)",
                                quantity=detail.quantity,
                                reference_id=purchase_id,
                                user=admin_user  # type: ignore
                            )

                            if revert_result.get("success", False):
                                reverted_items.append({
                                    "product_id": detail.product.id,
                                    "product_name": detail.product.name,
                                    "quantity_restored": detail.quantity,
                                    "location": default_location.name,
                                    "batch_code": None,
                                    "expiry_date": None,
                                    "note": "Restored to default location (original location not found)"
                                })
                            else:
                                logger.error(
                                    f"Failed to revert inventory to default location for product {detail.product.id}")
                        else:
                            logger.error(
                                "No storage locations available for inventory reversion")
                    except Exception as fallback_error:
                        logger.error(
                            f"Fallback inventory reversion failed: {str(fallback_error)}")

            inventory_reverted = len(reverted_items) > 0

        except Exception as e:
            logger.error(
                f"Error reverting inventory for purchase {purchase_id}: {str(e)}")
            inventory_reverted = False

    # Eliminar la compra (esto eliminará automáticamente los detalles por CASCADE)
    purchase.delete()

    # Log de auditoría después de la eliminación
    logger.info(
        f"Purchase {purchase_id} successfully deleted by admin {admin_user.username}. "
        f"Inventory reverted: {inventory_reverted}, Items restored: {len(reverted_items)}"
    )

    return {
        "success": True,
        "message": f"Purchase {purchase_id} deleted successfully by administrator.",
        "data": {
            "deleted_purchase_id": purchase_id,
            "original_status": original_status,
            "original_user": {
                "id": original_user.id,
                "username": original_user.username,
                "email": original_user.email
            },
            "total_amount": original_total,
            "details_count": len(purchase_details),
            "inventory_reverted": inventory_reverted,
            "reverted_items": reverted_items,
            "deleted_by": {
                "id": admin_user.pk,
                "username": admin_user.username
            },
            "force_delete_used": force_delete,
            "deleted_at": timezone.now().isoformat()
        }
    }


@transaction.atomic
def update_purchase_status(purchase_id: int, new_status: str, user_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Actualiza el estado de una compra con validaciones de negocio.

    Permite cambiar el estado de una compra siguiendo las reglas de negocio establecidas.
    Los usuarios pueden actualizar sus propias compras, mientras que los administradores
    pueden actualizar cualquier compra. Se registran logs de auditoría para trazabilidad.

    Transiciones de Estado Permitidas:
        - OPEN → PAID: Cuando se completa el pago
        - OPEN → CANCELLED: Cuando se cancela la compra
        - CANCELLED → OPEN: Solo administradores (reactivar compra)
        - PAID → CANCELLED: Solo administradores en casos excepcionales

    Args:
        purchase_id (int): ID de la compra a actualizar
        new_status (str): Nuevo estado ['OPEN', 'PAID', 'CANCELLED']
        user_id (int): ID del usuario que realiza la actualización
        reason (Optional[str]): Motivo de la actualización (recomendado para auditoría)

    Returns:
        Dict[str, Any]: Respuesta estándar con información de la actualización:
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (Dict): Información de la actualización
                - purchase_id (int): ID de la compra actualizada
                - previous_status (str): Estado anterior
                - new_status (str): Nuevo estado
                - updated_by (Dict): Información del usuario que actualizó
                - updated_at (str): Timestamp de la actualización
                - reason (str): Motivo de la actualización

    Raises:
        ValueError: Si el estado no es válido o la transición no está permitida
        PermissionError: Si el usuario no tiene permisos para la actualización

    Ejemplo de uso:
        # Usuario marca su compra como pagada
        update_purchase_status(123, 'PAID', user_id=5, reason='Payment completed')

        # Admin cancela una compra
        update_purchase_status(456, 'CANCELLED', user_id=1, reason='Customer request')
    """
    validate_id(purchase_id, 'Purchase')
    validate_id(user_id, 'User')

    valid_statuses = [choice[0] for choice in Purchase.Status.choices]
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

    user = get_object_or_404(User, id=user_id)
    purchase = get_object_or_404(Purchase, id=purchase_id)

    is_admin = user.is_staff
    is_owner = purchase.user.pk == user_id

    if not is_admin and not is_owner:
        raise PermissionError("You can only update your own purchases")

    previous_status = purchase.status

    if previous_status == new_status:
        return {
            "success": True,
            "message": f"Purchase {purchase_id} already has status {new_status}",
            "data": {
                "purchase_id": purchase_id,
                "previous_status": previous_status,
                "new_status": new_status,
                "changed": False
            }
        }

    allowed_transitions = {
        Purchase.Status.OPEN.value: [Purchase.Status.PAID.value, Purchase.Status.CANCELLED.value],
        # Solo admin
        Purchase.Status.PAID.value: [Purchase.Status.CANCELLED.value],
        Purchase.Status.CANCELLED.value: [
            Purchase.Status.OPEN.value]   # Solo admin
    }

    if new_status not in allowed_transitions.get(previous_status, []):
        raise ValueError(
            f"Invalid status transition from {previous_status} to {new_status}. "
            f"Allowed transitions: {allowed_transitions.get(previous_status, [])}"
        )

    if not is_admin:

        if previous_status == Purchase.Status.CANCELLED:
            raise PermissionError(
                "Only administrators can reactivate cancelled purchases")

        if previous_status == Purchase.Status.PAID and new_status == Purchase.Status.CANCELLED:
            raise PermissionError(
                "Only administrators can cancel paid purchases")

    logger.info(
        f"User {user.username} (ID: {user_id}) updating purchase {purchase_id} "
        f"status from {previous_status} to {new_status}. Reason: {reason or 'Not provided'}"
    )

    purchase.status = new_status
    purchase.updated_by = user
    purchase.save(update_fields=['status', 'updated_by', 'updated_at'])

    logger.info(
        f"Purchase {purchase_id} status successfully updated to {new_status}")

    return {
        "success": True,
        "message": f"Purchase {purchase_id} status updated from {previous_status} to {new_status}",
        "data": {
            "purchase_id": purchase_id,
            "previous_status": previous_status,
            "new_status": new_status,
            "updated_by": {
                "id": user.pk,
                "username": user.username,
                "is_admin": is_admin
            },
            "updated_at": purchase.updated_at.isoformat(),
            "reason": reason,
            "changed": True
        }
    }


@transaction.atomic
def update_purchase_installments(purchase_id: int, new_installments_count: int, user_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Actualiza la cantidad de cuotas de una compra.

    Permite modificar el número de cuotas en las que se divide una compra.
    Solo se puede modificar si la compra está en estado OPEN y el usuario
    es el propietario o un administrador.

    Args:
        purchase_id (int): ID de la compra a actualizar
        new_installments_count (int): Nueva cantidad de cuotas (mínimo 1)
        user_id (int): ID del usuario que realiza la actualización
        reason (Optional[str]): Motivo de la actualización

    Returns:
        Dict[str, Any]: Respuesta estándar con información de la actualización

    Raises:
        ValueError: Si la cantidad de cuotas es inválida o la compra no permite modificaciones
        PermissionError: Si el usuario no tiene permisos
    """

    validate_id(purchase_id, 'Purchase')
    validate_id(user_id, 'User')

    if not isinstance(new_installments_count, int) or new_installments_count < 1:
        raise ValueError("Installments count must be a positive integer")

    if new_installments_count > 60:  # Límite razonable
        raise ValueError("Installments count cannot exceed 60")

    user = get_object_or_404(User, id=user_id)
    purchase = get_object_or_404(Purchase, id=purchase_id)

    is_admin = user.is_staff
    is_owner = purchase.user.pk == user_id

    if not is_admin and not is_owner:
        log_permission_attempt(user_id, user.username,
                               "update installments", "purchase", purchase_id)
        raise PermissionError("You can only update your own purchases")

    if purchase.status != Purchase.Status.OPEN:
        raise ValueError("Can only modify installments for OPEN purchases")

    previous_installments = purchase.total_installments_count

    if previous_installments == new_installments_count:
        return {
            "success": True,
            "message": f"Purchase {purchase_id} already has {new_installments_count} installments",
            "data": {
                "purchase_id": purchase_id,
                "previous_installments": previous_installments,
                "new_installments": new_installments_count,
                "changed": False
            }
        }

    # Log antes de la actualización
    logger.info(
        f"User {user.username} (ID: {user_id}) updating purchase {purchase_id} "
        f"installments from {previous_installments} to {new_installments_count}. "
        f"Reason: {reason or 'Not provided'}"
    )

    purchase.total_installments_count = new_installments_count
    purchase.updated_by = user
    purchase.save(
        update_fields=['total_installments_count', 'updated_by', 'updated_at'])

    logger.info(
        f"Purchase {purchase_id} installments successfully updated to {new_installments_count}")

    return {
        "success": True,
        "message": f"Purchase {purchase_id} installments updated from {previous_installments} to {new_installments_count}",
        "data": {
            "purchase_id": purchase_id,
            "previous_installments": previous_installments,
            "new_installments": new_installments_count,
            "updated_by": {
                "id": user.pk,
                "username": user.username,
                "is_admin": is_admin
            },
            "updated_at": purchase.updated_at.isoformat(),
            "reason": reason,
            "changed": True
        }
    }


@transaction.atomic
def update_purchase_discount(purchase_id: int, new_discount: Decimal, user_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Actualiza el descuento aplicado a una compra y recalcula el monto total.

    Permite aplicar o modificar descuentos en una compra. Solo se puede modificar
    si la compra está en estado OPEN. El monto total se recalcula automáticamente
    considerando el nuevo descuento.

    Args:
        purchase_id (int): ID de la compra a actualizar
        new_discount (Decimal): Nuevo descuento a aplicar (0.00 o mayor)
        user_id (int): ID del usuario que realiza la actualización
        reason (Optional[str]): Motivo de la actualización del descuento

    Returns:
        Dict[str, Any]: Respuesta estándar con información de la actualización:
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (Dict): Información de la actualización incluyendo:
                - purchase_id (int): ID de la compra actualizada
                - previous_discount (Decimal): Descuento anterior
                - new_discount (Decimal): Nuevo descuento aplicado
                - previous_total (Decimal): Monto total anterior
                - new_total (Decimal): Nuevo monto total calculado
                - updated_by (Dict): Información del usuario
                - updated_at (str): Timestamp de la actualización

    Raises:
        ValueError: Si el descuento es inválido o la compra no permite modificaciones
        PermissionError: Si el usuario no tiene permisos

    Ejemplo de uso:
        # Aplicar descuento del 10%
        update_purchase_discount(123, Decimal('10.00'), user_id=5, reason='Customer loyalty discount')
    """
    validate_id(purchase_id, 'Purchase')
    validate_id(user_id, 'User')

    if not isinstance(new_discount, Decimal):
        new_discount = Decimal(str(new_discount))

    if new_discount < Decimal('0.00'):
        raise ValueError("Discount cannot be negative")

    user = get_object_or_404(User, id=user_id)
    purchase = get_object_or_404(Purchase, id=purchase_id)

    is_admin = user.is_staff
    is_owner = purchase.user.pk == user_id

    if not is_admin and not is_owner:
        log_permission_attempt(user_id, user.username,
                               "update discount", "purchase", purchase_id)
        raise PermissionError("You can only update your own purchases")

    if purchase.status != Purchase.Status.OPEN:
        raise ValueError("Can only modify discount for OPEN purchases")

    previous_discount = purchase.discount_applied or Decimal('0.00')
    previous_total = purchase.total_amount

    if previous_discount == new_discount:
        return {
            "success": True,
            "message": f"Purchase {purchase_id} already has discount of {new_discount}",
            "data": {
                "purchase_id": purchase_id,
                "previous_discount": str(previous_discount),
                "new_discount": str(new_discount),
                "changed": False
            }
        }

    details = PurchaseDetail.objects.filter(purchase=purchase)
    subtotal = sum(detail.quantity *
                   detail.unit_price_at_purchase for detail in details)

    new_total = subtotal - new_discount

    if new_total < Decimal('0.00'):
        raise ValueError(
            f"Discount of {new_discount} would result in negative total. Maximum discount allowed: {subtotal}")

    logger.info(
        f"User {user.username} (ID: {user_id}) updating purchase {purchase_id} "
        f"discount from {previous_discount} to {new_discount}. "
        f"Total changes from {previous_total} to {new_total}. "
        f"Reason: {reason or 'Not provided'}"
    )

    purchase.discount_applied = new_discount
    purchase.total_amount = new_total
    purchase.updated_by = user
    purchase.save(update_fields=['discount_applied',
                  'total_amount', 'updated_by', 'updated_at'])

    logger.info(
        f"Purchase {purchase_id} discount successfully updated to {new_discount}, new total: {new_total}")

    return {
        "success": True,
        "message": f"Purchase {purchase_id} discount updated from {previous_discount} to {new_discount}",
        "data": {
            "purchase_id": purchase_id,
            "previous_discount": str(previous_discount),
            "new_discount": str(new_discount),
            "previous_total": str(previous_total),
            "new_total": str(new_total),
            "subtotal": str(subtotal),
            "updated_by": {
                "id": user.pk,
                "username": user.username,
                "is_admin": is_admin
            },
            "updated_at": purchase.updated_at.isoformat(),
            "reason": reason,
            "changed": True
        }
    }
