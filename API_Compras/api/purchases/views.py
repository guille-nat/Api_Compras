from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from decimal import Decimal, InvalidOperation
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from api.view_tags import purchases_admin
from api.permissions import PermissionDenied
import logging
from api.view_tags import (
    purchases_status_management,
    purchases_installments_management,
    purchases_discounts,
    purchases_admin,
    purchases_user_management,
    purchases_crud,
)
from .models import Purchase
from .serializers import PurchaseSerializer
from .services import (
    update_purchase_status as service_update_purchase_status,
    update_purchase_installments as service_update_purchase_installments,
    update_purchase_discount as service_update_purchase_discount,
    delete_purchase_admin,
    get_user_purchases,
    get_admin_purchases_with_filters,
    get_single_purchase
)

logger = logging.getLogger(__name__)
PAGINATION_PAGE_SIZE_PURCHASES = 10


@swagger_auto_schema(
    method='patch',
    operation_summary="Actualizar estado de compra",
    operation_description="Actualiza el estado de una compra específica. Permite cambiar entre estados OPEN, PAID y CANCELLED.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'new_status': openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=['OPEN', 'PAID', 'CANCELLED'],
                description="Nuevo estado de la compra"
            ),
            'reason': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Motivo de la actualización (opcional)"
            )
        },
        required=['new_status']
    ),
    responses={
        200: openapi.Response(
            description="Estado actualizado exitosamente",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: openapi.Response(description="Datos inválidos o estado no válido"),
        403: openapi.Response(description="Sin permisos para actualizar esta compra"),
        404: openapi.Response(description="Compra no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=purchases_status_management()
)
@api_view(['PATCH'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
@extend_schema(parameters=[OpenApiParameter('purchase_id', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID de la compra')], tags=purchases_status_management())
def update_purchase_status(request, purchase_id):
    """
    Actualiza el estado de una compra.

    Body Parameters:
    - new_status (str): Nuevo estado ['OPEN', 'PAID', 'CANCELLED']
    - reason (str, optional): Motivo de la actualización
    """
    try:
        new_status = request.data.get('new_status')
        reason = request.data.get('reason')

        if not new_status:
            return Response({
                "success": False,
                "message": "new_status is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        result = service_update_purchase_status(
            purchase_id=int(purchase_id),
            new_status=new_status,
            user_id=request.user.pk,
            reason=reason
        )

        return Response(result, status=status.HTTP_200_OK)

    except ValueError as e:
        logger.warning(f"Invalid data for status update: {str(e)}")
        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except PermissionError as e:
        logger.warning(f"Permission denied for status update: {str(e)}")
        # Intentar determinar el tipo de error de permisos para respuesta específica
        if "can only update your own purchases" in str(e).lower():
            error_response = PermissionDenied.purchase_access_denied(
                request.user.pk, int(purchase_id), "modify"
            )
        elif "only administrators can" in str(e).lower():
            error_response = PermissionDenied.admin_required(
                "cancel_paid" if "paid" in str(e).lower() else "reactivate_cancelled")
        else:
            error_response = {
                "success": False,
                "message": str(e),
                "data": {"error_type": "permission_denied"}
            }
        return Response(error_response, status=status.HTTP_403_FORBIDDEN)

    except Exception as e:
        logger.error(f"Unexpected error updating purchase status: {str(e)}")
        return Response({
            "success": False,
            "message": "An unexpected error occurred"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='patch',
    operation_summary="Actualizar cuotas de compra",
    operation_description="Modifica la cantidad de cuotas de una compra existente. Permite cambios entre 1 y 60 cuotas.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'new_installments_count': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                minimum=1,
                maximum=60,
                description="Nueva cantidad de cuotas"
            ),
            'reason': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Motivo de la actualización (opcional)"
            )
        },
        required=['new_installments_count']
    ),
    responses={
        200: openapi.Response(description="Cuotas actualizadas exitosamente"),
        400: openapi.Response(description="Cantidad de cuotas inválida (1-60)"),
        403: openapi.Response(description="Sin permisos para actualizar esta compra"),
        404: openapi.Response(description="Compra no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=purchases_installments_management()
)
@api_view(['PATCH'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
@extend_schema(parameters=[OpenApiParameter('purchase_id', OpenApiTypes.INT, OpenApiParameter.PATH, description='ID de la compra')], tags=purchases_installments_management())
def update_purchase_installments(request, purchase_id):
    """
    Actualiza la cantidad de cuotas de una compra.

    Body Parameters:
    - new_installments_count (int): Nueva cantidad de cuotas (1-60)
    - reason (str, optional): Motivo de la actualización
    """
    try:
        new_installments_count = request.data.get('new_installments_count')
        reason = request.data.get('reason')

        if not new_installments_count:
            return Response({
                "success": False,
                "message": "new_installments_count is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validar que sea entero
        try:
            new_installments_count = int(new_installments_count)
        except (ValueError, TypeError):
            return Response({
                "success": False,
                "message": "new_installments_count must be a valid integer"
            }, status=status.HTTP_400_BAD_REQUEST)

        result = service_update_purchase_installments(
            purchase_id=int(purchase_id),
            new_installments_count=new_installments_count,
            user_id=request.user.pk,
            reason=reason
        )

        return Response(result, status=status.HTTP_200_OK)

    except ValueError as e:
        logger.warning(f"Invalid data for installments update: {str(e)}")
        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except PermissionError as e:
        logger.warning(f"Permission denied for installments update: {str(e)}")
        if "can only update your own purchases" in str(e).lower():
            error_response = PermissionDenied.purchase_access_denied(
                request.user.pk, int(purchase_id), "modify"
            )
        else:
            error_response = {
                "success": False,
                "message": str(e),
                "data": {"error_type": "permission_denied"}
            }
        return Response(error_response, status=status.HTTP_403_FORBIDDEN)

    except Exception as e:
        logger.error(
            f"Unexpected error updating purchase installments: {str(e)}")
        return Response({
            "success": False,
            "message": "An unexpected error occurred"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='patch',
    operation_summary="Actualizar descuento de compra",
    operation_description="Modifica el descuento aplicado a una compra específica.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'new_discount': openapi.Schema(
                type=openapi.TYPE_NUMBER,
                format=openapi.FORMAT_DECIMAL,
                minimum=0.00,
                description="Nuevo descuento a aplicar"
            ),
            'reason': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Motivo de la actualización (opcional)"
            )
        },
        required=['new_discount']
    ),
    responses={
        200: openapi.Response(description="Descuento actualizado exitosamente"),
        400: openapi.Response(description="Descuento inválido (debe ser >= 0)"),
        403: openapi.Response(description="Sin permisos para actualizar esta compra"),
        404: openapi.Response(description="Compra no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=purchases_discounts()
)
@api_view(['PATCH'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_purchase_discount(request, purchase_id):
    """
    Actualiza el descuento aplicado a una compra.

    Body Parameters:
    - new_discount (decimal): Nuevo descuento a aplicar (0.00 o mayor)
    - reason (str, optional): Motivo de la actualización
    """
    try:
        new_discount = request.data.get('new_discount')
        reason = request.data.get('reason')

        if new_discount is None:
            return Response({
                "success": False,
                "message": "new_discount is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validar y convertir a Decimal
        try:
            new_discount = Decimal(str(new_discount))
        except (ValueError, InvalidOperation, TypeError):
            return Response({
                "success": False,
                "message": "new_discount must be a valid decimal number"
            }, status=status.HTTP_400_BAD_REQUEST)

        result = service_update_purchase_discount(
            purchase_id=int(purchase_id),
            new_discount=new_discount,
            user_id=request.user.pk,
            reason=reason
        )

        return Response(result, status=status.HTTP_200_OK)

    except ValueError as e:
        logger.warning(f"Invalid data for discount update: {str(e)}")
        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except PermissionError as e:
        logger.warning(f"Permission denied for discount update: {str(e)}")
        if "can only update your own purchases" in str(e).lower():
            error_response = PermissionDenied.purchase_access_denied(
                request.user.pk, int(purchase_id), "modify"
            )
        else:
            error_response = {
                "success": False,
                "message": str(e),
                "data": {"error_type": "permission_denied"}
            }
        return Response(error_response, status=status.HTTP_403_FORBIDDEN)

    except Exception as e:
        logger.error(f"Unexpected error updating purchase discount: {str(e)}")
        return Response({
            "success": False,
            "message": "An unexpected error occurred"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='delete',
    operation_summary="Eliminar compra (Admin)",
    operation_description="Elimina una compra del sistema. Solo disponible para administradores.",
    manual_parameters=[
        openapi.Parameter(
            'force_delete',
            openapi.IN_QUERY,
            description="Fuerza la eliminación incluso si hay dependencias",
            type=openapi.TYPE_BOOLEAN,
            default=False
        )
    ],
    responses={
        200: openapi.Response(description="Compra eliminada exitosamente"),
        400: openapi.Response(description="No se puede eliminar por dependencias"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Compra no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=purchases_admin()
)
@api_view(['DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminUser])
def admin_delete_purchase(request, purchase_id):
    """
    Elimina una compra (solo administradores).

    Query Parameters:
    - force_delete (bool, optional): Si True, fuerza la eliminación
    """
    try:
        force_delete = request.GET.get(
            'force_delete', 'false').lower() == 'true'

        result = delete_purchase_admin(
            purchase_id=int(purchase_id),
            admin_user_id=request.user.pk,
            force_delete=force_delete
        )

        return Response(result, status=status.HTTP_200_OK)

    except ValueError as e:
        logger.warning(f"Invalid data for purchase deletion: {str(e)}")
        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except PermissionError as e:
        logger.warning(f"Permission denied for purchase deletion: {str(e)}")
        if "only staff users" in str(e).lower():
            error_response = PermissionDenied.admin_required("delete_purchase")
        else:
            error_response = {
                "success": False,
                "message": str(e),
                "data": {"error_type": "permission_denied"}
            }
        return Response(error_response, status=status.HTTP_403_FORBIDDEN)

    except Exception as e:
        logger.error(f"Unexpected error deleting purchase: {str(e)}")
        return Response({
            "success": False,
            "message": "An unexpected error occurred"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_summary="Mis compras",
    operation_description="Obtiene todas las compras del usuario autenticado con filtros opcionales.",
    manual_parameters=[
        openapi.Parameter(
            'status',
            openapi.IN_QUERY,
            description="Filtrar por estado de compra",
            type=openapi.TYPE_STRING,
            enum=['OPEN', 'PAID', 'CANCELLED']
        ),
        openapi.Parameter(
            'date_from',
            openapi.IN_QUERY,
            description="Fecha inicio (YYYY-MM-DD)",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATE
        ),
        openapi.Parameter(
            'date_to',
            openapi.IN_QUERY,
            description="Fecha fin (YYYY-MM-DD)",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATE
        )
    ],
    responses={
        200: PurchaseSerializer(many=True),
        401: openapi.Response(description="No autenticado"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=purchases_user_management()
)
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_my_purchases(request):
    """
    Lista las compras del usuario autenticado con filtros.

    Query Parameters:
    - status (str, optional): Filtrar por estado
    """
    try:
        status_filter = request.GET.get('status')

        result = get_user_purchases(
            user_id=request.user.pk,
            status=status_filter
        )

        # Verificar si el servicio retornó error
        if not result.get('success', False):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        # Obtener las compras del resultado del servicio
        purchases_data = result.get('data', {}).get('purchases', [])

        # Crear objetos Purchase desde los datos para serializar correctamente
        purchase_ids = [purchase.get(
            'id') for purchase in purchases_data if purchase.get('id')]
        purchases_queryset = Purchase.objects.filter(
            id__in=purchase_ids).order_by('-created_at')

        # Aplicar paginación estándar
        paginator = PageNumberPagination()
        paginator.page_size = PAGINATION_PAGE_SIZE_PURCHASES
        paginated_purchases = paginator.paginate_queryset(
            purchases_queryset, request)

        # Serializar los datos paginados
        serializer = PurchaseSerializer(paginated_purchases, many=True)

        # Retornar respuesta paginada estándar
        return paginator.get_paginated_response(serializer.data)

    except Exception as e:
        logger.error(f"Unexpected error getting user purchases: {str(e)}")
        return Response({
            "success": False,
            "message": "An unexpected error occurred"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_summary="Todas las compras (Admin)",
    operation_description="Obtiene todas las compras del sistema con filtros avanzados. Solo para administradores.",
    manual_parameters=[
        openapi.Parameter(
            'user_id',
            openapi.IN_QUERY,
            description="Filtrar por ID de usuario",
            type=openapi.TYPE_INTEGER
        ),
        openapi.Parameter(
            'status',
            openapi.IN_QUERY,
            description="Filtrar por estado",
            type=openapi.TYPE_STRING,
            enum=['OPEN', 'PAID', 'CANCELLED']
        ),
        openapi.Parameter(
            'date_from',
            openapi.IN_QUERY,
            description="Fecha inicio",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATE
        ),
        openapi.Parameter(
            'date_to',
            openapi.IN_QUERY,
            description="Fecha fin",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATE
        )
    ],
    responses={
        200: PurchaseSerializer(many=True),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=purchases_admin()
)
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminUser])
def get_admin_all_purchases(request):
    """
    Lista todas las compras con filtros avanzados (solo administradores).

    Query Parameters:
    - status (str, optional): Filtrar por estado
    - start_date (str, optional): Fecha inicial (YYYY-MM-DD)
    - end_date (str, optional): Fecha final (YYYY-MM-DD)
    - min_amount (decimal, optional): Monto mínimo
    - max_amount (decimal, optional): Monto máximo
    - user_id (int, optional): Filtrar por usuario específico
    - user_username (str, optional): Filtrar por username
    - installments_count (int, optional): Filtrar por cantidad de cuotas
    - has_discount (bool, optional): Filtrar por si tiene descuento
    """
    try:
        filters = {
            'status': request.GET.get('status'),
            'start_date': request.GET.get('start_date'),
            'end_date': request.GET.get('end_date'),
            'min_amount': request.GET.get('min_amount'),
            'max_amount': request.GET.get('max_amount'),
            'user_id': request.GET.get('user_id'),
            'user_username': request.GET.get('user_username'),
            'installments_count': request.GET.get('installments_count'),
            'has_discount': request.GET.get('has_discount')
        }

        # Limpiar filtros vacíos
        filters = {k: v for k, v in filters.items()
                   if v is not None and v != ''}

        try:
            result = get_admin_purchases_with_filters(**filters)

            # Verificar si el servicio retornó error
            if not result.get('success', False):
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

            # Obtener las compras del resultado del servicio
            purchases_data = result.get('data', {}).get('purchases', [])

            # Crear objetos Purchase desde los datos para serializar correctamente
            purchase_ids = [purchase.get(
                'id') for purchase in purchases_data if purchase.get('id')]
            purchases_queryset = Purchase.objects.filter(
                id__in=purchase_ids).order_by('-created_at')

            # Aplicar paginación estándar
            paginator = PageNumberPagination()
            paginator.page_size = PAGINATION_PAGE_SIZE_PURCHASES
            paginated_purchases = paginator.paginate_queryset(
                purchases_queryset, request)

            # Serializar los datos paginados
            serializer = PurchaseSerializer(paginated_purchases, many=True)

            # Retornar respuesta paginada estándar
            return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            logger.error(f"Unexpected error getting admin purchases: {str(e)}")
            return Response({
                "success": False,
                "message": "An unexpected error occurred"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        # Catch-all for errors building filters or other unexpected failures
        logger.error(f"Unexpected error in get_admin_all_purchases: {str(e)}")
        return Response({
            "success": False,
            "message": "An unexpected error occurred"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    methods=['get', 'post'],
    operation_summary="Listar/Crear compras",
    operation_description="GET: Lista compras del usuario. POST: Crea una nueva compra.",
    request_body=PurchaseSerializer,
    responses={
        200: PurchaseSerializer(many=True),
        201: PurchaseSerializer,
        400: openapi.Response(description="Datos inválidos"),
        401: openapi.Response(description="No autenticado")
    },
    tags=purchases_crud()
)
@api_view(['GET', 'POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def purchase_list_create(request):
    """
    Lista todas las compras del usuario o crea una nueva compra.

    GET: Lista compras del usuario (usuarios normales) o todas (superusuarios)
    POST: Crea una nueva compra
    """
    if request.method == 'GET':
        user = request.user

        if user.is_superuser:
            purchases = Purchase.objects.all().order_by('-created_at')
        else:
            purchases = Purchase.objects.filter(
                user=user).order_by('-created_at')

        # Aplicar paginación estándar
        paginator = PageNumberPagination()
        paginator.page_size = PAGINATION_PAGE_SIZE_PURCHASES
        paginated_purchases = paginator.paginate_queryset(purchases, request)

        # Serializar los datos paginados
        serializer = PurchaseSerializer(paginated_purchases, many=True)

        # Retornar respuesta paginada estándar
        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        serializer = PurchaseSerializer(data=request.data)

        if serializer.is_valid():
            # Asignar el usuario autenticado
            serializer.save(user=request.user)
            return Response({
                "success": True,
                "message": "Purchase created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "success": False,
                "message": "Invalid data",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    methods=['get', 'put', 'delete'],
    operation_summary="Detalle de compra",
    operation_description="Operaciones CRUD sobre una compra específica.",
    request_body=PurchaseSerializer,
    responses={
        200: PurchaseSerializer,
        204: openapi.Response(description="Eliminado exitosamente"),
        400: openapi.Response(description="Datos inválidos"),
        403: openapi.Response(description="Sin permisos"),
        404: openapi.Response(description="Compra no encontrada")
    },
    tags=purchases_crud()
)
@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def purchase_detail(request, purchase_id):
    """
    Obtiene, actualiza o elimina una compra específica.

    GET: Obtiene detalles de la compra
    PUT: Actualiza la compra completa
    DELETE: Elimina la compra (solo el propietario o superusuario)
    """
    try:
        user = request.user

        # Usar el servicio para validar permisos y obtener la compra
        result = get_single_purchase(user.pk, int(purchase_id))

        if not result.get("success", False):
            return Response(result, status=status.HTTP_403_FORBIDDEN if result.get("data", {}).get("error_type") == "access_denied" else status.HTTP_404_NOT_FOUND)

        purchase = Purchase.objects.get(pk=purchase_id)

        if request.method == 'GET':
            # Devolver la respuesta completa del servicio que ya incluye validación
            return Response(result, status=status.HTTP_200_OK)

        elif request.method == 'PUT':
            serializer = PurchaseSerializer(
                purchase, data=request.data, partial=False)

            if serializer.is_valid():
                serializer.save()
                return Response({
                    "success": True,
                    "message": "Purchase updated successfully",
                    "data": serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "message": "Invalid data",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            purchase.delete()
            return Response({
                "success": True,
                "message": "Purchase deleted successfully"
            }, status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(f"Unexpected error in purchase detail: {str(e)}")
        return Response({
            "success": False,
            "message": "An unexpected error occurred"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
