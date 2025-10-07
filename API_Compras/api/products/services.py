from .models import Product, ProductCategory
from api.categories.models import Category
from django.db import transaction, models
from .utils import ProductDataValidator, extract_product_codes, validate_product_data
from typing import Dict, Any, List
from api.utils import validate_id
from api.promotions.models import PromotionScopeProduct, PromotionRule
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from django.contrib.auth import get_user_model

User = get_user_model()


@transaction.atomic
def create_products(data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """
    Crea múltiples productos en la base de datos de forma masiva y transaccional con soporte para múltiples categorías.

    Permite la creación eficiente de múltiples productos validando los datos de entrada,
    verificando la existencia de categorías asociadas y utilizando operaciones masivas
    optimizadas. Cada producto puede tener múltiples categorías a través de la tabla
    intermedia ProductCategory. Toda la operación se ejecuta dentro de una transacción 
    atómica para garantizar la consistencia de datos en caso de errores.

    Proceso:
        - Extrae la lista de productos de los datos de entrada
        - Valida la estructura y contenido de todos los productos
        - Verifica la existencia de todas las categorías referenciadas
        - Prefetch categorías en una sola consulta para optimización
        - Crea objetos Product en memoria sin persistir usando bulk_create
        - Crea relaciones ProductCategory en bulk para cada producto
        - Establece la primera categoría como principal por defecto
        - Retorna estadísticas de creación y productos creados

    Validaciones realizadas:
        - Presencia de la clave 'products' en los datos de entrada
        - Validación completa de datos de productos usando ProductDataValidator
        - Verificación de existencia de todas las categorías
        - Unicidad de códigos de productos
        - Formato correcto de precios y cantidades

    Parámetros:
        data (Dict[str, Any]): Diccionario que debe contener la clave 'products'
            - products (List[Dict[str, Any]]): Lista de diccionarios con datos de productos
                Cada producto debe contener:
                - product_code (str): Código único del producto
                - name (str): Nombre del producto
                - brand (str): Marca del producto (opcional)
                - model (str): Modelo del producto (opcional)
                - unit_price (Decimal/str): Precio unitario
                - category_ids (List[int]): Lista de IDs de categorías asociadas
                - primary_category_id (int, opcional): ID de la categoría principal
        user_id (int): ID del usuario que crea los productos
            Se asigna como created_by y updated_by para auditoría

    Retorna:
        Dict[str, Any]: Diccionario con información de la operación
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - created_count (int): Número total de productos creados
            - products (List[Product]): Lista de instancias Product creadas
            - categories_assigned (int): Total de relaciones producto-categoría creadas

    Excepciones:
        ValueError: Cuando faltan datos requeridos, datos inválidos o categorías inexistentes
        IntegrityError: Por violaciones de restricciones de base de datos
        DatabaseError: Por errores de conexión o transaccionales
    """
    products = data.get('products')
    if products is None:
        raise ValueError("'products' key is missing in input data")

    if not isinstance(products, list) or len(products) == 0:
        raise ValueError("'products' must be a non-empty list")

    required_fields = [
        "product_code", "name", "unit_price", "category_ids"
    ]

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise ValueError(f"User with id {user_id} does not exist")

    for i, product in enumerate(products):
        if not isinstance(product, dict):
            raise ValueError(f"Product at index {i} must be a dictionary")

        if not ProductDataValidator.required_fields(data=product, fields=required_fields):
            missing_fields = [
                field for field in required_fields if field not in product or product[field] is None]
            raise ValueError(
                f"Product at index {i} is missing required fields: {missing_fields}")

        if not isinstance(product.get('category_ids'), list) or len(product.get('category_ids', [])) == 0:
            raise ValueError(
                f"Product at index {i} must have at least one category in 'category_ids' list")

    products_data_valid = True
    validation_errors = []

    for i, product in enumerate(products):

        if not ProductDataValidator.product_code(product['product_code']):
            validation_errors.append(
                f"Product {i}: Invalid product_code format")
            products_data_valid = False

        if not ProductDataValidator.text_field(product['name']):
            validation_errors.append(f"Product {i}: Invalid name format")
            products_data_valid = False

        if 'brand' in product and product['brand'] and not ProductDataValidator.text_field(product['brand']):
            validation_errors.append(f"Product {i}: Invalid brand format")
            products_data_valid = False

        if 'model' in product and product['model'] and not ProductDataValidator.text_field(product['model']):
            validation_errors.append(f"Product {i}: Invalid model format")
            products_data_valid = False

        if not ProductDataValidator.price(product['unit_price']):
            validation_errors.append(f"Product {i}: Invalid unit_price format")
            products_data_valid = False

        category_ids = product['category_ids']
        for cat_id in category_ids:
            if not ProductDataValidator.positive_integer(cat_id):
                validation_errors.append(
                    f"Product {i}: Invalid category_id {cat_id}")
                products_data_valid = False

        primary_cat_id = product.get('primary_category_id')
        if primary_cat_id is not None:
            if not ProductDataValidator.positive_integer(primary_cat_id):
                validation_errors.append(
                    f"Product {i}: Invalid primary_category_id format")
                products_data_valid = False
            elif primary_cat_id not in category_ids:
                validation_errors.append(
                    f"Product {i}: primary_category_id must be in category_ids list")
                products_data_valid = False

    if not products_data_valid:
        raise ValueError("Validation errors found: " +
                         "; ".join(validation_errors))

    all_category_ids = set()
    for product in products:
        all_category_ids.update(product['category_ids'])

    existing_categories = Category.objects.filter(id__in=all_category_ids)
    existing_category_ids = set(
        existing_categories.values_list('id', flat=True))

    missing_category_ids = all_category_ids - existing_category_ids
    if missing_category_ids:
        raise ValueError(
            f"The following category IDs do not exist: {list(missing_category_ids)}")

    product_codes = [prod['product_code'] for prod in products]
    if len(product_codes) != len(set(product_codes)):
        duplicates = [code for code in set(
            product_codes) if product_codes.count(code) > 1]
        raise ValueError(f"Duplicate product codes found: {duplicates}")

    existing_codes = Product.objects.filter(
        product_code__in=product_codes).values_list('product_code', flat=True)
    if existing_codes:
        raise ValueError(
            f"The following product codes already exist: {list(existing_codes)}")

    category_map = {cat.id: cat for cat in existing_categories}

    products_to_create = []
    for product_data in products:
        products_to_create.append(Product(
            product_code=product_data['product_code'],
            name=product_data['name'],
            brand=product_data.get('brand', ''),
            model=product_data.get('model', ''),
            unit_price=Decimal(str(product_data['unit_price'])),
            created_by=user,
            updated_by=user
        ))

    created_products = Product.objects.bulk_create(
        products_to_create,
        batch_size=1000,
        ignore_conflicts=False
    )

    product_codes_created = [prod.product_code for prod in products_to_create]
    created_products_with_ids = Product.objects.filter(
        product_code__in=product_codes_created
    ).order_by('id')

    product_code_to_obj = {
        prod.product_code: prod for prod in created_products_with_ids}

    product_categories_to_create = []
    total_categories_assigned = 0

    for i, product_data in enumerate(products):
        created_product = product_code_to_obj[product_data['product_code']]
        category_ids = product_data['category_ids']
        primary_category_id = product_data.get(
            'primary_category_id', category_ids[0])

        for cat_id in category_ids:
            product_categories_to_create.append(ProductCategory(
                product=created_product,
                category=category_map[cat_id],
                is_primary=(cat_id == primary_category_id),
                assigned_by=user
            ))
            total_categories_assigned += 1

    ProductCategory.objects.bulk_create(
        product_categories_to_create,
        batch_size=1000,
        ignore_conflicts=False
    )

    for product in created_products_with_ids:
        product.refresh_from_db()

        if hasattr(product, '_prefetched_objects_cache'):
            product._prefetched_objects_cache = {}

    return {
        "success": True,
        "message": f"Successfully created {len(created_products_with_ids)} products with {total_categories_assigned} category associations",
        "created_count": len(created_products_with_ids),
        "products": list(created_products_with_ids),
        "categories_assigned": total_categories_assigned
    }


@transaction.atomic
def partial_update_product(product_id: int, data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """
    Actualiza parcialmente un producto existente en la base de datos con soporte para múltiples categorías.

    Permite la actualización de campos específicos de un producto sin necesidad
    de enviar todos los campos. Solo los campos proporcionados en el diccionario
    de datos serán actualizados. La operación se ejecuta dentro de una transacción
    atómica para garantizar la consistencia de datos.

    Proceso:
        - Busca el producto por ID y verifica su existencia
        - Valida los datos de entrada según el tipo de campo
        - Verifica la existencia de categorías si se proporciona category_ids
        - Actualiza solo los campos proporcionados en los datos
        - Maneja relaciones ProductCategory para múltiples categorías
        - Actualiza automáticamente el campo updated_by con el usuario actual
        - Guarda los cambios en la base de datos

    Validaciones realizadas:
        - Existencia del producto por ID
        - Validación de formato para campos de texto usando patrones regex
        - Validación de rango para unit_price (debe ser positivo y menor a 1,000,000,000)
        - Verificación de existencia de categorías si se proporciona category_ids
        - Validación de primary_category_id dentro de category_ids
        - Validación de unicidad para product_code si se actualiza

    Parámetros:
        product_id (int): ID del producto a actualizar
        data (Dict[str, Any]): Diccionario con los campos a actualizar
            Campos opcionales:
            - product_code (str): Nuevo código del producto
            - name (str): Nuevo nombre del producto
            - brand (str): Nueva marca del producto
            - model (str): Nuevo modelo del producto
            - unit_price (Decimal/str/float): Nuevo precio unitario
            - category_ids (List[int]): Lista de IDs de las nuevas categorías
            - primary_category_id (int, opcional): ID de la categoría principal
        user_id (int): ID del usuario que realiza la actualización

    Retorna:
        Dict[str, Any]: Diccionario con información de la operación
            - success (bool): True si la actualización fue exitosa
            - product (Product): Instancia del producto actualizado
            - updated_fields (List[str]): Lista de campos que fueron actualizados
            - categories_updated (bool): True si se actualizaron las categorías

    Excepciones:
        ValueError: Cuando el producto no existe, datos inválidos o categorías inexistentes
        IntegrityError: Por violaciones de restricciones de base de datos (ej: product_code duplicado)
        DatabaseError: Por errores de conexión o transaccionales
    """
    try:
        validate_id(product_id, "product_id")

        product = Product.objects.select_for_update().get(id=product_id)
    except Product.DoesNotExist:
        raise ValueError(f"Product with id {product_id} does not exist")

    if not data:
        raise ValueError("No data provided for update")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise ValueError(f"User with id {user_id} does not exist")

    updated_fields = []
    categories_updated = False

    if 'category_ids' in data:
        category_ids = data['category_ids']

        if not isinstance(category_ids, list) or len(category_ids) == 0:
            raise ValueError("'category_ids' must be a non-empty list")

        for cat_id in category_ids:
            if not ProductDataValidator.positive_integer(cat_id):
                raise ValueError(f"Invalid category_id: {cat_id}")

        existing_categories = Category.objects.filter(id__in=category_ids)
        existing_category_ids = set(
            existing_categories.values_list('id', flat=True))

        missing_category_ids = set(category_ids) - existing_category_ids
        if missing_category_ids:
            raise ValueError(
                f"The following category IDs do not exist: {list(missing_category_ids)}")

        primary_category_id = data.get('primary_category_id')
        if primary_category_id is not None:
            if not ProductDataValidator.positive_integer(primary_category_id):
                raise ValueError("Invalid primary_category_id format")
            elif primary_category_id not in category_ids:
                raise ValueError(
                    "primary_category_id must be in category_ids list")
        else:
            primary_category_id = category_ids[0]

    if 'product_code' in data and not ProductDataValidator.product_code(data['product_code']):
        raise ValueError("Invalid product_code format")

    if 'name' in data and not ProductDataValidator.text_field(data['name']):
        raise ValueError("Invalid name format")

    if 'brand' in data and data['brand'] and not ProductDataValidator.text_field(data['brand']):
        raise ValueError("Invalid brand format")

    if 'model' in data and data['model'] and not ProductDataValidator.text_field(data['model']):
        raise ValueError("Invalid model format")

    if 'unit_price' in data and not ProductDataValidator.price(data['unit_price']):
        raise ValueError("Invalid unit_price format")

    if 'product_code' in data:
        value = data['product_code']
        if value != product.product_code:
            existing_product = Product.objects.filter(
                product_code=value
            ).exclude(id=product_id).first()
            if existing_product:
                raise ValueError(f"Product code '{value}' already exists")

            product.product_code = value
            updated_fields.append('product_code')

    text_fields = ['name', 'brand', 'model']
    for field in text_fields:
        if field in data:
            setattr(product, field, data[field])
            updated_fields.append(field)

    if 'unit_price' in data:
        from decimal import Decimal
        product.unit_price = Decimal(str(data['unit_price']))
        updated_fields.append('unit_price')

    if 'category_ids' in data:
        category_ids = data['category_ids']
        primary_category_id = data.get('primary_category_id', category_ids[0])

        ProductCategory.objects.filter(product=product).delete()

        categories_for_update = Category.objects.filter(id__in=category_ids)
        category_map = {cat.pk: cat for cat in categories_for_update}

        product_categories_to_create = []
        for cat_id in category_ids:
            product_categories_to_create.append(ProductCategory(
                product=product,
                category=category_map[cat_id],
                is_primary=(cat_id == primary_category_id),
                assigned_by=user
            ))

        ProductCategory.objects.bulk_create(product_categories_to_create)

        updated_fields.append('categories')
        categories_updated = True

    elif 'primary_category_id' in data:
        primary_category_id = data['primary_category_id']

        try:
            primary_category = Category.objects.get(id=primary_category_id)
        except Category.DoesNotExist:
            raise ValueError(
                f"Category with id {primary_category_id} does not exist")

        try:
            product.set_primary_category(primary_category, user=user)
            updated_fields.append('primary_category')
            categories_updated = True
        except ValueError as e:
            raise ValueError(f"Cannot set primary category: {str(e)}")

        product.refresh_from_db()
        if hasattr(product, '_prefetched_objects_cache'):
            product._prefetched_objects_cache = {}

    if updated_fields:
        product.updated_by = user
        product.save()

    return {
        "success": True,
        "product": product,
        "updated_fields": updated_fields,
        "categories_updated": categories_updated
    }


def get_all_products_with_promotions() -> list[dict[str, Any]]:
    """
    Obtiene todos los productos con sus promociones activas asociadas.

    Utiliza optimizaciones de consultas para evitar el problema N+1 y 
    prefetch de datos relacionados para mejorar el rendimiento. Solo
    incluye promociones activas con reglas vigentes.

    Returns:
        list[dict[str, Any]]: Lista de diccionarios con datos de productos y sus promociones activas

    Optimizaciones aplicadas:
        - prefetch_related para categorías múltiples optimizado
        - Prefetch optimizado para promociones y reglas activas
        - Filtrado a nivel de base de datos para promociones activas
        - Agrupación eficiente de datos en memoria
    """

    products = Product.objects.prefetch_related(
        'categories',
        'productcategory_set'
    ).order_by("brand")

    current_time = timezone.now()

    promotions_scope = PromotionScopeProduct.objects.select_related(
        'promotion', 'product'
    ).prefetch_related(
        models.Prefetch(
            'promotion__promotionrule_set',
            queryset=PromotionRule.objects.filter(
                start_at__lte=current_time,
                end_at__gte=current_time
            ),
            to_attr='active_rules'
        )
    ).filter(
        promotion__active=True,
        promotion__promotionrule__start_at__lte=current_time,
        promotion__promotionrule__end_at__gte=current_time
    )

    all_products_with_promotions = extract_product_codes(
        products, promotions_scope)

    return all_products_with_promotions


def get_product_by_filter(**filters):
    """
    Filtra productos por un único criterio y retorna sus promociones activas.
    Adaptado para funcionar con múltiples categorías por producto.

    Permite buscar productos usando un filtro permitido (id, product_code, name, brand, model, 
    unit_price, min_price, max_price, category_id, primary_category_only).
    Valida el formato de los datos y retorna los productos encontrados junto con sus promociones activas.

    Parámetros:
        filters: Filtros de búsqueda permitidos.
            - category_id: Busca productos que tengan esta categoría (cualquiera, no solo principal)
            - primary_category_only: Si True con category_id, busca solo en categorías principales

    Retorna:
        Dict con éxito, mensaje y datos de productos con promociones activas.

    Excepciones:
        ValueError: Si el filtro es inválido, faltan parámetros o hay errores de formato.
    """
    try:
        permitted_filters = ['id', 'category_id', 'product_code', 'name',
                             'brand', 'model', 'unit_price', 'min_price', 'max_price', 'primary_category_only']

        for key in filters.keys():
            if key not in permitted_filters:
                raise ValueError(
                    f"Filter '{key}' is not permitted, allowed filters are {permitted_filters}")
        count = 0
        for key in filters.keys():
            if filters[key] is not None and key != 'primary_category_only':
                count += 1

        if count > 1:
            raise ValueError("Only one filter can be applied at a time")

        base_queryset = Product.objects.prefetch_related(
            'categories', 'productcategory_set'
        )

        if 'id' in filters:
            # Coerce potential string to int
            try:
                filters['id'] = int(filters['id'])
            except (TypeError, ValueError):
                pass
            validate_id(filters['id'], 'product_id')
            products = base_queryset.filter(id=filters['id']).order_by('id')
            filter_by = 'id'

        elif 'category_id' in filters:
            # Coerce potential string to int
            try:
                filters['category_id'] = int(filters['category_id'])
            except (TypeError, ValueError):
                pass
            validate_id(filters['category_id'], 'category_id')

            primary_only = filters.get('primary_category_only', False)

            if primary_only:

                products = base_queryset.filter(
                    productcategory__category_id=filters['category_id'],
                    productcategory__is_primary=True
                ).order_by('name')
                filter_by = 'primary_category_id'
            else:
                products = base_queryset.filter(
                    categories__id=filters['category_id']
                ).distinct().order_by('name')
                filter_by = 'category_id'

        elif 'product_code' in filters:
            if not ProductDataValidator.product_code(filters['product_code']):
                raise ValueError("Invalid product_code format")
            products = base_queryset.filter(
                product_code=filters['product_code']
            ).order_by('product_code')
            filter_by = 'product_code'

        elif 'name' in filters:
            if not ProductDataValidator.text_field(filters['name']):
                raise ValueError("Invalid name format")
            products = base_queryset.filter(
                name__icontains=filters['name']
            ).order_by('name')
            filter_by = 'name'

        elif 'brand' in filters:
            if not ProductDataValidator.text_field(filters['brand']):
                raise ValueError("Invalid brand format")
            products = base_queryset.filter(
                brand__icontains=filters['brand']
            ).order_by('brand', 'name')
            filter_by = 'brand'

        elif 'model' in filters:
            if not ProductDataValidator.text_field(filters['model']):
                raise ValueError("Invalid model format")
            products = base_queryset.filter(
                model__icontains=filters['model']
            ).order_by('model', 'name')
            filter_by = 'model'

        elif 'unit_price' in filters:
            if not ProductDataValidator.price(filters['unit_price']):
                raise ValueError("Invalid unit_price format")
            try:
                filters['unit_price'] = Decimal(str(filters['unit_price']))
            except (ValueError, InvalidOperation):
                raise ValueError("Invalid unit_price format")
            products = base_queryset.filter(
                unit_price=filters['unit_price']
            ).order_by('unit_price', 'name')
            filter_by = 'unit_price'

        elif 'min_price' in filters:
            if not ProductDataValidator.price(filters['min_price']):
                raise ValueError("Invalid min_price format")
            try:
                filters['min_price'] = Decimal(str(filters['min_price']))
            except (ValueError, InvalidOperation):
                raise ValueError("Invalid min_price format")
            products = base_queryset.filter(
                unit_price__gte=Decimal(str(filters['min_price']))
            ).order_by('unit_price', 'name')
            filter_by = 'min_price'

        elif 'max_price' in filters:
            if not ProductDataValidator.price(filters['max_price']):
                raise ValueError("Invalid max_price format")
            try:
                filters['max_price'] = Decimal(str(filters['max_price']))
            except (ValueError, InvalidOperation):
                raise ValueError("Invalid max_price format")
            products = base_queryset.filter(
                unit_price__lte=Decimal(str(filters['max_price']))
            ).order_by('unit_price', 'name')
            filter_by = 'max_price'

        else:
            raise ValueError(
                "At least one filter (id, category_id, product_code, name, brand, model, unit_price, min_price, max_price) must be provided")

        current_time = timezone.now()

        products_filter_id = [product.pk for product in products]

        promotions_scope = PromotionScopeProduct.objects.select_related(
            'promotion', 'product'
        ).prefetch_related(
            models.Prefetch(
                'promotion__promotionrule_set',
                queryset=PromotionRule.objects.filter(
                    start_at__lte=current_time,
                    end_at__gte=current_time
                ),
                to_attr='active_rules'
            )
        ).filter(
            product_id__in=products_filter_id,
            promotion__active=True,
            promotion__promotionrule__start_at__lte=current_time,
            promotion__promotionrule__end_at__gte=current_time
        )
        products_with_promotions = extract_product_codes(
            products, promotions_scope)
        return {"success": True,
                "message": f"Filter by {filter_by} applied successfully",
                "data":  products_with_promotions
                }
    except KeyError as e:
        raise ValueError(f"Missing filter parameter: {str(e)}")
