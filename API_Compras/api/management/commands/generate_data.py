from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal
import random
import time
from datetime import datetime, timedelta
import pytz
from contextlib import contextmanager

from api.categories.models import Category
from api.products.models import Product, ProductCategory
from api.storage_location.models import StorageLocation
from api.inventories.models import InventoryRecord, InventoryMovement, StockSnapshot
from api.purchases.models import Purchase, PurchaseDetail
from api.payments.models import Payment, Installment, InstallmentAuditLog
from api.promotions.models import (
    Promotion, PromotionScopeCategory, PromotionScopeProduct,
    PromotionScopeLocation, PromotionRule
)
from api.models import NotificationTemplate
from api.constants import NotificationCodes
"""
Comando de gestión Django para generar datos de prueba masivos.

Genera datos completos para todos los modelos del sistema (excepto notificaciones)
con fechas distribuidas uniformemente entre 2021-01-01 y 2025-10-01.

Uso:
    python manage.py generate_data  # Configuración por defecto
    python manage.py generate_data --products 1000 --users 500 --purchases 2000 --movements 5000 --clear
    python manage.py generate_data --clear  # Limpia datos existentes antes de generar

Modelos incluidos:
    - Usuarios (CustomUser)
    - Categorías (Category)
    - Productos (Product) + relaciones con categorías
    - Ubicaciones de almacén (StorageLocation)
    - Inventarios (InventoryRecord)
    - Movimientos de inventario (InventoryMovement)
    - Templates de notificación (NotificationTemplate)
    - Promociones (Promotion) + alcances y reglas
    - Compras (Purchase) + detalles
    - Pagos (Payment) + cuotas (Installment)
    - Auditoría de cuotas (InstallmentAuditLog)
    - Snapshots de inventario (StockSnapshot)

RANGO TEMPORAL: Todos los registros con timestamp se generan entre 2021-01-01 y 2025-10-01
para proveer un espectro amplio para generar gráficas analíticas.
"""


@contextmanager
def disable_auto_now_add(*models):
    """
    Context manager que temporalmente deshabilita auto_now_add en modelos específicos.

    Permite asignar fechas manuales a campos que normalmente usan auto_now_add=True.
    Útil para generar datos de prueba con fechas históricas específicas.

    Args:
        *models: Modelos de Django donde deshabilitar auto_now_add

    Usage:
        with disable_auto_now_add(InventoryMovement, Purchase):
            # Crear objetos con fechas manuales
            movement = InventoryMovement(created_at=custom_date, ...)
    """
    original_values = {}

    try:
        # Deshabilitar auto_now_add temporalmente
        for model in models:
            for field in model._meta.fields:
                if hasattr(field, 'auto_now_add') and field.auto_now_add:
                    original_values[(model, field.name)] = field.auto_now_add
                    field.auto_now_add = False

        yield

    finally:
        # Restaurar valores originales
        for (model, field_name), original_value in original_values.items():
            field = model._meta.get_field(field_name)
            field.auto_now_add = original_value


