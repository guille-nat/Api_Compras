from datetime import datetime
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import logging
from api.view_tags import promotions_public, promotions_admin
from rest_framework.pagination import PageNumberPagination
from .serializers import PromotionWithAllRelationsSerializer, PromotionRuleSerializer, PromotionCreateSerializer
from .models import Promotion
from . import services
from datetime import datetime
from api.response_helpers import success_response, server_error_response, validation_error_response

logger = logging.getLogger(__name__)


@swagger_auto_schema(
    method='get',
    operation_summary="Listar promociones activas",
    operation_description="Obtiene todas las promociones activas en el sistema con sus reglas y relaciones.",
    responses={
        200: PromotionWithAllRelationsSerializer(many=True),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_public()
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@extend_schema(responses={200: PromotionWithAllRelationsSerializer(many=True)}, tags=promotions_public())
def list_active_promotions(request):
    try:
        now = timezone.now()

        queryset = Promotion.objects.filter(
            active=True,
            promotionrule__start_at__lte=now,
            promotionrule__end_at__gte=now
        ).distinct().prefetch_related(
            'promotionrule',
            'promotionscopecategory__category',
            'promotionscopeproduct__product',
            'promotionscopelocation__location'
        )

        # Configurar paginación estándar
        paginator = PageNumberPagination()
        paginator.page_size = 10  # Tamaño de página para promociones

        # Aplicar paginación estándar al queryset con prefetch optimizado
        page_data = paginator.paginate_queryset(queryset, request)
        serializer = PromotionWithAllRelationsSerializer(page_data, many=True)
        return paginator.get_paginated_response(serializer.data)
    except ValueError as e:
        logger.error(f"Validation error list promotions active: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Unexpected error list promotions active: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_summary="Productos con promociones activas",
    operation_description="Lista productos que tienen promociones activas aplicadas.",
    responses={
        200: openapi.Response(
            description="Lista de productos con promociones",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                }
            )
        ),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_public()
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@extend_schema(parameters=[OpenApiParameter('product_id', OpenApiTypes.INT, OpenApiParameter.QUERY, description='ID del producto', required=True)], tags=promotions_public())
def list_promotions_active_products(request):
    try:
        product_id = request.query_params.get('product_id')
        product_id = int(product_id)

        # Obtener promociones desde el servicio
        promotions_data = services.get_active_promotions_product(product_id)

        # Configurar paginación estándar para las promociones
        paginator = PageNumberPagination()
        paginator.page_size = 10  # Tamaño de página para promociones de productos

        # Aplicar paginación estándar a la lista de promociones
        page_data = paginator.paginate_queryset(promotions_data, request)

        # Los datos ya vienen serializados del servicio como diccionarios
        return paginator.get_paginated_response(page_data)
    except ValueError as e:
        logger.error(
            f"Validation error list promotions active products: {str(e)}")
        return validation_error_response("Error validation data")
    except Exception as e:
        logger.error(f"Unexpected error crea: {str(e)}")
        return server_error_response("Error internal server")


@swagger_auto_schema(
    method='get',
    operation_summary="Categorías con promociones activas",
    operation_description="Lista categorías que tienen promociones activas aplicadas.",
    responses={
        200: openapi.Response(description="Lista de categorías con promociones"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_public()
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=promotions_public())
def list_categories_with_active_promotions(request):
    try:
        # Obtener categorías con promociones desde el servicio
        categories_data = services.get_categories_with_active_promotions()

        # Configurar paginación estándar para las categorías
        paginator = PageNumberPagination()
        paginator.page_size = 10  # Tamaño de página para categorías con promociones

        # Aplicar paginación estándar a la lista de categorías
        page_data = paginator.paginate_queryset(categories_data, request)

        # Los datos ya vienen serializados del servicio como diccionarios
        return paginator.get_paginated_response(page_data)
    except ValueError as e:
        logger.error(
            f"Validation error list categories with active promotions: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(
            f"Unexpected error list categories with active promotions: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_summary="Crear promoción",
    operation_description="Crea una nueva promoción en el sistema. Solo para administradores.",
    request_body=PromotionCreateSerializer,
    responses={
        201: PromotionCreateSerializer,
        400: openapi.Response(description="Datos inválidos"),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
@extend_schema(request=PromotionCreateSerializer, responses={201: PromotionCreateSerializer}, tags=promotions_admin())
def create_promotion(request):
    try:
        data = request.data
        response_data = services.create_promotion_and_rule(
            data, user_id=request.user.id)

        return Response(
            {"success": True,
             "message": "Promotion created successfully",
             "data": response_data},
            status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        logger.error(f"Validation error creating promotion: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Unexpected error creating promotion: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_summary="Crear regla de promoción",
    operation_description="Crea una nueva regla para una promoción existente.",
    request_body=PromotionRuleSerializer,
    responses={
        201: PromotionRuleSerializer,
        400: openapi.Response(description="Datos inválidos"),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_rule(request):
    try:
        data = request.data
        response_data = services.create_rule(promotion_id=data.get('promotion_id'), type=data.get('type'),
                                             value=data.get('value'), priority=data.get('priority'),
                                             start_date=data.get('start_date'), end_date=data.get('end_date'),
                                             acumulable=data.get('acumulable'), user_id=request.user.id)

        return Response(
            {"success": True,
             "message": "Rule created successfully",
             "data": response_data},
            status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        logger.error(f"Validation error creating rule: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Unexpected error creating rule: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_summary="Asociar producto a promoción",
    operation_description="Crea una asociación entre un producto y una promoción.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'promotion_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'product_id': openapi.Schema(type=openapi.TYPE_INTEGER)
        },
        required=['promotion_id', 'product_id']
    ),
    responses={
        201: openapi.Response(description="Producto asociado exitosamente"),
        400: openapi.Response(description="Datos inválidos"),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_promotion_product(request):
    try:
        data = request.data
        response_data = services.create_promotion_product(
            promotion_id=data.get('promotion_id'),
            product_id=data.get('product_id'),
            user_id=request.user.id
        )

        return Response(
            {"success": True,
             "message": "Promotion-Product scope created successfully",
             "data": response_data},
            status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        logger.error(
            f"Validation error creating promotion-product scope: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(
            f"Unexpected error creating promotion-product scope: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_summary="Asociar categoría a promoción",
    operation_description="Crea una asociación entre una categoría y una promoción.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'promotion_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'category_id': openapi.Schema(type=openapi.TYPE_INTEGER)
        },
        required=['promotion_id', 'category_id']
    ),
    responses={
        201: openapi.Response(description="Categoría asociada exitosamente"),
        400: openapi.Response(description="Datos inválidos"),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_promotion_category(request):
    try:
        data = request.data
        response_data = services.create_promotion_category(
            promotion_id=data.get('promotion_id'),
            category_id=data.get('category_id'),
            user_id=request.user.id
        )

        return Response(
            {"success": True,
             "message": "Promotion-Category scopes created successfully",
             "data": response_data},
            status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        logger.error(
            f"Validation error creating promotion-category scopes: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(
            f"Unexpected error creating promotion-category scopes: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_summary="Asociar ubicación a promoción",
    operation_description="Crea una asociación entre una ubicación y una promoción.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'promotion_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'location_id': openapi.Schema(type=openapi.TYPE_INTEGER)
        },
        required=['promotion_id', 'location_id']
    ),
    responses={
        201: openapi.Response(description="Ubicación asociada exitosamente"),
        400: openapi.Response(description="Datos inválidos"),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_promotion_location(request):
    try:
        data = request.data
        response_data = services.create_promotion_location(
            promotion_id=data.get('promotion_id'),
            location_id=data.get('location_id'),
            user_id=request.user.id
        )

        return Response(
            {"success": True,
             "message": "Promotion-Location scope created successfully",
             "data": response_data},
            status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        logger.error(
            f"Validation error creating promotion-location scope: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(
            f"Unexpected error creating promotion-location scope: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='patch',
    operation_summary="Actualizar promoción",
    operation_description="Actualiza los datos de una promoción existente.",
    request_body=PromotionCreateSerializer,
    responses={
        200: PromotionCreateSerializer,
        400: openapi.Response(description="Datos inválidos"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Promoción no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_promotion(request, promotion_id):
    try:
        data = request.data
        name = data.get('name')
        active = data.get('active')

        response_data = services.update_promotion(
            promotion_id=promotion_id,
            name=name,
            active=active,
            user_id=request.user.id
        )

        return Response(
            {"success": response_data['success'],
             "message": response_data['message'],
             "data": response_data['data']},
            status=status.HTTP_200_OK
        )
    except ValueError as e:
        logger.error(f"Unexpected error updating promotion: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Unexpected error updating promotion: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='patch',
    operation_summary="Actualizar regla de promoción",
    operation_description="Actualiza una regla específica de promoción.",
    request_body=PromotionRuleSerializer,
    responses={
        200: PromotionRuleSerializer,
        400: openapi.Response(description="Datos inválidos"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Regla no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_rule(request, rule_id):
    try:
        data = request.data
        type = data.get('type')
        value = data.get('value')
        priority = data.get('priority')
        start_date = datetime.combine(
            data.get('start_at'), datetime.max.time())
        end_date = datetime.combine(data.get('end_at'), datetime.max.time())
        acumulable = data.get('acumulable')

        response_data = services.update_rule(
            rule_id=rule_id,
            type=type,
            value=value,
            priority=priority,
            start_date=start_date,
            end_date=end_date,
            acumulable=acumulable,
            user_id=request.user.id
        )

        return Response(
            {"success": response_data['success'],
             "message": response_data['message'],
             "data": response_data['data']},
            status=status.HTTP_200_OK
        )
    except ValueError as e:
        logger.error(f"Unexpected error updating rule: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Unexpected error updating rule: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='delete',
    operation_summary="Eliminar promoción",
    operation_description="Elimina una promoción y todas sus relaciones asociadas.",
    responses={
        204: openapi.Response(description="Promoción eliminada exitosamente"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Promoción no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_promotion(request, promotion_id):
    try:
        response_data = services.delete_promotion(
            promotion_id=promotion_id,
            user_id=request.user.id
        )
        logger.info(
            f"Promotion with ID {promotion_id} deleted by user {request.user.id}")
        return Response(
            {"success": response_data['success'],
             "message": response_data['message'],
             "data": response_data['data']},
            status=status.HTTP_200_OK
        )
    except ValueError as e:
        logger.error(f"Unexpected error deleting promotion: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error deleting promotion: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='delete',
    operation_summary="Eliminar regla de promoción",
    operation_description="Elimina una regla específica de promoción.",
    responses={
        204: openapi.Response(description="Regla eliminada exitosamente"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Regla no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_rule(request, rule_id):
    try:
        response_data = services.delete_rule(
            rule_id=rule_id,
            user_id=request.user.id
        )
        logger.info(
            f"Rule with ID {rule_id} deleted by user {request.user.id}")
        return Response(
            {"success": response_data['success'],
             "message": response_data['message'],
             "data": response_data['data']},
            status=status.HTTP_200_OK
        )
    except ValueError as e:
        logger.error(f"Unexpected error deleting rule: {str(e)}")
        return Response({
            "success": False,
            "message": "Error validation data",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error deleting rule: {str(e)}")
        return Response({
            "success": False,
            "message": "Error internal server",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='delete',
    operation_summary="Desasociar categoría de promoción",
    operation_description="Elimina la asociación entre una categoría y una promoción.",
    responses={
        204: openapi.Response(description="Asociación eliminada exitosamente"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Asociación no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_promotion_category(request, promotion_id, category_id):
    try:
        response_data = services.delete_promotion_category(
            promotion_id=promotion_id,
            category_id=category_id,
            user_id=request.user.id
        )

        logger.info(
            f"Promotion-Category association {promotion_id}-{category_id} deleted by user {request.user.id}")

        return Response(
            {
                "success": response_data['success'],
                "message": response_data['message'],
                "data": response_data['data']
            },
            status=status.HTTP_200_OK
        )
    except ValueError as e:
        logger.error(f"Validation error deleting promotion-category: {str(e)}")
        return Response({
            "success": False,
            "message": "Error de validación en los datos",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error deleting promotion-category: {str(e)}")
        return Response({
            "success": False,
            "message": "Error interno del servidor",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='delete',
    operation_summary="Desasociar producto de promoción",
    operation_description="Elimina la asociación entre un producto y una promoción.",
    responses={
        204: openapi.Response(description="Asociación eliminada exitosamente"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Asociación no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_promotion_product(request, promotion_id, product_id):
    try:
        response_data = services.delete_promotion_product(
            promotion_id=promotion_id,
            product_id=product_id,
            user_id=request.user.id
        )

        logger.info(
            f"Promotion-Product association {promotion_id}-{product_id} deleted by user {request.user.id}")

        return Response(
            {
                "success": response_data['success'],
                "message": response_data['message'],
                "data": response_data['data']
            },
            status=status.HTTP_200_OK
        )
    except ValueError as e:
        logger.error(f"Validation error deleting promotion-product: {str(e)}")
        return Response({
            "success": False,
            "message": "Error de validación en los datos",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error deleting promotion-product: {str(e)}")
        return Response({
            "success": False,
            "message": "Error interno del servidor",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='delete',
    operation_summary="Desasociar ubicación de promoción",
    operation_description="Elimina la asociación entre una ubicación y una promoción.",
    responses={
        204: openapi.Response(description="Asociación eliminada exitosamente"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Asociación no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=promotions_admin()
)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_promotion_location(request, promotion_id, location_id):
    try:
        response_data = services.delete_promotion_location(
            promotion_id=promotion_id,
            location_id=location_id,
            user_id=request.user.id
        )

        logger.info(
            f"Promotion-Location association {promotion_id}-{location_id} deleted by user {request.user.id}")

        return Response(
            {
                "success": response_data['success'],
                "message": response_data['message'],
                "data": response_data['data']
            },
            status=status.HTTP_200_OK
        )
    except ValueError as e:
        logger.error(f"Validation error deleting promotion-location: {str(e)}")
        return Response({
            "success": False,
            "message": "Error de validación en los datos",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error deleting promotion-location: {str(e)}")
        return Response({
            "success": False,
            "message": "Error interno del servidor",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
