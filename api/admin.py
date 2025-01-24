from django.contrib import admin
from .models import Products, Compras, Cuotas, Pagos, DetallesCompras


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para el modelo Products.
    """
    list_display = ('cod_products', 'nombre', 'marca',
                    'modelo', 'precio_unitario', 'stock')
    search_fields = ('cod_products', 'nombre', 'marca', 'modelo')
    list_filter = ('marca', 'modelo')
    ordering = ('nombre',)


@admin.register(Compras)
class ComprasAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para el modelo Compras.
    """
    list_display = ('id', 'usuario', 'fecha_compra',
                    'fecha_vencimiento', 'monto_total', 'cuotas_totales', 'descuento_aplicado', 'cuota_actual')
    search_fields = ('usuario__username', 'id')
    list_filter = ('fecha_compra', 'fecha_vencimiento')
    ordering = ('-fecha_compra',)


@admin.register(Cuotas)
class CuotasAdmin(admin.ModelAdmin):
    """


    Configuración del panel de administración para el modelo Cuotas.
    """
    list_display = ('id', 'compras', 'nro_cuota', 'monto',
                    'fecha_vencimiento', 'estado')
    search_fields = ('compras__id', 'estado')
    list_filter = ('estado', 'fecha_vencimiento')
    ordering = ('compras', 'nro_cuota')


@admin.register(Pagos)
class PagosAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para el modelo Pagos.
    """
    list_display = ('id', 'cuotas', 'fecha_pago', 'monto',
                    'medio_pago')
    search_fields = ('cuotas__id', 'medio_pago', 'fecha_pago')
    list_filter = ('medio_pago', 'fecha_pago')
    ordering = ('-fecha_pago',)


@admin.register(DetallesCompras)
class DetallesComprasAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para el modelo DetallesCompras.
    """
    list_display = ('id', 'compras', 'products', 'cantidad_productos')
    search_fields = ('compras__id', 'products__id')
    list_filter = ('id', )