class Command(BaseCommand):
    help = 'Genera datos de prueba masivos para el sistema - rango temporal 2021 a 2025-10-01'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.User = get_user_model()
        self.external_ref_counter = 0

        # 🗓️ Rango temporal unificado: 2021 → 2025-10-01
        self.START_DATE = datetime(2021, 1, 1, tzinfo=pytz.UTC)
        self.END_DATE = datetime(2025, 10, 1, tzinfo=pytz.UTC)
        self.DELTA_DAYS = (self.END_DATE - self.START_DATE).days

    def _generate_unique_external_ref(self):
        """Genera una referencia externa única."""
        self.external_ref_counter += 1
        # Últimos 6 dígitos del timestamp
        timestamp = int(time.time() * 1000) % 1000000
        return f'REF{timestamp:06d}{self.external_ref_counter:04d}'

    def _random_date_between(self, start_date, end_date):
        """Genera una fecha aleatoria entre dos fechas específicas."""
        if start_date >= end_date:
            return start_date

        delta_days = (end_date - start_date).days
        if delta_days <= 0:
            return start_date

        random_days = random.randint(0, delta_days)
        return start_date + timedelta(days=random_days)

    def _random_date_in_range(self):
        """Genera una fecha aleatoria en el rango temporal definido."""
        random_days = random.randint(0, self.DELTA_DAYS)
        return self.START_DATE + timedelta(days=random_days)

    def add_arguments(self, parser):
        parser.add_argument('--products', type=int, default=500)
        parser.add_argument('--users', type=int, default=100)
        parser.add_argument('--purchases', type=int, default=200)
        parser.add_argument('--movements', type=int, default=1000)
        parser.add_argument('--clear', action='store_true')

    def handle(self, *args, **options):
        # Verificar si signals están deshabilitados
        from django.conf import settings
        if settings.DISABLE_SIGNALS:
            self.stdout.write(self.style.SUCCESS(
                '🔕 Signals DESHABILITADOS - No se enviarán emails'))
        else:
            self.stdout.write(self.style.WARNING(
                '⚠️  Signals HABILITADOS - Se intentarán enviar emails'))
            self.stdout.write(self.style.WARNING(
                '💡 Para deshabilitar: $env:DISABLE_SIGNALS="True" (PowerShell) o set DISABLE_SIGNALS=True (CMD)'))

        # Verificar conexión a Redis
        try:
            cache.set("test_connection", "ok", timeout=5)
            if cache.get("test_connection") == "ok":
                self.stdout.write(self.style.SUCCESS(
                    "Redis conectado exitosamente - usando Redis como cache"))
            else:
                self.stdout.write(self.style.WARNING(
                    "Redis no parece estar operativo"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"No se pudo conectar a Redis: {e}"))

        start_time = time.time()
        self.stdout.write(self.style.SUCCESS(
            f'Iniciando generación de datos (rango: {self.START_DATE.date()} → {self.END_DATE.date()})...'))

        if options['products'] < 400:
            options['products'] = 400
            self.stdout.write(self.style.WARNING(
                'Ajustando productos a mínimo 400'))

        if options['clear']:
            clear_start = time.time()
            self._clear_data()
            self.stdout.write(
                f'Limpieza completada en {time.time() - clear_start:.2f} segundos')

        try:
            with transaction.atomic():
                # Deshabilitar auto_now_add para permitir fechas manuales
                with disable_auto_now_add(
                    InventoryMovement, InventoryRecord, StockSnapshot,
                    Purchase, PurchaseDetail, Payment, Installment,
                    Promotion, PromotionScopeCategory, PromotionScopeProduct,
                    PromotionScopeLocation, PromotionRule, Product, ProductCategory,
                    StorageLocation, Category, NotificationTemplate
                ):
                    total_steps = 13
                    current_step = 0

                    for func, label in [
                        (lambda: self._generate_users(
                            options['users']), "Usuarios"),
                        (self._generate_categories, "Categorías"),
                        (lambda: self._generate_products(
                            options['products']), "Productos"),
                        (self._generate_storage_locations, "Ubicaciones"),
                        (self._generate_inventories, "Inventarios"),
                        (lambda: self._generate_inventory_movements(
                            options['movements']), "Movimientos"),
                        (self._generate_notification_templates,
                         "Templates Notificación"),
                        (self._generate_promotions, "Promociones"),
                        (self._generate_promotion_scopes, "Alcance Promociones"),
                        (lambda: self._generate_purchases(
                            options['purchases']), "Compras"),
                        (self._generate_payments, "Pagos"),
                        (self._generate_installment_audit_logs, "Auditoría Cuotas"),
                        (self._generate_stock_snapshots, "Snapshots Inventario"),
                    ]:
                        current_step += 1
                        step_start = time.time()

                        self.stdout.write(
                            f'\n[{current_step}/{total_steps}] Iniciando: {label}...')
                        func()

                        step_duration = time.time() - step_start
                        elapsed_total = time.time() - start_time

                        self.stdout.write(
                            f'[{current_step}/{total_steps}] {label}: {step_duration:.2f}s | Total transcurrido: {elapsed_total:.2f}s')

                        # Estimación de tiempo restante
                        if current_step > 0:
                            avg_time_per_step = elapsed_total / current_step
                            remaining_steps = total_steps - current_step
                            estimated_remaining = avg_time_per_step * remaining_steps
                            self.stdout.write(
                                f'Tiempo estimado restante: {estimated_remaining:.2f}s')

            self._show_summary()
            total_duration = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(
                f'Datos generados exitosamente en {total_duration:.2f} segundos'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error generando datos: {str(e)}'))
            raise

    # Limpieza de datos previos
    def _clear_data(self):
        self.stdout.write('Limpiando datos existentes...')

        # Orden de limpieza respetando dependencias
        StockSnapshot.objects.all().delete()
        InstallmentAuditLog.objects.all().delete()
        Payment.objects.all().delete()
        Installment.objects.all().delete()
        PurchaseDetail.objects.all().delete()
        Purchase.objects.all().delete()

        # Promociones y sus relaciones
        PromotionRule.objects.all().delete()
        PromotionScopeLocation.objects.all().delete()
        PromotionScopeProduct.objects.all().delete()
        PromotionScopeCategory.objects.all().delete()
        Promotion.objects.all().delete()

        # Inventarios
        InventoryMovement.objects.all().delete()
        InventoryRecord.objects.all().delete()

        # Productos y categorías
        ProductCategory.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()

        # Ubicaciones (sublocaciones primero)
        StorageLocation.objects.filter(parent__isnull=False).delete()
        StorageLocation.objects.filter(parent__isnull=True).delete()

        # Templates de notificación
        NotificationTemplate.objects.all().delete()

        # Usuarios (preservar superusers)
        deleted_users = self.User.objects.filter(is_superuser=False).delete()
        self.stdout.write(
            f'✅ {deleted_users[0]} usuarios eliminados (superusers preservados)')
        self.stdout.write('🎯 Limpieza completa terminada')

    # 👥 Usuarios
    def _generate_users(self, count):
        from django.contrib.auth.hashers import make_password
        self.stdout.write(f'👥 Generando {count} usuarios...')
        hashed_password = make_password('testpass123')
        batch_size = 1000
        total_created = 0

        for start in range(0, count, batch_size):
            users = []
            for i in range(start, min(start + batch_size, count)):
                # 📅 Fechas de creación distribuidas en todo el rango
                date_joined = self._random_date_in_range()

                user = self.User(
                    username=f'user_{i+1:04d}',
                    email=f'user_{i+1:04d}@example.com',
                    first_name=random.choice(
                        ['Ana', 'Carlos', 'María', 'José', 'Laura', 'Miguel']),
                    last_name=random.choice(
                        ['García', 'Rodríguez', 'González', 'Fernández']),
                    is_active=True,
                    password=hashed_password,
                    date_joined=date_joined
                )
                users.append(user)

            batch_start = time.time()
            self.User.objects.bulk_create(users, batch_size=100)
            total_created += len(users)
            self.stdout.write(
                f'📊 Lote {start // batch_size + 1}: {len(users)} usuarios en {time.time() - batch_start:.2f}s')

        self.stdout.write(f'✅ {total_created} usuarios creados')

    # 📂 Categorías
    def _generate_categories(self):
        self.stdout.write('📂 Generando categorías...')
        categories = [
            'Electrónicos', 'Ropa y Moda', 'Hogar y Jardín', 'Deportes', 'Libros y Medios', 'Salud y Belleza',
            'Automóvil', 'Alimentación', 'Smartphones', 'Laptops', 'Tablets', 'Audio',
            'Hombre', 'Mujer', 'Niños', 'Calzado', 'Muebles', 'Decoración', 'Cocina',
            'Jardín', 'Fitness', 'Fútbol', 'Running', 'Natación'
        ]

        category_objects = []
        for category_name in categories:
            created_at = self._random_date_in_range()
            category_objects.append(
                Category(name=category_name, created_at=created_at)
            )

        with disable_auto_now_add(Category):
            Category.objects.bulk_create(
                category_objects, ignore_conflicts=True)
        self.stdout.write(f'✅ {len(categories)} categorías creadas')

    # 📧 Templates de Notificación
    def _generate_notification_templates(self):
        self.stdout.write('📧 Generando templates de notificación...')
        user = self.User.objects.filter(is_superuser=True).first()

        templates = [
            {
                'code': NotificationCodes.PURCHASE_CONFIRMED,
                'subject': 'Compra Confirmada',
                'head_html': '<h1>¡Gracias por tu compra!</h1>',
                'footer_html': '<p>Tu compra ha sido confirmada exitosamente. Saludos, El equipo</p>'
            },
            {
                'code': NotificationCodes.INSTALLMENT_DUE_7D,
                'subject': 'Cuota vence en 7 días',
                'head_html': '<h1>Recordatorio de Pago</h1>',
                'footer_html': '<p>Tu cuota vence en 7 días. Saludos, El equipo</p>'
            },
            {
                'code': NotificationCodes.INSTALLMENT_PAID,
                'subject': 'Cuota Pagada',
                'head_html': '<h1>Pago Confirmado</h1>',
                'footer_html': '<p>Hemos recibido tu pago. Saludos, El equipo</p>'
            },
            {
                'code': NotificationCodes.PAYMENT_ERROR,
                'subject': 'Error en Pago',
                'head_html': '<h1>Error en el Procesamiento</h1>',
                'footer_html': '<p>Ha ocurrido un error con tu pago. Saludos, El equipo</p>'
            },
            {
                'code': NotificationCodes.OVERDUE_NOTICE,
                'subject': 'Aviso de Vencimiento',
                'head_html': '<h1>Cuota Vencida</h1>',
                'footer_html': '<p>Tu cuota está vencida. Saludos, El equipo</p>'
            },
            {
                'code': NotificationCodes.CREATED_ACCOUNT,
                'subject': 'Cuenta Creada',
                'head_html': '<h1>¡Bienvenido!</h1>',
                'footer_html': '<p>Tu cuenta ha sido creada exitosamente. Saludos, El equipo</p>'
            }
        ]

        notification_templates = [
            NotificationTemplate(
                code=template['code'],
                subject=template['subject'],
                head_html=template['head_html'],
                footer_html=template['footer_html'],
                active=True,
                created_by=user,
                updated_by=user,
                created_at=self._random_date_in_range()
            )
            for template in templates
        ]

        with disable_auto_now_add(NotificationTemplate):
            NotificationTemplate.objects.bulk_create(
                notification_templates, ignore_conflicts=True)
        self.stdout.write(
            f'✅ {len(notification_templates)} templates de notificación creados')

    # 🏪 Ubicaciones
    def _generate_storage_locations(self):
        self.stdout.write('🏪 Generando ubicaciones de almacenamiento...')
        user = self.User.objects.filter(is_superuser=True).first()
        warehouses = ['Almacén Central', 'Almacén Norte',
                      'Almacén Sur', 'Depósito Este', 'Centro Logístico']

        locations = []
        for name in warehouses:
            created_at = self._random_date_in_range()
            locations.append(
                StorageLocation(
                    name=name, street=f'Calle {name}', street_number=str(random.randint(100, 9999)),
                    state='Buenos Aires', city='CABA', country='Argentina', type='WH',
                    created_by=user, updated_by=user, created_at=created_at
                )
            )

        with disable_auto_now_add(StorageLocation):
            StorageLocation.objects.bulk_create(locations, batch_size=100)
        parents = list(StorageLocation.objects.filter(type='WH'))

        sublocations = []
        for parent in parents:
            for zone in ['A', 'B', 'C', 'D']:
                created_at = self._random_date_between(
                    parent.created_at, self.END_DATE)
                sublocations.append(
                    StorageLocation(
                        name=f'{parent.name}-Zona-{zone}', street=parent.street, street_number=parent.street_number,
                        floor_unit=f'Zona {zone}', state=parent.state, city=parent.city, country=parent.country,
                        type='SB', parent=parent, created_by=user, updated_by=user, created_at=created_at
                    )
                )

        with disable_auto_now_add(StorageLocation):
            StorageLocation.objects.bulk_create(sublocations, batch_size=100)
        self.stdout.write(
            f'✅ {len(locations) + len(sublocations)} ubicaciones creadas')

    def _generate_products(self, count):
        """Genera productos diversos."""
        self.stdout.write(f'📦 Generando {count} productos...')

        categories = list(Category.objects.all())
        users = list(self.User.objects.filter(
            is_superuser=True)[:1]) or [None]

        # Plantillas de productos por categoría
        product_templates = {
            'Smartphones': [
                ('iPhone 15 Pro', 1200, 'Smartphone premium con chip A17'),
                ('Samsung Galaxy S24', 1000, 'Android flagship con cámara avanzada'),
                ('Xiaomi Mi 13', 600, 'Smartphone con excelente relación calidad-precio'),
                ('Google Pixel 8', 800, 'Smartphone con IA avanzada'),
                ('OnePlus 11', 700, 'Smartphone gaming de alta gama')
            ],
            'Laptops': [
                ('MacBook Air M2', 1300, 'Laptop ultraligera para profesionales'),
                ('Dell XPS 13', 1100, 'Laptop premium Windows'),
                ('ThinkPad X1 Carbon', 1400, 'Laptop empresarial robusta'),
                ('ASUS ROG Gaming', 1600, 'Laptop para gaming de alta gama'),
                ('HP Pavilion', 800, 'Laptop versátil para uso general')
            ],
            'Hombre': [
                ('Camisa Formal', 45, 'Camisa de vestir de algodón'),
                ('Jeans Clásicos', 60, 'Pantalones vaqueros de mezclilla'),
                ('Chaqueta Casual', 120, 'Chaqueta ligera para entretiempo'),
                ('Polo Sport', 35, 'Polo deportivo de algodón'),
                ('Traje Ejecutivo', 300, 'Traje completo para eventos formales')
            ],
            'Mujer': [
                ('Vestido Elegante', 80, 'Vestido para ocasiones especiales'),
                ('Blusa Seda', 65, 'Blusa de seda natural'),
                ('Pantalón Ejecutivo', 70, 'Pantalón formal para oficina'),
                ('Falda Midi', 45, 'Falda de longitud media'),
                ('Chaqueta Blazer', 95, 'Blazer versátil para trabajo')
            ],
            'Muebles': [
                ('Sofá 3 Plazas', 650, 'Sofá cómodo para sala de estar'),
                ('Mesa Comedor', 450, 'Mesa de comedor para 6 personas'),
                ('Cama Queen', 550, 'Cama matrimonial con cabecero'),
                ('Escritorio Oficina', 280, 'Escritorio ergonómico para trabajo'),
                ('Estantería Moderna', 180, 'Estantería de diseño minimalista')
            ],
            'Fitness': [
                ('Mancuernas Ajustables', 120, 'Set de mancuernas de peso variable'),
                ('Cinta de Correr', 800,
                 'Cinta eléctrica para ejercicio cardiovascular'),
                ('Bicicleta Estática', 350, 'Bicicleta indoor para entrenamiento'),
                ('Banco Multiusos', 180, 'Banco ajustable para ejercicios'),
                ('Kit Yoga', 45, 'Kit completo para práctica de yoga')
            ]
        }

        products = []
        brands = ['Premium', 'Classic', 'Sport', 'Elite',
                  'Pro', 'Advanced', 'Standard', 'Deluxe']

        for i in range(count):
            category = random.choice(categories)

            # Usar plantillas si están disponibles
            if category.name in product_templates:
                template = random.choice(product_templates[category.name])
                base_name, base_price, base_description = template

                # Añadir variación
                brand = random.choice(brands)
                name = f'{brand} {base_name}'
                price = base_price * \
                    random.uniform(0.8, 1.3)  # Variación de precio ±30%
                description = f'{base_description}. Modelo {brand} con características mejoradas.'
            else:
                # Generar producto genérico
                name = f'{random.choice(brands)} {category.name} {i+1:04d}'
                price = random.uniform(10, 2000)
                description = f'Producto de alta calidad en la categoría {category.name}'

            user = users[0] if users[0] else None
            created_at = self._random_date_in_range()
            product = Product(
                name=name,
                description=description,
                unit_price=Decimal(str(round(price, 2))),
                product_code=f'PROD-{i+1:06d}',
                brand=random.choice(brands),
                model=f'Model-{random.randint(1000, 9999)}',
                created_by=user,
                created_at=created_at,
                updated_by=user
            )
            products.append(product)

        # Crear productos primero
        with disable_auto_now_add(Product):
            Product.objects.bulk_create(products, batch_size=100)

        # Luego crear las relaciones de categorías
        created_products = Product.objects.order_by('-id')[:count]
        product_categories = []
        user = users[0] if users[0] else None

        for product in created_products:
            # Asignar 1-3 categorías por producto
            num_categories = random.randint(1, min(3, len(categories)))
            selected_categories = random.sample(categories, num_categories)

            for i, category in enumerate(selected_categories):
                # 📅 Fecha de asignación histórica
                assigned_date = self._random_date_in_range()

                product_category = ProductCategory(
                    product=product,
                    category=category,
                    # La primera categoría es la principal
                    is_primary=(i == 0),
                    assigned_at=assigned_date,
                    assigned_by=user
                )
                product_categories.append(product_category)

        # 📅 Usar contexto para permitir fechas históricas en assigned_at
        with disable_auto_now_add(ProductCategory):
            ProductCategory.objects.bulk_create(
                product_categories, batch_size=100)
        self.stdout.write(
            f'✅ {count} productos creados con {len(product_categories)} relaciones de categoría')

    def _generate_inventories(self):
        """Genera inventarios para los productos."""
        self.stdout.write('📊 Generando inventarios...')

        products = list(Product.objects.all())
        locations = list(StorageLocation.objects.all())

        self.stdout.write(
            f'   📦 Procesando {len(products)} productos en {len(locations)} ubicaciones...')

        inventories = []
        processed_count = 0

        for product in products:
            # Cada producto puede estar en 1-3 ubicaciones
            num_locations = random.randint(1, min(3, len(locations)))
            selected_locations = random.sample(locations, num_locations)

            for location in selected_locations:
                # Generar lotes aleatorios
                batch_code = f'LOTE-{random.randint(1000, 9999)}' if random.choice([
                    True, False]) else '__NULL__'
                expiry_date = timezone.now().date() + timedelta(days=random.randint(30, 365)
                                                                ) if batch_code != '__NULL__' else None
                created_at = self._random_date_in_range()
                inventory = InventoryRecord(
                    product=product,
                    location=location,
                    quantity=random.randint(0, 1000),
                    batch_code=batch_code,
                    expiry_date=expiry_date if expiry_date else timezone.now().date() +
                    timedelta(days=365),
                    created_at=created_at,
                    updated_by=None  # Se puede agregar usuario si está disponible
                )
                inventories.append(inventory)

            processed_count += 1
            # Mostrar progreso cada 100 productos
            if processed_count % 100 == 0:
                self.stdout.write(
                    f'   📊 Procesados {processed_count}/{len(products)} productos...')

        self.stdout.write(
            f'   💾 Guardando {len(inventories)} registros en base de datos...')
        with disable_auto_now_add(InventoryRecord):
            InventoryRecord.objects.bulk_create(inventories, batch_size=100)
        self.stdout.write(
            f'✅ {len(inventories)} registros de inventario creados')

    def _generate_promotions(self):
        """Genera promociones con fechas en el rango temporal."""
        self.stdout.write('🎉 Generando promociones...')

        users = list(self.User.objects.filter(is_superuser=True)[:1])
        user = users[0] if users else None

        promotions = []
        promotion_names = [
            'Descuento Verano',
            'Black Friday',
            'Liquidación',
            'Cliente VIP',
            'Primera Compra',
            'Oferta Especial',
            'Fin de Temporada',
            'Cyber Monday',
            'Descuento Navidad',
            'Promoción Año Nuevo'
        ]

        for name in promotion_names:
            # 📅 Fechas de creación distribuidas en el rango
            created_at = self._random_date_in_range()

            promotion = Promotion(
                name=name,
                active=random.choice([True, False]),
                created_by=user,
                updated_by=user,
                created_at=created_at
            )
            promotions.append(promotion)

        with disable_auto_now_add(Promotion):
            Promotion.objects.bulk_create(promotions)
        self.stdout.write(f'✅ {len(promotions)} promociones creadas')

    # 🎯 Alcance de Promociones
    def _generate_promotion_scopes(self):
        """Genera alcances de promociones."""
        self.stdout.write('🎯 Generando alcances de promociones...')

        promotions = list(Promotion.objects.all())
        categories = list(Category.objects.all())
        # Limitamos para eficiencia
        products = list(Product.objects.all()[:50])
        locations = list(StorageLocation.objects.all()[:10])
        user = self.User.objects.filter(is_superuser=True).first()

        scope_categories = []
        scope_products = []
        scope_locations = []
        promotion_rules = []

        for promotion in promotions:
            # Cada promoción puede tener varios alcances

            # Alcance por categorías (70% de las promociones)
            if random.random() < 0.7:
                selected_categories = random.sample(
                    categories, random.randint(1, 3))
                for category in selected_categories:
                    # 📅 Fecha de alcance posterior o igual a la creación de la promoción
                    scope_created_at = self._random_date_between(
                        promotion.created_at, self.END_DATE
                    )
                    scope_categories.append(
                        PromotionScopeCategory(
                            promotion=promotion,
                            category=category,
                            created_by=user,
                            updated_by=user,
                            created_at=scope_created_at
                        )
                    )

            # Alcance por productos específicos (40% de las promociones)
            if random.random() < 0.4:
                selected_products = random.sample(
                    products, random.randint(1, 5))
                for product in selected_products:
                    # 📅 Fecha de alcance posterior o igual a la creación de la promoción
                    scope_created_at = self._random_date_between(
                        promotion.created_at, self.END_DATE
                    )
                    scope_products.append(
                        PromotionScopeProduct(
                            promotion=promotion,
                            product=product,
                            created_by=user,
                            updated_by=user,
                            created_at=scope_created_at
                        )
                    )

            # Alcance por ubicaciones (30% de las promociones)
            if random.random() < 0.3:
                selected_locations = random.sample(
                    locations, random.randint(1, 2))
                for location in selected_locations:
                    # 📅 Fecha de alcance posterior o igual a la creación de la promoción
                    scope_created_at = self._random_date_between(
                        promotion.created_at, self.END_DATE
                    )
                    scope_locations.append(
                        PromotionScopeLocation(
                            promotion=promotion,
                            location=location,
                            created_by=user,
                            updated_by=user,
                            created_at=scope_created_at
                        )
                    )

            # Reglas de promoción (80% de las promociones)
            if random.random() < 0.8:
                # 📅 Fecha de creación de regla posterior a la promoción
                rule_created_at = self._random_date_between(
                    promotion.created_at, self.END_DATE
                )

                # 📅 Fechas de inicio y fin lógicas para la regla
                # La regla puede empezar entre su creación y algunos días después
                max_start_delay = min(
                    30, (self.END_DATE - rule_created_at).days)
                if max_start_delay > 0:
                    start_delay = random.randint(0, max_start_delay)
                    start_date = rule_created_at + timedelta(days=start_delay)
                else:
                    start_date = rule_created_at

                # La regla dura entre 7 y 90 días
                duration_days = random.randint(7, 90)
                end_date = start_date + timedelta(days=duration_days)

                # Asegurar que no exceda nuestro rango temporal
                if end_date > self.END_DATE:
                    end_date = self.END_DATE

                promotion_rules.append(
                    PromotionRule(
                        promotion=promotion,
                        type=random.choice([
                            PromotionRule.Type.PERCENTAGE,
                            PromotionRule.Type.AMOUNT,
                            PromotionRule.Type.FIRST_PURCHASE
                        ]),
                        value=Decimal(str(random.uniform(5, 50))),
                        priority=random.randint(1, 100),
                        start_at=start_date,
                        end_at=end_date,
                        acumulable=random.choice([True, False]),
                        created_by=user,
                        updated_by=user,
                        created_at=rule_created_at
                    )
                )

        # Crear todos los alcances
        if scope_categories:
            with disable_auto_now_add(PromotionScopeCategory):
                PromotionScopeCategory.objects.bulk_create(scope_categories)
        if scope_products:
            with disable_auto_now_add(PromotionScopeProduct):
                PromotionScopeProduct.objects.bulk_create(scope_products)
        if scope_locations:
            with disable_auto_now_add(PromotionScopeLocation):
                PromotionScopeLocation.objects.bulk_create(scope_locations)
        if promotion_rules:
            with disable_auto_now_add(PromotionRule):
                PromotionRule.objects.bulk_create(promotion_rules)

        total_scopes = len(scope_categories) + len(scope_products) + \
            len(scope_locations) + len(promotion_rules)
        self.stdout.write(f'✅ {total_scopes} alcances de promociones creados')

    def _generate_inventory_movements(self, count):
        """Genera movimientos de inventario distribuidos en el rango temporal completo."""
        self.stdout.write(
            f'📦 Generando {count} movimientos de inventario ({self.START_DATE.date()} → {self.END_DATE.date()})...')
        start_time = timezone.now()

        products = list(Product.objects.all())
        locations = list(StorageLocation.objects.all())
        users = list(self.User.objects.filter(is_superuser=True)[:1])
        user = users[0] if users else None

        self.stdout.write(
            f'   📊 Recursos disponibles: {len(products)} productos, {len(locations)} ubicaciones')

        movements = []
        batch_size = 5000

        movement_scenarios = [
            {"reason": InventoryMovement.Reason.PURCHASE_ENTRY, "reference_type": InventoryMovement.RefType.PURCHASE, "probability": 0.4,
             "description_templates": ['Entrada por compra', 'Recepción de mercadería', 'Compra de stock', 'Reposición de inventario']},
            {"reason": InventoryMovement.Reason.EXIT_SALE, "reference_type": InventoryMovement.RefType.SALE, "probability": 0.3,
             "description_templates": ['Salida por venta', 'Despacho de pedido', 'Venta mostrador', 'Entrega al cliente']},
            {"reason": InventoryMovement.Reason.TRANSFER, "reference_type": InventoryMovement.RefType.MANUAL, "probability": 0.2,
             "description_templates": ['Transferencia entre almacenes', 'Reorganización de stock', 'Movimiento interno']},
            {"reason": InventoryMovement.Reason.ADJUSTMENT, "reference_type": InventoryMovement.RefType.MANUAL, "probability": 0.07,
             "description_templates": ['Ajuste de inventario', 'Corrección de cantidad', 'Regularización de stock']},
            {"reason": InventoryMovement.Reason.RETURN_ENTRY, "reference_type": InventoryMovement.RefType.SALE, "probability": 0.03,
             "description_templates": ['Devolución de cliente', 'Producto defectuoso retornado', 'Cancelación de venta']}
        ]

        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            batch_movements = []

            self.stdout.write(
                f'   📦 Generando lote {batch_start//batch_size + 1}: movimientos {batch_start+1} a {batch_end}...')

            for i in range(batch_start, batch_end):
                product = random.choice(products)

                rand = random.random()
                cumulative_prob = 0
                scenario = movement_scenarios[0]
                for sc in movement_scenarios:
                    cumulative_prob += sc['probability']
                    if rand <= cumulative_prob:
                        scenario = sc
                        break

                # 📅 Fecha aleatoria en rango temporal unificado
                movement_date = self._random_date_in_range()

                from_location, to_location = None, None
                if scenario['reason'] == InventoryMovement.Reason.PURCHASE_ENTRY:
                    to_location = random.choice(locations)
                elif scenario['reason'] == InventoryMovement.Reason.EXIT_SALE:
                    from_location = random.choice(locations)
                elif scenario['reason'] == InventoryMovement.Reason.TRANSFER:
                    from_location, to_location = random.sample(locations, 2)
                else:
                    if random.choice([True, False]):
                        from_location = random.choice(locations)
                    else:
                        to_location = random.choice(locations)

                if scenario['reason'] == InventoryMovement.Reason.PURCHASE_ENTRY:
                    quantity = random.randint(50, 500)
                elif scenario['reason'] == InventoryMovement.Reason.EXIT_SALE:
                    quantity = random.randint(1, 20)
                elif scenario['reason'] == InventoryMovement.Reason.TRANSFER:
                    quantity = random.randint(10, 100)
                else:
                    quantity = random.randint(1, 50)

                batch_code = f'LOTE-{random.randint(1000,9999)}' if random.choice([
                    True, False]) else None

                # 📅 Fechas de expiración coherentes con el movimiento
                if batch_code:
                    min_expiry = movement_date.date() + timedelta(days=30)
                    max_expiry = min(self.END_DATE.date(),
                                     movement_date.date() + timedelta(days=730))

                    if min_expiry <= max_expiry:
                        days_diff = (max_expiry - min_expiry).days
                        if days_diff > 0:
                            random_days = random.randint(0, days_diff)
                            expiry_date = min_expiry + \
                                timedelta(days=random_days)
                        else:
                            expiry_date = min_expiry
                    else:
                        expiry_date = min_expiry
                else:
                    expiry_date = None

                reference_id = random.randint(
                    1000, 9999) if scenario['reference_type'] != InventoryMovement.RefType.MANUAL else None

                movement = InventoryMovement(
                    product=product,
                    batch_code=batch_code,
                    expiry_date=expiry_date,
                    from_location=from_location,
                    to_location=to_location,
                    quantity=quantity,
                    reason=scenario['reason'],
                    description=random.choice(
                        scenario['description_templates']),
                    reference_type=scenario['reference_type'],
                    reference_id=reference_id,
                    # 📅 Fecha manual (auto_now_add deshabilitado)
                    created_at=movement_date,
                    occurred_at=movement_date,
                    created_by=user,
                    updated_by=user
                )
                batch_movements.append(movement)

            # Guardar lote
            batch_creation_start = time.time()
            with disable_auto_now_add(InventoryMovement):
                InventoryMovement.objects.bulk_create(
                    batch_movements, batch_size=100)
            self.stdout.write(
                f'   ✅ Lote {batch_start//batch_size + 1} guardado en {time.time() - batch_creation_start:.2f}s')
            movements.extend(batch_movements)

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        self.stdout.write(
            f'✅ {len(movements)} movimientos generados en rango temporal completo en {duration:.2f}s')

    def _generate_purchases(self, count):
        """Genera compras distribuidas en el rango temporal completo."""
        self.stdout.write(
            f'🛒 Generando {count} compras ({self.START_DATE.date()} → {self.END_DATE.date()})...')
        start_time = timezone.now()

        users = list(self.User.objects.filter(is_superuser=False))
        products = list(Product.objects.all())

        self.stdout.write(
            f'   📊 Usuarios disponibles: {len(users)}, Productos disponibles: {len(products)}')

        purchases = []
        purchase_items = []
        batch_size = 1000

        self.stdout.write(
            f'   🔄 Generando {count} compras en lotes de {batch_size}...')

        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            batch_purchases = []

            self.stdout.write(
                f'   📦 Procesando lote {batch_start//batch_size + 1}: compras {batch_start+1} a {batch_end}...')

            for i in range(batch_start, batch_end):
                user = random.choice(users)
                # 📅 Fecha de compra aleatoria en rango temporal unificado
                purchase_date = self._random_date_in_range()
                # 📅 created_at puede ser igual o ligeramente después de purchase_date
                created_at = self._random_date_between(
                    purchase_date,
                    purchase_date + timedelta(hours=random.randint(0, 24))
                )

                purchase = Purchase(
                    user=user,
                    total_amount=Decimal('0.00'),
                    status=random.choice(['OPEN', 'PAID', 'CANCELLED']),
                    purchase_date=purchase_date,
                    created_at=created_at,
                    total_installments_count=random.choice([1, 3, 6, 12]),
                    discount_applied=Decimal(str(random.uniform(0, 50))) if random.choice(
                        [True, False]) else Decimal('0.00')
                )
                batch_purchases.append(purchase)

            # Crear lote de compras
            batch_creation_start = time.time()
            # 📅 Usar contexto para permitir fechas históricas en created_at
            with disable_auto_now_add(Purchase):
                Purchase.objects.bulk_create(batch_purchases, batch_size=100)
            self.stdout.write(
                f'   ✅ Lote {batch_start//batch_size + 1} creado en {time.time() - batch_creation_start:.2f}s')
            purchases.extend(batch_purchases)

        self.stdout.write(
            f'   💾 {len(purchases)} compras base creadas, generando items...')

        # Ahora crear items para cada compra en lotes
        created_purchases = Purchase.objects.order_by('-id')[:count]
        items_batch_size = 500

        for batch_start in range(0, len(created_purchases), items_batch_size):
            batch_end = min(batch_start + items_batch_size,
                            len(created_purchases))
            batch_items = []

            self.stdout.write(
                f'   🛍️  Generando items para compras {batch_start+1} a {batch_end}...')

            for purchase in created_purchases[batch_start:batch_end]:
                # Cada compra tiene 1-5 items
                num_items = random.randint(1, 5)
                selected_products = random.sample(
                    products, min(num_items, len(products)))

                total_amount = Decimal('0.00')

                for product in selected_products:
                    quantity = random.randint(1, 5)
                    unit_price = product.unit_price

                    # Aplicar descuento aleatorio (simulando promoción)
                    if random.choice([True, False]):
                        discount_percentage = Decimal(
                            str(random.uniform(5, 25)))
                        discount = (unit_price * discount_percentage / 100)
                        unit_price = unit_price - discount

                    subtotal = unit_price * quantity
                    total_amount += subtotal

                    # 📅 Fecha de creación coherente con la compra o después
                    item_created_at = self._random_date_between(
                        purchase.created_at,
                        self.END_DATE
                    )

                    item = PurchaseDetail(
                        purchase=purchase,
                        product=product,
                        quantity=quantity,
                        unit_price_at_purchase=unit_price,
                        subtotal=subtotal,
                        created_at=item_created_at
                    )
                    batch_items.append(item)

                # Actualizar total de la compra
                purchase.total_amount = total_amount
                purchase.save()

            # Crear lote de items
            items_creation_start = time.time()
            # 📅 Usar contexto para permitir fechas históricas en created_at
            with disable_auto_now_add(PurchaseDetail):
                PurchaseDetail.objects.bulk_create(batch_items, batch_size=100)
            self.stdout.write(
                f'   ✅ {len(batch_items)} items creados en {time.time() - items_creation_start:.2f}s')
            purchase_items.extend(batch_items)

        total_duration = (timezone.now() - start_time).total_seconds()
        self.stdout.write(
            f'✅ {count} compras y {len(purchase_items)} items creados en rango temporal completo en {total_duration:.2f}s')

    def _generate_payments(self):
        """Genera cuotas y pagos con fechas en el rango temporal."""
        self.stdout.write('💳 Generando cuotas y pagos...')
        start_time = time.time()

        purchases = list(Purchase.objects.exclude(status='CANCELLED'))
        payment_methods = ['CASH', 'CARD', 'TRANSFER']

        self.stdout.write(
            f'   📊 Procesando {len(purchases)} compras para generar cuotas y pagos...')

        installments = []
        payments = []
        processed_purchases = 0

        for purchase in purchases:
            processed_purchases += 1

            # Log cada 1000 compras procesadas
            if processed_purchases % 1000 == 0:
                self.stdout.write(
                    f'   🔄 Procesadas {processed_purchases}/{len(purchases)} compras...')

            # Algunas compras en cuotas, otras pago único
            is_installment_purchase = random.choice(
                [True, False]) and purchase.total_amount > 100

            if is_installment_purchase:
                # Compra con múltiples cuotas
                num_installments = random.choice([3, 6, 12])
                base_amount = purchase.total_amount / num_installments

                for i in range(num_installments):
                    # 📅 Fechas de vencimiento basadas en fecha de compra
                    due_date = purchase.purchase_date.date() + timedelta(days=30 * (i + 1))
                    # Asegurar que due_date no exceda nuestro rango
                    if due_date > self.END_DATE.date():
                        due_date = self.END_DATE.date()

                    # Aplicar recargos/descuentos aleatorios
                    surcharge = Decimal(str(random.uniform(0, 5))) if random.choice(
                        [True, False]) else Decimal('0')
                    discount = Decimal(str(random.uniform(0, 3))) if random.choice(
                        [True, False]) else Decimal('0')

                    final_amount = base_amount * \
                        (1 + surcharge/100 - discount/100)

                    # 📅 Fecha de creación de cuota: entre fecha de compra y vencimiento
                    installment_created_at = self._random_date_between(
                        purchase.purchase_date,
                        datetime.combine(
                            due_date, datetime.min.time(), tzinfo=pytz.UTC)
                    )

                    installment = Installment(
                        purchase=purchase,
                        num_installment=i + 1,
                        base_amount=base_amount,
                        surcharge_pct=surcharge,
                        discount_pct=discount,
                        amount_due=final_amount,
                        due_date=due_date,
                        created_at=installment_created_at,
                        state=random.choice(
                            ['PENDING', 'PAID']) if i == 0 else 'PENDING'
                    )
                    installments.append(installment)
            else:
                # Compra con pago único
                due_date = purchase.purchase_date.date() + timedelta(days=30)
                if due_date > self.END_DATE.date():
                    due_date = self.END_DATE.date()

                # 📅 Fecha de creación de cuota: entre fecha de compra y vencimiento
                installment_created_at = self._random_date_between(
                    purchase.purchase_date,
                    datetime.combine(
                        due_date, datetime.min.time(), tzinfo=pytz.UTC)
                )
                state = random.choice(['PENDING', 'PAID', 'OVERDUE'])

                installment = Installment(
                    purchase=purchase,
                    num_installment=1,
                    base_amount=purchase.total_amount,
                    surcharge_pct=Decimal(
                        '8.0') if state == 'OVERDUE' else Decimal('0'),
                    discount_pct=random.choice(
                        [Decimal('0'), Decimal('2.0'), Decimal('5.0')]),
                    amount_due=purchase.total_amount,
                    due_date=due_date,
                    created_at=installment_created_at,
                    state=state
                )
                installments.append(installment)

        self.stdout.write(f'   💾 Guardando {len(installments)} cuotas...')
        # Crear cuotas primero
        installments_creation_start = time.time()
        # 📅 Usar contexto para permitir fechas históricas en created_at
        with disable_auto_now_add(Installment):
            Installment.objects.bulk_create(installments, batch_size=100)
        self.stdout.write(
            f'   ✅ Cuotas creadas en {time.time() - installments_creation_start:.2f}s')

        # Crear pagos para algunas cuotas pagadas
        self.stdout.write(
            f'   🔍 Buscando cuotas pagadas para generar pagos...')
        created_installments = list(Installment.objects.filter(state='PAID'))
        self.stdout.write(
            f'   💰 Generando pagos para {len(created_installments)} cuotas pagadas...')

        for i, installment in enumerate(created_installments):
            if i % 500 == 0 and i > 0:
                self.stdout.write(
                    f'   🔄 Procesados {i}/{len(created_installments)} pagos...')

            # Algunos pagos pueden ser parciales
            payment_amount = installment.amount_due
            if random.choice([True, False]):
                payment_amount = installment.amount_due * \
                    Decimal(str(random.uniform(0.5, 1.0)))

            # 📅 Fecha de pago: entre vencimiento y final del rango (para cuotas pagadas)
            # Si está PAID, el pago debe ser después del vencimiento
            due_datetime = datetime.combine(
                installment.due_date, datetime.min.time(), tzinfo=pytz.UTC)
            payment_created_at = self._random_date_between(
                due_datetime, self.END_DATE
            )

            payment = Payment(
                installment=installment,
                amount=payment_amount,
                payment_method=random.choice(payment_methods),
                external_ref=self._generate_unique_external_ref(),
                payment_date=payment_created_at,
                created_at=payment_created_at
            )
            payments.append(payment)

            # Actualizar estado de cuota si pago completo
            if payment_amount >= installment.amount_due:
                installment.paid_amount = payment_amount
                installment.paid_at = payment_created_at
                installment.save()

        self.stdout.write(f'   💾 Guardando {len(payments)} pagos...')
        payments_creation_start = time.time()
        # 📅 Usar contexto para permitir fechas históricas en created_at
        with disable_auto_now_add(Payment):
            Payment.objects.bulk_create(payments, batch_size=100)

        total_duration = time.time() - start_time
        self.stdout.write(
            f'✅ {len(installments)} cuotas y {len(payments)} pagos creados en {total_duration:.2f}s')

    # 🔍 Auditoría de Cuotas
    def _generate_installment_audit_logs(self):
        """Genera logs de auditoría para cambios en cuotas."""
        self.stdout.write('🔍 Generando logs de auditoría de cuotas...')
        start_time = time.time()

        installments = list(Installment.objects.all())
        users = list(self.User.objects.filter(is_superuser=True))

        self.stdout.write(
            f'   📊 Procesando {len(installments)} cuotas disponibles...')

        audit_logs = []

        # Solo crear auditorías para ~30% de las cuotas (para simular cambios reales)
        # Limitar a 1000 para eficiencia
        max_audits = min(len(installments) // 3, 1000)
        installments_to_audit = random.sample(installments, max_audits)

        self.stdout.write(
            f'   🎯 Generando auditorías para {len(installments_to_audit)} cuotas seleccionadas...')

        for i, installment in enumerate(installments_to_audit):
            if i % 100 == 0 and i > 0:
                self.stdout.write(
                    f'   🔄 Procesadas {i}/{len(installments_to_audit)} cuotas...')

            # Cada cuota puede tener 1-3 cambios de auditoría
            num_changes = random.randint(1, 3)

            for j in range(num_changes):
                # 📅 Fecha de auditoría posterior a la creación de la cuota
                # La auditoría debe ocurrir después de que se creó la cuota
                min_audit_date = installment.created_at + \
                    timedelta(hours=1)  # Al menos 1 hora después
                # Máximo 6 meses después
                max_audit_date = min(
                    self.END_DATE, min_audit_date + timedelta(days=180))

                if min_audit_date >= max_audit_date:
                    max_audit_date = self.END_DATE

                audit_date = self._random_date_between(
                    min_audit_date, max_audit_date)

                reasons = [
                    'Corrección de monto por error administrativo',
                    'Aplicación de descuento por pronto pago',
                    'Recargo por mora aplicado',
                    'Ajuste por cambio de condiciones',
                    'Corrección de fecha de vencimiento'
                ]

                changes = {
                    'field_changed': random.choice(['amount_due', 'due_date', 'state']),
                    'old_value': f'{random.uniform(100, 1000):.2f}',
                    'new_value': f'{random.uniform(100, 1000):.2f}',
                    'timestamp': audit_date.isoformat()
                }

                audit_log = InstallmentAuditLog(
                    installment=installment,
                    updated_at=audit_date,
                    updated_by=random.choice(users) if users else None,
                    reason=random.choice(reasons),
                    delta_json=changes
                )
                audit_logs.append((audit_log, audit_date))

        self.stdout.write(
            f'   💾 Guardando {len(audit_logs)} logs de auditoría...')
        # Crear logs primero
        logs_to_create = [log for log, _ in audit_logs]
        creation_start = time.time()

        # 📅 Usar contexto para permitir fechas históricas en created_at
        with disable_auto_now_add(InstallmentAuditLog):
            InstallmentAuditLog.objects.bulk_create(
                logs_to_create, batch_size=100)

        self.stdout.write(
            f'   ✅ Logs creados en {time.time() - creation_start:.2f}s')

        total_duration = time.time() - start_time
        self.stdout.write(
            f'✅ {len(logs_to_create)} logs de auditoría creados en {total_duration:.2f}s')

    # 📸 Snapshots de Inventario
    def _generate_stock_snapshots(self):
        """Genera snapshots de inventario para materialización de reportes."""
        self.stdout.write('📸 Generando snapshots de inventario...')
        start_time = time.time()

        # Limitamos para eficiencia
        products = list(Product.objects.all()[:100])
        locations = list(StorageLocation.objects.all())
        user = self.User.objects.filter(is_superuser=True).first()

        self.stdout.write(
            f'   📊 Productos disponibles: {len(products)}, Ubicaciones: {len(locations)}')

        snapshots = []

        # Generar snapshots para ~50% de los productos en ~50% de las ubicaciones
        selected_products = random.sample(products, len(products) // 2)
        selected_locations = random.sample(locations, len(locations) // 2)

        total_combinations = len(selected_products) * len(selected_locations)
        self.stdout.write(
            f'   🎯 Generando snapshots para {len(selected_products)} productos × {len(selected_locations)} ubicaciones = {total_combinations} combinaciones...')

        processed = 0
        for product in selected_products:
            for location in selected_locations:
                processed += 1
                if processed % 500 == 0:
                    self.stdout.write(
                        f'   🔄 Procesadas {processed}/{total_combinations} combinaciones...')

                # 📅 Fecha de último movimiento coherente con inventarios
                # Puede ser cualquier fecha en el rango, pero manteniendo lógica
                last_movement_date = self._random_date_in_range()
                # 📅 created_at del snapshot puede ser igual o después del último movimiento
                snapshot_created_at = self._random_date_between(
                    last_movement_date,
                    self.END_DATE
                )

                batch_code = f'LOTE-{random.randint(1000, 9999)}' if random.choice([
                    True, False]) else None

                # 📅 Fecha de expiración debe ser posterior al último movimiento
                if batch_code:
                    min_expiry = last_movement_date.date() + timedelta(days=30)
                    max_expiry = min(self.END_DATE.date(
                    ), last_movement_date.date() + timedelta(days=730))

                    if min_expiry <= max_expiry:
                        # Generar fecha de expiración entre el rango válido
                        days_diff = (max_expiry - min_expiry).days
                        if days_diff > 0:
                            random_days = random.randint(0, days_diff)
                            expiry_date = min_expiry + \
                                timedelta(days=random_days)
                        else:
                            expiry_date = min_expiry
                    else:
                        expiry_date = min_expiry
                else:
                    expiry_date = None

                snapshot = StockSnapshot(
                    product=product,
                    location=location,
                    batch_code=batch_code,
                    expiry_date=expiry_date,
                    quantity=random.randint(0, 500),
                    last_movement_at=last_movement_date,
                    created_at=snapshot_created_at,
                    updated_by=user
                )
                snapshots.append(snapshot)

        self.stdout.write(f'   💾 Guardando {len(snapshots)} snapshots...')
        creation_start = time.time()

        # 📅 Usar contexto para permitir fechas históricas en created_at
        with disable_auto_now_add(StockSnapshot):
            StockSnapshot.objects.bulk_create(snapshots, batch_size=100)

        total_duration = time.time() - start_time
        self.stdout.write(
            f'✅ {len(snapshots)} snapshots de inventario creados en {total_duration:.2f}s')

    def _show_summary(self):
        """Muestra un resumen de los datos generados."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE DATOS GENERADOS'))
        self.stdout.write(
            f'🗓️  Rango temporal: {self.START_DATE.date()} → {self.END_DATE.date()}')
        self.stdout.write('='*60)

        stats = [
            ('👥 Usuarios', self.User.objects.filter(is_superuser=False).count()),
            ('📂 Categorías', Category.objects.count()),
            ('📦 Productos', Product.objects.count()),
            ('🔗 Relaciones Producto-Categoría', ProductCategory.objects.count()),
            ('🏪 Ubicaciones de Almacenamiento', StorageLocation.objects.count()),
            ('📊 Inventarios', InventoryRecord.objects.count()),
            ('📦 Movimientos de Inventario', InventoryMovement.objects.count()),
            ('📧 Templates de Notificación', NotificationTemplate.objects.count()),
            ('🎉 Promociones', Promotion.objects.count()),
            ('🎯 Alcances de Categorías', PromotionScopeCategory.objects.count()),
            ('🎯 Alcances de Productos', PromotionScopeProduct.objects.count()),
            ('🎯 Alcances de Ubicaciones', PromotionScopeLocation.objects.count()),
            ('� Reglas de Promoción', PromotionRule.objects.count()),
            ('�🛒 Compras', Purchase.objects.count()),
            ('📝 Items de Compra', PurchaseDetail.objects.count()),
            ('💳 Pagos', Payment.objects.count()),
            ('📅 Cuotas', Installment.objects.count()),
            ('🔍 Auditoría de Cuotas', InstallmentAuditLog.objects.count()),
            ('📸 Snapshots de Inventario', StockSnapshot.objects.count()),
        ]

        total_records = 0
        for label, count in stats:
            self.stdout.write(f'{label}: {count:,}')
            total_records += count

        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS(
            f'🎯 TOTAL REGISTROS: {total_records:,}'))
        self.stdout.write('='*60)

        # Verificar objetivos
        products_count = Product.objects.count()
        if products_count >= 400:
            self.stdout.write(self.style.SUCCESS(
                f'✅ Objetivo productos cumplido: {products_count} >= 400'))
        else:
            self.stdout.write(self.style.ERROR(
                f'❌ Objetivo productos NO cumplido: {products_count} < 400'))

        if total_records >= 1000:
            self.stdout.write(self.style.SUCCESS(
                f'✅ Objetivo total registros cumplido: {total_records:,} >= 1,000'))
        else:
            self.stdout.write(self.style.WARNING(
                f'⚠️  Total registros: {total_records:,} < 1,000'))

        # Verificación de rango temporal
        sample_purchases = Purchase.objects.order_by('?')[:5]
        if sample_purchases:
            self.stdout.write('\n📅 Verificación de rango temporal (muestra):')
            for i, purchase in enumerate(sample_purchases, 1):
                self.stdout.write(
                    f'   Compra {i}: {purchase.purchase_date.date()}')

        self.stdout.write(
            '\n🎯 Todos los modelos excepto notificaciones han sido poblados')
        self.stdout.write(
            f'📈 Datos listos para generar gráficas desde {self.START_DATE.date()}')
