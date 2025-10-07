from django.http import HttpResponse, JsonResponse
from .tasks import (
    generate_product_rotation_report,
    generate_movements_input_output_report,
    generate_sales_summary_report,
    generate_top_products_report,
    generate_payment_methods_report,
    generate_overdue_installments_report
)
from .models import Report
from .serializers import (
    OverdueInstallmentsReportSerializer, ReportCreateSerializer,
    ProductRotationReportSerializer,
    MovementsReportSerializer, SalesSummaryReportSerializer,
    TopProductsReportSerializer, PaymentMethodsReportSerializer,
    ReportStatusSerializer, ReportListSerializer
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from datetime import datetime, date
from rest_framework import status
from api.cache import cache_manager, CacheKeys, CacheTimeouts
from api.permissions import PermissionDenied
from api.response_helpers import server_error_response, validation_error_response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
import json

logger = logging.getLogger(__name__)


@swagger_auto_schema(
    method='post',
    operation_description="""
    **Crear Reporte de Rotación de Productos (Asíncrono)**
    
    Inicia la generación asíncrona de un reporte de rotación de productos por ubicación.
    El reporte se procesa en segundo plano usando Celery.
    
    **Flujo de trabajo:**
    1. Crear solicitud de reporte con este endpoint
    2. Recibir `task_id` y `report_id` en la respuesta
    3. Consultar estado con `/reports/status/<task_id>/`
    4. Descargar archivo cuando `status` sea `COMPLETED` usando `/reports/<report_id>/download/`
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['location_id', 'from_date'],
        properties={
            'location_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID de la ubicación'),
            'from_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description='Fecha inicial'),
            'to_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description='Fecha final'),
            'excel': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True, description='Generar Excel'),
            'graphic': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True, description='Incluir gráfico'),
            'download_graphic': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False, description='Descargar gráfico'),
            'language_graphic': openapi.Schema(type=openapi.TYPE_STRING, enum=['es', 'en'], default='es', description='Idioma'),
        }
    ),
    responses={
        202: openapi.Response(
            description="Reporte en cola para procesamiento",
            examples={
                "application/json": {
                    "success": True,
                    "message": "Reporte en cola para procesamiento",
                    "data": {
                        "report_id": 1,
                        "task_id": "abc123-def456",
                        "status": "PENDING"
                    }
                }
            }
        ),
        400: openapi.Response(description="Error de validación"),
        401: openapi.Response(description="No autorizado"),
    },
    tags=['Analytics - Reportes Asincrónicos']
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_product_rotation_report(request):
    """
    Crea un reporte asíncrono de rotación de productos por ubicación.

    Este endpoint inicia la generación en segundo plano de un reporte detallado sobre
    la rotación de productos en una ubicación específica durante un período de tiempo.
    El reporte analiza movimientos de entrada, salida, transferencias y retornos,
    procesándose mediante Celery para operaciones de larga duración.

    Args:
        request (Request): Objeto de solicitud DRF con los siguientes datos esperados:
            - location_id (int): ID de la ubicación de almacén **[Requerido]**
            - from_date (str): Fecha inicial ISO (YYYY-MM-DD) **[Requerido]**
            - to_date (str): Fecha final ISO (default: fecha actual) **[Opcional]**
            - excel (bool): Generar archivo Excel (default: False) **[Opcional]**
            - graphic (bool): Generar gráfico (default: True) **[Opcional]**
            - download_graphic (bool): Incluir PNG en descarga (default: False) **[Opcional]**
            - language_graphic (str): Idioma 'es' o 'en' (default: 'es') **[Opcional]**

    Returns:
        Response: Respuesta DRF con estructura estándar:
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (dict): Datos del reporte creado
                * task_id (str): ID de la tarea Celery para consultar estado
                * report_id (int): ID del reporte en la base de datos
                * status (str): Estado inicial del reporte (PENDING)

            Status HTTP 201: Reporte creado y en cola correctamente
            Status HTTP 400: Errores de validación en los parámetros
            Status HTTP 403: Usuario sin permisos de administrador
            Status HTTP 500: Error interno durante la creación

    Raises:
        Exception: Captura y loguea cualquier error no manejado, retornando respuesta 500.

    Examples:
        >>> # Solicitud básica con ubicación y fechas
        >>> POST /api/v2/admin/analytics/reports/product-rotation/create/
        >>> {
        >>>     "location_id": 1,
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31"
        >>> }

        >>> # Solicitud completa con Excel, gráfico embebido y ZIP
        >>> POST /api/v2/admin/analytics/reports/product-rotation/create/
        >>> {
        >>>     "location_id": 1,
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31",
        >>>     "excel": true,
        >>>     "graphic": true,
        >>>     "download_graphic": true,
        >>>     "language_graphic": "es"
        >>> }

    Notes:
        - El reporte se procesa de forma asíncrona usando Celery workers
        - Consultar estado del reporte: GET /reports/status/<task_id>/
        - Descargar archivo completado: GET /reports/<report_id>/download/
        - Requiere permisos de administrador (IsAdminUser permission class)
        - Los parámetros se serializan a JSON y se almacenan en el modelo Report
        - Las fechas se convierten a formato ISO string para compatibilidad JSON
        - Soporta múltiples formatos de salida: Excel, PNG, o ZIP con ambos

    References:
        - Django REST Framework: https://www.django-rest-framework.org/api-guide/requests/
        - Celery Tasks: https://docs.celeryq.dev/en/stable/userguide/tasks.html
        - drf-yasg: https://drf-yasg.readthedocs.io/en/stable/
    """
    serializer = ProductRotationReportSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': 'Validation errors',
            'data': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        validated_data = serializer.validated_data

        # Convertir dates a strings ISO para JSON serialization
        parameters = {
            'location_id': validated_data['location_id'],
            'from_date': validated_data['from_date'].isoformat(),
            'to_date': validated_data['to_date'].isoformat(),
            'excel': validated_data.get('excel', False),
            'graphic': validated_data.get('graphic', True),
            'download_graphic': validated_data.get('download_graphic', False),
            'language_graphic': validated_data.get('language_graphic', 'es')
        }

        report = Report.objects.create(
            user=request.user,
            report_type=Report.ReportType.PRODUCT_ROTATION,
            parameters=parameters,
            status=Report.Status.PENDING
        )

        task = generate_product_rotation_report.delay(
            report_id=report.id,
            parameters=parameters
        )

        report.task_id = task.id
        report.save(update_fields=['task_id'])

        return Response({
            'success': True,
            'message': 'Report queued for processing',
            'data': {
                'task_id': task.id,
                'report_id': report.id,
                'status': report.status
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error creating product rotation report: {str(e)}")
        return Response({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_description="""
    **Crear Reporte de Movimientos Entrada/Salida (Asíncrono)**
    
    Inicia la generación asíncrona de un reporte de movimientos de inventario.
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['from_date'],
        properties={
            'from_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            'to_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            'excel': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
            'graphic': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
            'download_graphic': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
            'type_graphic': openapi.Schema(type=openapi.TYPE_STRING, enum=['pie', 'bar'], default='pie'),
            'language_graphic': openapi.Schema(type=openapi.TYPE_STRING, enum=['es', 'en'], default='es'),
        }
    ),
    responses={
        202: openapi.Response(description="Reporte en cola"),
        400: openapi.Response(description="Error de validación"),
    },
    tags=['Analytics - Reportes Asincrónicos']
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_movements_report(request):
    """
    Crea un reporte asíncrono de movimientos de inventario entrada/salida.

    Este endpoint inicia la generación en segundo plano de un reporte sobre movimientos
    de inventario, analizando entradas por compras y salidas por ventas. El reporte puede
    incluir análisis estadísticos, gráficos comparativos (pie o bar charts), y datos
    tabulares exportables a Excel. Se procesa de forma asíncrona mediante Celery.

    Args:
        request (Request): Objeto de solicitud DRF con los siguientes datos esperados:
            - from_date (str): Fecha inicial en formato ISO (YYYY-MM-DD) **[Requerido]**
            - to_date (str): Fecha final en formato ISO (default: fecha actual) **[Opcional]**
            - excel (bool): Generar archivo Excel (default: False) **[Opcional]**
            - graphic (bool): Generar gráfico (default: True) **[Opcional]**
            - download_graphic (bool): Incluir PNG en ZIP (default: False) **[Opcional]**
            - type_graphic (str): Tipo 'pie' o 'bar' (default: 'pie') **[Opcional]**
            - language_graphic (str): Idioma 'es' o 'en' (default: 'es') **[Opcional]**

    Returns:
        Response: Respuesta DRF con estructura estándar:
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (dict): Datos del reporte creado
                * task_id (str): ID de la tarea Celery para consultar estado
                * report_id (int): ID del reporte en la base de datos
                * status (str): Estado inicial del reporte (PENDING)

            Status HTTP 201: Reporte creado y en cola correctamente
            Status HTTP 400: Errores de validación en los parámetros
            Status HTTP 403: Usuario sin permisos de administrador
            Status HTTP 500: Error interno durante la creación

    Raises:
        Exception: Captura y loguea cualquier error no manejado, retornando respuesta 500.

    Examples:
        >>> # Solicitud básica con solo fechas
        >>> POST /api/v2/admin/analytics/reports/movements/create/
        >>> {
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31"
        >>> }

        >>> # Solicitud completa con Excel, gráfico de barras y ZIP
        >>> POST /api/v2/admin/analytics/reports/movements/create/
        >>> {
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31",
        >>>     "excel": true,
        >>>     "graphic": true,
        >>>     "download_graphic": true,
        >>>     "type_graphic": "bar",
        >>>     "language_graphic": "es"
        >>> }

    Notes:
        - El reporte se procesa de forma asíncrona usando Celery workers
        - Consultar estado del reporte: GET /reports/status/<task_id>/
        - Descargar archivo completado: GET /reports/<report_id>/download/
        - Requiere permisos de administrador (IsAdminUser permission class)
        - Tipos de gráfico: 'pie' (circular) o 'bar' (barras)
        - Formatos de salida: Excel, PNG, o ZIP con ambos
        - Analiza solo movimientos tipo PURCHASE_ENTRY y EXIT_SALE

    References:
        - Django REST Framework: https://www.django-rest-framework.org/api-guide/requests/
        - Celery Tasks: https://docs.celeryq.dev/en/stable/userguide/tasks.html
        - drf-yasg: https://drf-yasg.readthedocs.io/en/stable/
    """
    serializer = MovementsReportSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': 'Validation errors',
            'data': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        validated_data = serializer.validated_data

        # Convertir dates a strings ISO para JSON serialization
        parameters = {
            'from_date': validated_data['from_date'].isoformat(),
            'to_date': validated_data['to_date'].isoformat(),
            'excel': validated_data.get('excel', False),
            'download_graphic': validated_data.get('download_graphic', False),
            'type_graphic': validated_data.get('type_graphic', 'bar'),
            'language_graphic': validated_data.get('language_graphic', 'es')
        }

        report = Report.objects.create(
            user=request.user,
            report_type=Report.ReportType.MOVEMENTS_INPUT_OUTPUT,
            parameters=parameters,
            status=Report.Status.PENDING
        )

        task = generate_movements_input_output_report.delay(
            report_id=report.id,
            parameters=parameters
        )

        report.task_id = task.id
        report.save(update_fields=['task_id'])

        return Response({
            'success': True,
            'message': 'Report queued for processing',
            'data': {
                'task_id': task.id,
                'report_id': report.id,
                'status': report.status
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error creating movements report: {str(e)}")
        return Response({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_description="""
    **Crear Reporte de Resumen de Ventas (Asíncrono)**
    
    Inicia la generación asíncrona de un reporte de resumen de ventas.
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['from_date'],
        properties={
            'from_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            'to_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            'month_compare': openapi.Schema(type=openapi.TYPE_INTEGER, default=2),
            'language_graphic': openapi.Schema(type=openapi.TYPE_STRING, enum=['es', 'en'], default='es'),
        }
    ),
    responses={
        202: openapi.Response(description="Reporte en cola"),
        400: openapi.Response(description="Error de validación"),
    },
    tags=['Analytics - Reportes Asincrónicos']
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_sales_summary_report(request):
    """
    Crea un reporte asíncrono de resumen de ventas con análisis comparativo.

    Este endpoint inicia la generación en segundo plano de un reporte financiero completo
    sobre ventas, incluyendo análisis de ingresos, tendencias temporales, y comparaciones
    con períodos anteriores. Genera gráficos de evolución y KPIs financieros clave.
    Se procesa de forma asíncrona mediante Celery.

    Args:
        request (Request): Objeto de solicitud DRF con los siguientes datos esperados:
            - from_date (str): Fecha inicial en formato ISO (YYYY-MM-DD) **[Requerido]**
            - to_date (str): Fecha final en formato ISO (default: fecha actual) **[Opcional]**
            - month_compare (int): Meses hacia atrás para comparar (default: 2) **[Opcional]**
            - language_graphic (str): Idioma 'es' o 'en' (default: 'es') **[Opcional]**

    Returns:
        Response: Respuesta DRF con estructura estándar:
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (dict): Datos del reporte creado
                * task_id (str): ID de la tarea Celery para consultar estado
                * report_id (int): ID del reporte en la base de datos
                * status (str): Estado inicial del reporte (PENDING)

            Status HTTP 201: Reporte creado y en cola correctamente
            Status HTTP 400: Errores de validación en los parámetros
            Status HTTP 403: Usuario sin permisos de administrador
            Status HTTP 500: Error interno durante la creación

    Raises:
        Exception: Captura y loguea cualquier error no manejado, retornando respuesta 500.

    Examples:
        >>> # Solicitud básica con solo fechas
        >>> POST /api/v2/admin/analytics/reports/sales-summary/create/
        >>> {
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31"
        >>> }

        >>> # Solicitud con comparación de 6 meses
        >>> POST /api/v2/admin/analytics/reports/sales-summary/create/
        >>> {
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31",
        >>>     "month_compare": 6,
        >>>     "language_graphic": "en"
        >>> }

    Notes:
        - El reporte se procesa de forma asíncrona usando Celery workers
        - Consultar estado del reporte: GET /reports/status/<task_id>/
        - Descargar archivo completado: GET /reports/<report_id>/download/
        - Requiere permisos de administrador (IsAdminUser permission class)
        - Incluye KPIs: total ventas, promedio diario, tendencia, comparativa
        - Gráficos de evolución temporal y comparación con períodos anteriores
        - Siempre genera Excel con múltiples hojas y gráficos embebidos

    References:
        - Django REST Framework: https://www.django-rest-framework.org/api-guide/requests/
        - Celery Tasks: https://docs.celeryq.dev/en/stable/userguide/tasks.html
        - drf-yasg: https://drf-yasg.readthedocs.io/en/stable/
    """
    serializer = SalesSummaryReportSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': 'Validation errors',
            'data': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        validated_data = serializer.validated_data

        # Convertir dates a strings ISO para JSON serialization
        parameters = {
            'from_date': validated_data['from_date'].isoformat(),
            'to_date': validated_data['to_date'].isoformat(),
            'month_compare': validated_data.get('month_compare', 6),
            'language_graphic': validated_data.get('language_graphic', 'es')
        }

        report = Report.objects.create(
            user=request.user,
            report_type=Report.ReportType.SALES_SUMMARY,
            parameters=parameters,
            status=Report.Status.PENDING
        )

        task = generate_sales_summary_report.delay(
            report_id=report.id,
            parameters=parameters
        )

        report.task_id = task.id
        report.save(update_fields=['task_id'])

        return Response({
            'success': True,
            'message': 'Report queued for processing',
            'data': {
                'task_id': task.id,
                'report_id': report.id,
                'status': report.status
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error creating sales summary report: {str(e)}")
        return Response({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_description="""
    **Crear Reporte de Productos Más Vendidos (Asíncrono)**
    
    Inicia la generación asíncrona de un reporte de top productos.
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['from_date'],
        properties={
            'from_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            'to_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            'limit': openapi.Schema(type=openapi.TYPE_INTEGER, default=10),
            'excel': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
            'graphic': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
            'download_graphic': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
            'language_graphic': openapi.Schema(type=openapi.TYPE_STRING, enum=['es', 'en'], default='es'),
        }
    ),
    responses={
        202: openapi.Response(description="Reporte en cola"),
        400: openapi.Response(description="Error de validación"),
    },
    tags=['Analytics - Reportes Asincrónicos']
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_top_products_report(request):
    """
    Crea un reporte asíncrono de productos más vendidos (ranking de ventas).

    Este endpoint inicia la generación en segundo plano de un reporte de análisis de
    productos más vendidos, ordenados por cantidad de unidades vendidas. Incluye gráficos
    de ranking, análisis comparativo y datos tabulares exportables. Se procesa de forma
    asíncrona mediante Celery para operaciones de larga duración.

    Args:
        request (Request): Objeto de solicitud DRF con los siguientes datos esperados:
            - from_date (str): Fecha inicial en formato ISO (YYYY-MM-DD) **[Requerido]**
            - to_date (str): Fecha final en formato ISO (default: fecha actual) **[Opcional]**
            - limit (int): Número de productos a incluir (default: 10) **[Opcional]**
            - excel (bool): Generar archivo Excel (default: False) **[Opcional]**
            - graphic (bool): Generar gráfico (default: True) **[Opcional]**
            - download_graphic (bool): Incluir PNG en ZIP (default: False) **[Opcional]**
            - language_graphic (str): Idioma 'es' o 'en' (default: 'es') **[Opcional]**

    Returns:
        Response: Respuesta DRF con estructura estándar:
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (dict): Datos del reporte creado
                * task_id (str): ID de la tarea Celery para consultar estado
                * report_id (int): ID del reporte en la base de datos
                * status (str): Estado inicial del reporte (PENDING)

            Status HTTP 201: Reporte creado y en cola correctamente
            Status HTTP 400: Errores de validación en los parámetros
            Status HTTP 403: Usuario sin permisos de administrador
            Status HTTP 500: Error interno durante la creación

    Raises:
        Exception: Captura y loguea cualquier error no manejado, retornando respuesta 500.

    Examples:
        >>> # Solicitud básica para top 10 productos
        >>> POST /api/v2/admin/analytics/reports/top-products/create/
        >>> {
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31"
        >>> }

        >>> # Solicitud para top 20 con Excel y gráfico
        >>> POST /api/v2/admin/analytics/reports/top-products/create/
        >>> {
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31",
        >>>     "limit": 20,
        >>>     "excel": true,
        >>>     "graphic": true,
        >>>     "download_graphic": true,
        >>>     "language_graphic": "es"
        >>> }

    Notes:
        - El reporte se procesa de forma asíncrona usando Celery workers
        - Consultar estado del reporte: GET /reports/status/<task_id>/
        - Descargar archivo completado: GET /reports/<report_id>/download/
        - Requiere permisos de administrador (IsAdminUser permission class)
        - El ranking se basa en cantidad de unidades vendidas (no en ingresos)
        - Incluye gráficos de barras horizontales para mejor visualización
        - Formatos de salida: Excel, PNG, o ZIP con ambos

    References:
        - Django REST Framework: https://www.django-rest-framework.org/api-guide/requests/
        - Celery Tasks: https://docs.celeryq.dev/en/stable/userguide/tasks.html
        - drf-yasg: https://drf-yasg.readthedocs.io/en/stable/
    """
    serializer = TopProductsReportSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': 'Validation errors',
            'data': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        validated_data = serializer.validated_data

        # Convertir dates a strings ISO para JSON serialization
        parameters = {
            'from_date': validated_data['from_date'].isoformat(),
            'to_date': validated_data['to_date'].isoformat(),
            'limit': validated_data.get('limit', 10),
            'excel': validated_data.get('excel', False),
            'download_graphic': validated_data.get('download_graphic', False),
            'language_graphic': validated_data.get('language_graphic', 'es')
        }

        report = Report.objects.create(
            user=request.user,
            report_type=Report.ReportType.TOP_PRODUCTS,
            parameters=parameters,
            status=Report.Status.PENDING
        )

        task = generate_top_products_report.delay(
            report_id=report.id,
            parameters=parameters
        )

        report.task_id = task.id
        report.save(update_fields=['task_id'])

        return Response({
            'success': True,
            'message': 'Report queued for processing',
            'data': {
                'task_id': task.id,
                'report_id': report.id,
                'status': report.status
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error creating top products report: {str(e)}")
        return Response({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_description="""
    **Crear Reporte de Análisis de Métodos de Pago (Asíncrono)**
    
    Inicia la generación asíncrona de un reporte de análisis de métodos de pago utilizados
    en las ventas durante un período específico.
    
    **Características del reporte:**
    - Distribución de pagos por método (efectivo, tarjeta, transferencia, etc.)
    - Análisis estadístico de preferencias de pago
    - Gráficos comparativos entre métodos de pago
    - Totales monetarios por cada método
    
    **Flujo de trabajo:**
    1. Crear solicitud de reporte con este endpoint → Recibir `task_id` y `report_id`
    2. Consultar estado con `/reports/status/<task_id>/` hasta `status=COMPLETED`
    3. Descargar archivo con `/reports/<report_id>/download/`
    
    **Formatos de salida:**
    - `excel=true, graphic=false`: Solo archivo Excel con datos tabulares
    - `excel=true, graphic=true, download_graphic=false`: Excel con gráfico embebido
    - `excel=true, graphic=true, download_graphic=true`: ZIP (Excel + PNG separado)
    - `excel=false, graphic=true, download_graphic=true`: Solo archivo PNG
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['from_date'],
        properties={
            'from_date': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                description='Fecha inicial del período (formato: YYYY-MM-DD)'
            ),
            'to_date': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                description='Fecha final del período (opcional, default: fecha actual)'
            ),
            'excel': openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                default=False,
                description='Generar archivo Excel con datos tabulares'
            ),
            'download_graphic': openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                default=False,
                description='Incluir gráfico PNG separado en ZIP o descarga directa'
            ),
            'language_graphic': openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=['es', 'en'],
                default='es',
                description='Idioma para etiquetas y títulos (español o inglés)'
            ),
        }
    ),
    responses={
        201: openapi.Response(
            description="Reporte en cola para procesamiento",
            examples={
                "application/json": {
                    "success": True,
                    "message": "Report queued for processing",
                    "data": {
                        "task_id": "abc123-def456-ghi789",
                        "report_id": 15,
                        "status": "PENDING"
                    }
                }
            }
        ),
        400: openapi.Response(
            description="Error de validación en parámetros",
            examples={
                "application/json": {
                    "success": False,
                    "message": "Validation errors",
                    "data": {
                        "from_date": ["Este campo es requerido."],
                        "to_date": ["La fecha final no puede ser anterior a la fecha inicial."]
                    }
                }
            }
        ),
        401: openapi.Response(description="No autenticado - Token JWT requerido"),
        403: openapi.Response(description="Permisos insuficientes - Se requiere rol de administrador"),
        500: openapi.Response(description="Error interno del servidor"),
    },
    tags=['Analytics - Reportes Asincrónicos']
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_payment_methods_report(request):
    """
    Crea un reporte asíncrono de análisis de métodos de pago.

    Este endpoint inicia la generación en segundo plano de un reporte detallado sobre
    los métodos de pago utilizados en las ventas durante un período específico. El reporte
    se procesa mediante Celery y puede incluir archivos Excel, gráficos PNG o ambos en ZIP.

    Args:
        request (Request): Objeto de solicitud DRF con los siguientes datos esperados:
            - from_date (str): Fecha inicial en formato ISO (YYYY-MM-DD) **[Requerido]**
            - to_date (str): Fecha final en formato ISO (default: fecha actual) **[Opcional]**
            - excel (bool): Generar archivo Excel (default: False) **[Opcional]**
            - download_graphic (bool): Incluir gráfico en descarga (default: False) **[Opcional]**
            - language_graphic (str): Idioma 'es' o 'en' (default: 'es') **[Opcional]**

    Returns:
        Response: Respuesta DRF con estructura estándar:
            - success (bool): Indica si la operación fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (dict): Datos del reporte creado
                * task_id (str): ID de la tarea Celery para consultar estado
                * report_id (int): ID del reporte en la base de datos
                * status (str): Estado inicial del reporte (PENDING)

            Status HTTP 201: Reporte creado y en cola correctamente
            Status HTTP 400: Errores de validación en los parámetros
            Status HTTP 403: Usuario sin permisos de administrador
            Status HTTP 500: Error interno durante la creación

    Raises:
        Exception: Captura y loguea cualquier error no manejado, retornando respuesta 500.

    Examples:
        >>> # Solicitud básica con solo fechas
        >>> POST /api/v2/admin/analytics/reports/payment-methods/create/
        >>> {
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31"
        >>> }

        >>> # Solicitud completa con Excel y gráfico en ZIP
        >>> POST /api/v2/admin/analytics/reports/payment-methods/create/
        >>> {
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31",
        >>>     "excel": true,
        >>>     "download_graphic": true,
        >>>     "language_graphic": "es"
        >>> }

    Notes:
        - El reporte se procesa de forma asíncrona usando Celery workers
        - Consultar estado del reporte con endpoint: GET /reports/status/<task_id>/
        - Descargar archivo completado con: GET /reports/<report_id>/download/
        - Requiere permisos de administrador (IsAdminUser permission class)
        - Los parámetros se serializan a JSON y se almacenan en el modelo Report
        - Las fechas se convierten a formato ISO string para compatibilidad JSON

    References:
        - Django REST Framework Request/Response: https://www.django-rest-framework.org/api-guide/requests/
        - Celery Task Management: https://docs.celeryq.dev/en/stable/userguide/tasks.html
        - drf-yasg Swagger Documentation: https://drf-yasg.readthedocs.io/en/stable/
    """
    serializer = PaymentMethodsReportSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': 'Validation errors',
            'data': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        validated_data = serializer.validated_data

        # Convertir dates a strings ISO para JSON serialization
        parameters = {
            'from_date': validated_data['from_date'].isoformat(),
            'to_date': validated_data['to_date'].isoformat(),
            'excel': validated_data.get('excel', False),
            'download_graphic': validated_data.get('download_graphic', False),
            'language_graphic': validated_data.get('language_graphic', 'es')
        }

        report = Report.objects.create(
            user=request.user,
            report_type=Report.ReportType.PAYMENT_METHODS,
            parameters=parameters,
            status=Report.Status.PENDING
        )

        task = generate_payment_methods_report.delay(
            report_id=report.id,
            parameters=parameters
        )

        report.task_id = task.id
        report.save(update_fields=['task_id'])

        return Response({
            'success': True,
            'message': 'Report queued for processing',
            'data': {
                'task_id': task.id,
                'report_id': report.id,
                'status': report.status
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(
            f"Error creating payment methods report: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_description="""
    **Crear Reporte de Cuotas Vencidas (Asíncrono)**
    
    Inicia la generación asíncrona de un reporte avanzado de análisis de cuotas vencidas
    en el sistema de crédito. Incluye distribución por días de mora, impacto monetario
    y evolución temporal.
    
    **Características del reporte:**
    - Análisis de aging (antigüedad de deuda): 1-30, 31-60, 61-90, 91-180, +180 días
    - Impacto monetario por rango de vencimiento
    - Gráficos de distribución y evolución temporal
    - Tabla detallada con clientes, montos y días de mora
    - Indicadores de riesgo crediticio
    
    **Flujo de trabajo:**
    1. Crear solicitud de reporte con este endpoint → Recibir `task_id` y `report_id`
    2. Consultar estado con `/reports/status/<task_id>/` periódicamente
    3. Cuando `status=COMPLETED`, descargar con `/reports/<report_id>/download/`
    
    **Formatos de salida disponibles:**
    - `excel=true, graphic=false`: Solo Excel con datos tabulares y métricas
    - `excel=true, graphic=true, download_graphic=false`: Excel con gráficos embebidos
    - `excel=true, graphic=true, download_graphic=true`: ZIP con Excel + PNG separados
    - `excel=false, graphic=true, download_graphic=true`: Solo gráficos PNG
    
    **Casos de uso:**
    - Gestión de cartera vencida
    - Análisis de riesgo crediticio
    - Reportes para gerencia financiera
    - Seguimiento de cobranzas
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['from_date'],
        properties={
            'from_date': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                description='Fecha inicial del período de análisis (formato: YYYY-MM-DD)'
            ),
            'to_date': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                description='Fecha final del período (opcional, default: fecha actual)'
            ),
            'excel': openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                default=False,
                description='Generar archivo Excel con datos detallados y KPIs'
            ),
            'download_graphic': openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                default=False,
                description='Incluir gráficos PNG en ZIP o descarga directa'
            ),
            'language_graphic': openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=['es', 'en'],
                default='es',
                description='Idioma para etiquetas, títulos y leyendas de gráficos'
            ),
        }
    ),
    responses={
        201: openapi.Response(
            description="Reporte en cola para procesamiento asíncrono",
            examples={
                "application/json": {
                    "success": True,
                    "message": "Report queued for processing",
                    "data": {
                        "task_id": "xyz789-abc123-def456",
                        "report_id": 28,
                        "status": "PENDING"
                    }
                }
            }
        ),
        400: openapi.Response(
            description="Error de validación en los parámetros enviados",
            examples={
                "application/json": {
                    "success": False,
                    "message": "Validation errors",
                    "data": {
                        "from_date": ["Este campo es requerido."],
                        "language_graphic": ["'fr' no es una opción válida. Opciones: 'es', 'en'."]
                    }
                }
            }
        ),
        401: openapi.Response(description="No autenticado - Se requiere token JWT válido"),
        403: openapi.Response(description="Permisos insuficientes - Solo administradores"),
        500: openapi.Response(
            description="Error interno del servidor durante la creación",
            examples={
                "application/json": {
                    "success": False,
                    "message": "Internal server error: Connection to Celery broker failed",
                    "data": None
                }
            }
        ),
    },
    tags=['Analytics - Reportes Asincrónicos']
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_overdue_installments_report(request):
    """
    Crea un reporte asíncrono de análisis de cuotas vencidas.

    Este endpoint inicia la generación en segundo plano de un reporte avanzado sobre
    cuotas vencidas en el sistema de crédito, incluyendo análisis de aging (antigüedad),
    impacto monetario por rango de vencimiento y evolución temporal. El reporte se procesa
    mediante Celery y puede generar archivos Excel con gráficos embebidos, PNG o ZIP.

    Args:
        request (Request): Objeto de solicitud DRF con los siguientes datos esperados:
            - from_date (str): Fecha inicial en formato ISO (YYYY-MM-DD) **[Requerido]**
            - to_date (str): Fecha final en formato ISO (default: fecha actual) **[Opcional]**
            - excel (bool): Generar archivo Excel con datos y KPIs (default: False) **[Opcional]**
            - download_graphic (bool): Incluir gráficos en descarga (default: False) **[Opcional]**
            - language_graphic (str): Idioma 'es' o 'en' (default: 'es') **[Opcional]**

    Returns:
        Response: Respuesta DRF con estructura estándar del sistema:
            - success (bool): Indica si la operación fue exitosa (true/false)
            - message (str): Mensaje descriptivo del resultado de la operación
            - data (dict | None): Datos del reporte creado o None en caso de error
                * task_id (str): UUID de la tarea Celery para rastreo
                * report_id (int): ID del registro Report en base de datos
                * status (str): Estado inicial del reporte ('PENDING')

            **Status HTTP 201 CREATED**: Reporte creado y encolado exitosamente
            **Status HTTP 400 BAD REQUEST**: Errores de validación en parámetros
            **Status HTTP 403 FORBIDDEN**: Usuario sin permisos de administrador
            **Status HTTP 500 INTERNAL SERVER ERROR**: Error no manejado del servidor

    Raises:
        Exception: Captura cualquier excepción no manejada, la loguea con traceback
                   completo y retorna respuesta HTTP 500 con mensaje de error.

    Examples:
        >>> # Ejemplo 1: Reporte básico solo con rango de fechas
        >>> POST /api/v2/admin/analytics/reports/overdue-installments/create/
        >>> {
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31"
        >>> }
        >>> # Respuesta:
        >>> {
        >>>     "success": true,
        >>>     "message": "Report queued for processing",
        >>>     "data": {
        >>>         "task_id": "abc-123-def",
        >>>         "report_id": 42,
        >>>         "status": "PENDING"
        >>>     }
        >>> }

        >>> # Ejemplo 2: Reporte completo con Excel y gráficos en español
        >>> POST /api/v2/admin/analytics/reports/overdue-installments/create/
        >>> {
        >>>     "from_date": "2024-01-01",
        >>>     "to_date": "2024-12-31",
        >>>     "excel": true,
        >>>     "download_graphic": true,
        >>>     "language_graphic": "es"
        >>> }

    Notes:
        - **Procesamiento asíncrono**: El reporte se genera en background via Celery
        - **Rangos de aging**: 1-30, 31-60, 61-90, 91-180, +180 días de vencimiento
        - **Consultar estado**: Use GET /reports/status/<task_id>/ para monitorear
        - **Descargar resultado**: GET /reports/<report_id>/download/ cuando status=COMPLETED
        - **Permisos**: Requiere IsAdminUser (django.contrib.auth admin o staff=True)
        - **Serialización JSON**: Las fechas date se convierten a ISO string para JSONField
        - **Logging**: Errores se registran con logger.error(..., exc_info=True) para debugging
        - **Formatos de salida**:
            * Excel solo: Datos tabulares + hojas de resumen con KPIs
            * Excel + graphic: Incluye gráficos embebidos en segunda hoja
            * ZIP: Contiene Excel + archivos PNG separados para impresión

    References:
        - Django REST Framework Responses: https://www.django-rest-framework.org/api-guide/responses/
        - Celery Delayed Tasks: https://docs.celeryq.dev/en/stable/userguide/calling.html
        - drf-yasg OpenAPI Schema: https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
        - Aging Analysis: https://www.investopedia.com/terms/a/accounts-receivable-aging.asp
    """
    serializer = OverdueInstallmentsReportSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': 'Validation errors',
            'data': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        validated_data = serializer.validated_data

        # Convertir dates a strings ISO para JSON serialization
        parameters = {
            'from_date': validated_data['from_date'].isoformat(),
            'to_date': validated_data['to_date'].isoformat(),
            'excel': validated_data.get('excel', False),
            'download_graphic': validated_data.get('download_graphic', False),
            'language_graphic': validated_data.get('language_graphic', 'es')
        }

        report = Report.objects.create(
            user=request.user,
            report_type=Report.ReportType.OVERDUE_INSTALLMENTS,
            parameters=parameters,
            status=Report.Status.PENDING
        )

        task = generate_overdue_installments_report.delay(
            report_id=report.id,
            parameters=parameters
        )

        report.task_id = task.id
        report.save(update_fields=['task_id'])

        logger.info(
            f"Overdue installments report created: report_id={report.id}, "
            f"task_id={task.id}, user={request.user.username}"
        )

        return Response({
            'success': True,
            'message': 'Report queued for processing',
            'data': {
                'task_id': task.id,
                'report_id': report.id,
                'status': report.status
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(
            f"Error creating overdue installments report: {str(e)}",
            exc_info=True
        )
        return Response({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_description="""
    **Consultar Estado de Reporte**
    
    Consulta el estado actual de un reporte en procesamiento.
    
    **Estados posibles:**
    - `PENDING`: Reporte en cola, aún no se ha iniciado el procesamiento
    - `PROCESSING`: Reporte en proceso de generación
    - `COMPLETED`: Reporte completado exitosamente, listo para descargar
    - `FAILED`: Reporte falló durante la generación
    
    **Ejemplo de uso:**
    ```
    GET /api/analytics/reports/status/abc123-def456/
    ```
    """,
    responses={
        200: openapi.Response(
            description="Estado del reporte",
            examples={
                "application/json": {
                    "success": True,
                    "message": "Estado del reporte",
                    "data": {
                        "id": 1,
                        "task_id": "abc123-def456",
                        "report_type": "PRODUCT_ROTATION",
                        "report_type_display": "Rotación de Productos",
                        "status": "COMPLETED",
                        "status_display": "Completado",
                        "file_url": "http://example.com/media/reports/2024/01/01/file.xlsx",
                        "parameters": {},
                        "error_message": None,
                        "created_at": "2024-01-01T10:00:00Z",
                        "completed_at": "2024-01-01T10:05:00Z"
                    }
                }
            }
        ),
        404: openapi.Response(description="Reporte no encontrado"),
    },
    tags=['Analytics - Reportes Asincrónicos']
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def check_report_status(request, task_id):
    """
    Consulta el estado actual de un reporte en procesamiento asíncrono.

    Este endpoint permite verificar el progreso de un reporte que se está generando
    en segundo plano mediante Celery. Retorna información completa del estado actual,
    metadatos del reporte, y mensaje de error en caso de fallo.

    Args:
        request (Request): Objeto de solicitud DRF del usuario autenticado
        task_id (str): ID de la tarea Celery (UUID) recibido al crear el reporte

    Returns:
        Response: Respuesta DRF con estructura estándar:
            - success (bool): Indica si la consulta fue exitosa
            - message (str): Mensaje descriptivo del resultado
            - data (dict): Datos del estado del reporte
                * id (int): ID del reporte en base de datos
                * task_id (str): ID de la tarea Celery
                * report_type (str): Tipo de reporte (código)
                * report_type_display (str): Tipo de reporte (legible)
                * status (str): Estado actual (PENDING/PROCESSING/COMPLETED/FAILED)
                * status_display (str): Estado en formato legible
                * file_url (str|null): URL del archivo si está completado
                * parameters (dict): Parámetros usados para generar el reporte
                * error_message (str|null): Mensaje de error si falló
                * created_at (str): Timestamp de creación ISO
                * completed_at (str|null): Timestamp de finalización ISO

            Status HTTP 200: Consulta exitosa
            Status HTTP 403: Usuario sin permiso para ver este reporte
            Status HTTP 404: Reporte no encontrado
            Status HTTP 500: Error interno del servidor

    Raises:
        Report.DoesNotExist: Cuando no existe un reporte con ese task_id
        Exception: Captura cualquier error no manejado, loguea y retorna 500

    Examples:
        >>> # Consultar estado de un reporte en procesamiento
        >>> GET /api/v2/admin/analytics/reports/status/abc123-def456/
        >>> # Respuesta:
        >>> {
        >>>     "success": true,
        >>>     "message": "Report status",
        >>>     "data": {
        >>>         "id": 42,
        >>>         "task_id": "abc123-def456",
        >>>         "report_type": "PRODUCT_ROTATION",
        >>>         "status": "COMPLETED",
        >>>         "file_url": "http://example.com/media/reports/file.xlsx",
        >>>         ...
        >>>     }
        >>> }

    Notes:
        - Usar este endpoint para polling periódico hasta que status sea COMPLETED
        - El usuario debe ser el propietario del reporte o superusuario
        - Estados posibles: PENDING, PROCESSING, COMPLETED, FAILED
        - Cuando COMPLETED, usar endpoint download_report para obtener el archivo
        - Recomendación: polling cada 3-5 segundos para reportes grandes

    References:
        - Celery Task States: https://docs.celeryq.dev/en/stable/userguide/tasks.html#states
        - Django REST Framework: https://www.django-rest-framework.org/api-guide/requests/
    """
    try:
        report = Report.objects.get(task_id=task_id)

        if report.user != request.user and not request.user.is_superuser:
            return Response(
                {
                    'success': False,
                    'message': 'You do not have permission to view this report'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ReportStatusSerializer(
            report, context={'request': request})

        return Response(
            {
                'success': True,
                'message': 'Report status',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    except Report.DoesNotExist:
        return Response(
            {
                'success': False,
                'message': 'Report not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(
            f"Error checking report status: {str(e)}", exc_info=True)
        return server_error_response(f"Internal server error: {str(e)}")


@swagger_auto_schema(
    method='get',
    operation_description="""
    **Descargar Reporte Completado**
    
    Descarga el archivo de un reporte completado.
    
    **Requisitos:**
    - El reporte debe estar en estado `COMPLETED`
    - El usuario debe ser el propietario del reporte o superusuario
    
    **Ejemplo de uso:**
    ```
    GET /api/analytics/reports/1/download/
    ```
    """,
    responses={
        200: openapi.Response(
            description="Archivo del reporte",
            schema=openapi.Schema(type=openapi.TYPE_FILE)
        ),
        400: openapi.Response(description="Reporte aún no está completado"),
        403: openapi.Response(description="Sin permisos"),
        404: openapi.Response(description="Reporte no encontrado"),
    },
    tags=['Analytics - Reportes Asincrónicos']
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def download_report(request, report_id):
    """
    Descarga el archivo de un reporte completado.

    Este endpoint permite descargar el archivo generado de un reporte que ha finalizado
    exitosamente su procesamiento. Retorna el archivo binario con los headers HTTP
    apropiados para descarga directa en el navegador.

    Args:
        request (Request): Objeto de solicitud DRF del usuario autenticado
        report_id (int): ID del reporte en la base de datos

    Returns:
        FileResponse | Response: Archivo binario o respuesta de error:
            - FileResponse: Archivo binario con headers de descarga cuando exitoso
                * Content-Type: Según extensión (xlsx, zip, png, pdf)
                * Content-Disposition: attachment con nombre de archivo
            - Response JSON: En caso de error con estructura:
                * success (bool): false
                * message (str): Descripción del error

            Status HTTP 200: Descarga exitosa (FileResponse)
            Status HTTP 400: Reporte no está completado aún
            Status HTTP 403: Usuario sin permiso para descargar este reporte
            Status HTTP 404: Reporte no encontrado o sin archivo asociado
            Status HTTP 500: Error interno del servidor

    Raises:
        Report.DoesNotExist: Cuando no existe un reporte con ese ID
        Exception: Captura cualquier error no manejado, loguea y retorna 500

    Examples:
        >>> # Descargar archivo de reporte completado
        >>> GET /api/v2/admin/analytics/reports/42/download/
        >>> # Respuesta: Archivo binario (Excel, ZIP, PNG, etc.)

        >>> # Intentar descargar reporte incompleto
        >>> GET /api/v2/admin/analytics/reports/43/download/
        >>> # Respuesta JSON:
        >>> {
        >>>     "success": false,
        >>>     "message": "Report is not completed yet. Current status: Processing"
        >>> }

    Notes:
        - Solo descarga reportes con status=COMPLETED
        - El usuario debe ser propietario del reporte o superusuario
        - Tipos de archivo soportados: .xlsx, .xls, .zip, .pdf, .png
        - Content-Type se determina automáticamente por extensión
        - El archivo se transmite como stream para archivos grandes
        - Se registra log de auditoría al descargar

    References:
        - Django FileResponse: https://docs.djangoproject.com/en/5.1/ref/request-response/#fileresponse-objects
        - HTTP Content-Disposition: https://datatracker.ietf.org/doc/html/rfc6266
        - MIME Types: https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types
    """
    from .models import Report
    from django.http import FileResponse
    import os

    try:
        report = Report.objects.get(id=report_id)

        if report.user != request.user and not request.user.is_superuser:
            return Response(
                {
                    'success': False,
                    'message': 'You do not have permission to download this report'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        if report.status != Report.Status.COMPLETED:
            return Response(
                {
                    'success': False,
                    'message': f'Report is not completed yet. Current status: {report.get_status_display()}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not report.file:
            return Response(
                {
                    'success': False,
                    'message': 'Report has no associated file'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        file_extension = os.path.splitext(report.file.name)[1].lower()
        content_type_mapping = {
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.zip': 'application/zip',
            '.pdf': 'application/pdf',
            '.png': 'image/png',
        }
        content_type = content_type_mapping.get(
            file_extension, 'application/octet-stream')

        response = FileResponse(
            report.file.open('rb'),
            content_type=content_type
        )

        filename = os.path.basename(report.file.name)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        logger.info(
            f"Report {report_id} downloaded by user {request.user.username}")

        return response

    except Report.DoesNotExist:
        return Response(
            {
                'success': False,
                'message': 'Report not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}", exc_info=True)
        return server_error_response(f"Internal server error: {str(e)}")


@swagger_auto_schema(
    method='get',
    operation_description="""
    **Listar Reportes del Usuario**
    
    Lista todos los reportes creados por el usuario autenticado.
    Opcionalmente filtra por tipo de reporte y estado.
    """,
    manual_parameters=[
        openapi.Parameter(
            'report_type',
            openapi.IN_QUERY,
            description="Filtrar por tipo de reporte",
            type=openapi.TYPE_STRING,
            enum=['PRODUCT_ROTATION', 'MOVEMENTS_INPUT_OUTPUT', 'SALES_SUMMARY',
                  'TOP_PRODUCTS', 'PAYMENT_METHODS', 'OVERDUE_INSTALLMENTS'],
            required=False
        ),
        openapi.Parameter(
            'status',
            openapi.IN_QUERY,
            description="Filtrar por estado",
            type=openapi.TYPE_STRING,
            enum=['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'],
            required=False
        ),
    ],
    responses={
        200: openapi.Response(description="Lista de reportes"),
    },
    tags=['Analytics - Reportes Asincrónicos']
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_user_reports(request):
    """
    Lista todos los reportes del usuario autenticado con filtros opcionales.

    Este endpoint retorna una lista paginable de todos los reportes creados por el usuario
    autenticado, con capacidad de filtrado por tipo de reporte y estado. Los superusuarios
    pueden ver todos los reportes del sistema.

    Args:
        request (Request): Objeto de solicitud DRF con query parameters opcionales:
            - report_type (str): Filtrar por tipo específico **[Opcional]**
                Valores: PRODUCT_ROTATION, MOVEMENTS_INPUT_OUTPUT, SALES_SUMMARY,
                        TOP_PRODUCTS, PAYMENT_METHODS, OVERDUE_INSTALLMENTS
            - status (str): Filtrar por estado **[Opcional]**
                Valores: PENDING, PROCESSING, COMPLETED, FAILED

    Returns:
        Response: Respuesta DRF con estructura estándar:
            - success (bool): true
            - message (str): "Reports list"
            - data (list): Array de objetos de reporte con:
                * id (int): ID del reporte
                * report_type (str): Tipo de reporte (código)
                * report_type_display (str): Tipo legible
                * status (str): Estado actual
                * status_display (str): Estado legible
                * created_at (str): Timestamp de creación ISO
                * completed_at (str|null): Timestamp de finalización ISO
                * file (str|null): Nombre del archivo
            - count (int): Total de reportes retornados

            Status HTTP 200: Consulta exitosa
            Status HTTP 500: Error interno del servidor

    Raises:
        Exception: Captura cualquier error no manejado, loguea y retorna 500

    Examples:
        >>> # Listar todos los reportes del usuario
        >>> GET /api/v2/admin/analytics/reports/list/
        >>> # Respuesta:
        >>> {
        >>>     "success": true,
        >>>     "message": "Reports list",
        >>>     "data": [
        >>>         {
        >>>             "id": 42,
        >>>             "report_type": "PRODUCT_ROTATION",
        >>>             "report_type_display": "Rotación de Productos",
        >>>             "status": "COMPLETED",
        >>>             "created_at": "2024-01-01T10:00:00Z",
        >>>             ...
        >>>         }
        >>>     ],
        >>>     "count": 15
        >>> }

        >>> # Filtrar por tipo y estado
        >>> GET /api/v2/admin/analytics/reports/list/?report_type=SALES_SUMMARY&status=COMPLETED
        >>> # Respuesta: Solo reportes de ventas completados

    Notes:
        - Los superusuarios ven todos los reportes del sistema
        - Los usuarios normales solo ven sus propios reportes
        - Los resultados se ordenan por fecha de creación (más recientes primero)
        - Se pueden combinar múltiples filtros
        - Útil para dashboard de historial de reportes

    References:
        - Django QuerySet Filtering: https://docs.djangoproject.com/en/5.1/ref/models/querysets/#filter
        - DRF Query Parameters: https://www.django-rest-framework.org/api-guide/requests/#query_params
    """
    from .models import Report
    from .serializers import ReportListSerializer

    try:
        if request.user.is_superuser:
            queryset = Report.objects.all()
        else:
            queryset = Report.objects.filter(user=request.user)

        report_type = request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        report_status = request.query_params.get('status')
        if report_status:
            queryset = queryset.filter(status=report_status)

        queryset = queryset.order_by('-created_at')

        serializer = ReportListSerializer(queryset, many=True)

        return Response(
            {
                'success': True,
                'message': 'Reports list',
                'data': serializer.data,
                'count': queryset.count()
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}", exc_info=True)
        return server_error_response(f"Internal server error: {str(e)}")
