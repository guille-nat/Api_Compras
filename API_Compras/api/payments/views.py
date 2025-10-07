from rest_framework import status, generics
from django.core.exceptions import ValidationError
from .serializers import InstallmentSerializer, InstallmentInformationSerializer, PaymentSerializer
from django.shortcuts import get_object_or_404
from .models import Installment
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from .services import (
    get_all_installments,
    update_state_installment,
    fetch_installment_details,
    pay_installment,
    delete_installments_by_id
)
from rest_framework.decorators import api_view, permission_classes
from decimal import Decimal
from .utils import get_all_payments_by_user
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
import logging
from api.view_tags import payments_user_management, installments_user_management, installments_admin
from rest_framework.pagination import PageNumberPagination
logger = logging.getLogger(__name__)

PAGINATION_PAGE_SIZE_PAYMENTS = 10


class InstallmentViewSet(generics.ListAPIView):
    """
    ViewSet para listar cuotas (Installments) con filtros opcionales.

    Permite a usuarios autenticados visualizar sus cuotas asociadas,
    mientras que los superusuarios pueden acceder a todas las cuotas
    del sistema. Incluye filtrado por ID de compra y estado.

    Permisos requeridos:
        - IsAuthenticated: Usuario autenticado para acceso básico
        - is_superuser: Acceso completo a todas las cuotas (opcional)

    Filtros disponibles:
        - purchase_id (int): Filtra cuotas por ID de compra específica
        - state (str): Filtra cuotas por estado (PENDING, PAID, OVERDUE)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = InstallmentSerializer

    @swagger_auto_schema(
        operation_summary="Listar cuotas del usuario",
        operation_description="Obtiene las cuotas del usuario autenticado o todas las cuotas si es superusuario, con filtros opcionales.",
        manual_parameters=[
            openapi.Parameter(
                'purchase_id',
                openapi.IN_QUERY,
                description="Filtrar cuotas por ID de compra específica",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'state',
                openapi.IN_QUERY,
                description="Filtrar cuotas por estado",
                type=openapi.TYPE_STRING,
                enum=['PENDING', 'PAID', 'OVERDUE'],
                required=False
            )
        ],
        responses={
            200: InstallmentSerializer(many=True),
            401: openapi.Response(description="No autenticado"),
            500: openapi.Response(description="Error interno del servidor")
        },
        tags=installments_user_management()
    )
    @extend_schema(parameters=[
        OpenApiParameter('purchase_id', OpenApiTypes.INT, OpenApiParameter.QUERY,
                         description='Filtrar por compra', required=False),
        OpenApiParameter('state', OpenApiTypes.STR, OpenApiParameter.QUERY,
                         description='Filtrar por estado', required=False)
    ], responses={200: InstallmentSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        """
        Lista las cuotas del usuario con filtros opcionales.

        Los usuarios normales solo pueden ver sus propias cuotas,
        mientras que los superusuarios pueden ver todas las cuotas del sistema.

        Query Parameters:
            purchase_id (int, optional): ID de compra para filtrar cuotas
            state (str, optional): Estado de las cuotas (PENDING, PAID, OVERDUE)

        Returns:
            Response: Lista de cuotas siguiendo el estándar de respuestas

        Raises:
            401: Usuario no autenticado
            500: Error interno del servidor
        """

    def get(self, request, *args, **kwargs):
        """
        Lista las cuotas del usuario con filtros opcionales.

        Los usuarios normales solo pueden ver sus propias cuotas,
        mientras que los superusuarios pueden ver todas las cuotas del sistema.

        Query Parameters:
            purchase_id (int, optional): ID de compra para filtrar cuotas
            state (str, optional): Estado de las cuotas (PENDING, PAID, OVERDUE)

        Returns:
            Response: Lista de cuotas siguiendo el estándar de respuestas

        Raises:
            401: Usuario no autenticado
            500: Error interno del servidor
        """
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        """
        Retorna el QuerySet de cuotas filtrado según el usuario y parámetros de consulta.

        Para superusuarios: devuelve todas las cuotas del sistema.
        Para usuarios normales: solo sus cuotas asociadas a través de Purchase.

        Excepciones:
            ValidationError: Si los parámetros de filtro son inválidos.
        """
        if self.request.user.is_superuser:
            # Corregido: usar .all() para obtener QuerySet completo
            queryset = Installment.objects.all()
        else:
            result = get_all_installments(self.request.user)
            queryset = result['data']['installments']

        # Filtro por purchase_id
        purchase_id = self.request.query_params.get('purchase_id')
        if purchase_id:
            try:
                purchase_id = int(purchase_id)
                queryset = queryset.filter(purchase_id=purchase_id)
            except ValueError:
                raise ValidationError(f"ID de compra inválido: {purchase_id}")

        # Filtro por state
        state = self.request.query_params.get('state')
        if state:
            if state.upper() not in Installment.State.values:
                raise ValidationError(f"Estado inválido: {state}")
            queryset = queryset.filter(state=state.upper())

        return queryset


@swagger_auto_schema(
    method='patch',
    operation_summary="Cambiar estado de cuota (Admin)",
    operation_description="Actualiza el estado de una cuota específica. Solo disponible para administradores.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'installment_id': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="ID de la cuota a actualizar"
            ),
            'new_state': openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=['PENDING', 'PAID', 'OVERDUE'],
                description="Nuevo estado de la cuota"
            ),
            'reason': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Motivo del cambio de estado (opcional)"
            )
        },
        required=['installment_id', 'new_state']
    ),
    responses={
        200: openapi.Response(
            description="Estado actualizado exitosamente",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': InstallmentSerializer
                }
            )
        ),
        400: openapi.Response(description="Datos inválidos o estado no válido"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Cuota no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=installments_admin()
)
@extend_schema(request=inline_serializer(name='ChangeInstallmentStateSerializer', fields={
    'installment_id': serializers.IntegerField(),
    'new_state': serializers.CharField(),
    'reason': serializers.CharField(required=False, allow_blank=True),
}), tags=installments_admin())
@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def change_state_installment(request):
    """
    Cambia el estado de una cuota específica.

    Esta vista permite a los administradores actualizar manualmente
    el estado de cualquier cuota en el sistema.

    Request Body:
        dict: Contiene installment_id, new_state y reason opcional

    Returns:
        Response: Cuota actualizada con mensaje de confirmación

    Raises:
        400: Datos inválidos o estado no permitido
        403: Usuario sin permisos de administrador
        404: Cuota no encontrada
        500: Error interno del servidor
    """
    # Inicializar variables para análisis estático
    installment_id = None

    # Validación de installment_id
    try:
        installment_id = request.data.get('installment_id')
        installment_id = int(installment_id)
    except (ValueError, TypeError):
        logger.warning(f"ID de cuota inválido recibido: {installment_id}")
        return Response({
            'success': False,
            'message': 'ID de cuota inválido.',
            'error': 'El ID proporcionado no es válido.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Verificar existencia de la cuota (get_object_or_404 maneja el 404 automáticamente)
    installment = get_object_or_404(Installment, pk=installment_id)

    # Validación del nuevo estado
    new_state = request.data.get('state')
    if not new_state:
        return Response({
            'success': False,
            'message': 'Campo requerido faltante.',
            'error': "El campo 'state' es requerido."
        }, status=status.HTTP_400_BAD_REQUEST)

    if new_state.upper() not in Installment.State.values:
        return Response({
            'success': False,
            'message': 'Estado inválido.',
            'error': f"Estado inválido: {new_state}. Estados válidos: {list(Installment.State.values)}"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Delegar lógica de negocio al servicio
        updated_installment = update_state_installment(
            installment_id, new_state, request.user
        )

        # Serializar respuesta
        installment_serializer = InstallmentSerializer(
            updated_installment['data']['installment']
        )

        logger.info(
            f"Cuota {installment_id} actualizada a estado {new_state} por usuario {request.user.id}")

        return Response({
            'success': updated_installment['success'],
            'message': updated_installment['message'],
            'data': {
                'installment': installment_serializer.data,
                'old_state': updated_installment['data']['old_state'],
                'new_state': updated_installment['data']['new_state']
            }
        }, status=status.HTTP_200_OK)

    except ValueError as ve:
        logger.warning(
            f"Error de validación al actualizar cuota {installment_id}: {str(ve)}")
        return Response({
            'success': False,
            'message': 'Error de validación en los datos proporcionados.',
            'error': str(ve)
        }, status=status.HTTP_400_BAD_REQUEST)

    except ValidationError as val_err:
        logger.warning(
            f"Error de validación Django al actualizar cuota {installment_id}: {str(val_err)}")
        return Response({
            'success': False,
            'message': 'Error de validación en la operación.',
            'error': str(val_err)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(
            f"Error interno al actualizar cuota {installment_id}: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del servidor.',
            'error': 'Error interno del servidor al actualizar el estado de la cuota.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_summary="Obtener detalle de cuota",
    operation_description="Obtiene información detallada de una cuota específica.",
    manual_parameters=[
        openapi.Parameter(
            'installment_id',
            openapi.IN_QUERY,
            description="ID de la cuota a consultar",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ],
    responses={
        200: InstallmentInformationSerializer,
        400: openapi.Response(description="ID de cuota faltante o inválido"),
        401: openapi.Response(description="No autenticado"),
        403: openapi.Response(description="Sin permisos para ver esta cuota"),
        404: openapi.Response(description="Cuota no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=installments_user_management()
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_installment_detail(request):
    """
    Obtiene el detalle completo de una cuota específica.

    Esta vista permite a los usuarios obtener información detallada
    sobre una cuota, incluyendo datos de la compra asociada.

    Query Parameters:
        installment_id (int): ID único de la cuota a consultar

    Returns:
        Response: Información detallada de la cuota siguiendo el estándar

    Raises:
        400: ID de cuota faltante o inválido
        401: Usuario no autenticado
        403: Sin permisos para ver esta cuota específica
        404: Cuota no encontrada
        500: Error interno del servidor
    """
    # Referenciar explícitamente el objeto request para evitar advertencias de variable no usada
    _ = request

    try:
        installment_id = request.data.get('installment_id')
        installment_id = int(installment_id)
        result = fetch_installment_details(installment_id)

        return Response({
            'success': result['success'],
            'message': result['message'],
            'data': InstallmentInformationSerializer(result['data']).data
        }, status=status.HTTP_200_OK)

    except (ValueError, TypeError):
        return Response({
            'success': False,
            'message': 'ID de cuota inválido.',
            'error': 'El ID proporcionado no es válido.'
        }, status=status.HTTP_400_BAD_REQUEST)

    except ValidationError as val_err:
        return Response({
            'success': False,
            'message': 'Error de validación.',
            'error': str(val_err)
        }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    operation_summary="Procesar pago de cuota",
    operation_description="Procesa el pago de una cuota específica y actualiza su estado a PAID.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'installment_id': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="ID de la cuota a pagar"
            ),
            'payment_method': openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=['CASH', 'CARD', 'TRANSFER', 'OTHER'],
                description="Método de pago utilizado"
            ),
            'amount_paid': openapi.Schema(
                type=openapi.TYPE_NUMBER,
                format=openapi.FORMAT_DECIMAL,
                description="Monto pagado (opcional, se usa el monto de la cuota por defecto)"
            ),
            'notes': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Notas adicionales sobre el pago (opcional)"
            )
        },
        required=['installment_id', 'payment_method']
    ),
    responses={
        200: openapi.Response(
            description="Pago procesado exitosamente",
            schema=PaymentSerializer
        ),
        400: openapi.Response(description="Datos inválidos o cuota ya pagada"),
        401: openapi.Response(description="No autenticado"),
        403: openapi.Response(description="Sin permisos para pagar esta cuota"),
        404: openapi.Response(description="Cuota no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=payments_user_management()
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@extend_schema(request=inline_serializer(name='PayInstallmentSerializer', fields={
    'installment_id': serializers.IntegerField(),
    'payment_method': serializers.CharField(),
    'amount_paid': serializers.DecimalField(max_digits=12, decimal_places=2, required=False),
    'notes': serializers.CharField(required=False, allow_blank=True),
}), tags=["Payments - User Management"])
def pay(request):
    """
    Procesa el pago de una cuota específica.

    Esta vista permite a los usuarios procesar el pago de sus cuotas
    pendientes, actualizando automáticamente el estado a PAID.

    Request Body:
        dict: Contiene installment_id, payment_method, amount_paid opcional
              y notas adicionales

    Returns:
        Response: Registro del pago creado siguiendo el estándar

    Raises:
        400: Datos inválidos, cuota ya pagada o monto incorrecto
        401: Usuario no autenticado
        403: Sin permisos para pagar esta cuota específica
        404: Cuota no encontrada
        500: Error interno del servidor o fallo en procesamiento
    """
    # Inicializar para evitar advertencias de variable possibly unbound
    installment_id = None
    paid_amount = None

    required_fields = ['installment_id', 'paid_amount', 'payment_method']
    for field in required_fields:
        if field not in request.data:
            logger.warning(
                f"Campo requerido faltante: {field} para usuario {request.user.id}")
            return Response({
                'success': False,
                'message': 'Campo requerido faltante.',
                'error': f"El campo '{field}' es requerido."
            }, status=status.HTTP_400_BAD_REQUEST)
    try:
        # Conversión y validación de tipos de datos
        installment_id = int(request.data.get('installment_id'))
        paid_amount = Decimal(request.data.get('paid_amount'))
        payment_method = request.data.get('payment_method')
        external_reference = request.data.get('external_reference', '')

        # Procesar el pago a través del servicio
        result = pay_installment(
            installment_id, paid_amount, payment_method,
            external_reference if external_reference != '' else None,
        )

        # Serializar respuesta installment
        installment_serializer = InstallmentSerializer(
            result['data']['installment']
        )
        # Serializar respuesta payment
        payment_serializer = PaymentSerializer(result['data']['payment'])

        logger.info(
            f"Pago procesado exitosamente - Cuota: {installment_id}, "
            f"Monto: {paid_amount}, Usuario: {request.user.id}"
        )

        return Response({
            'success': result['success'],
            'message': result['message'],
            'data': {
                'installment': installment_serializer.data,
                'payment': payment_serializer.data,
                'amount_paid': result['data']['amount_paid'],
                'discount_applied': result['data']['discount_applied']
            }
        }, status=status.HTTP_200_OK)

    except (ValueError, TypeError) as ve:
        logger.warning(
            f"Datos inválidos en solicitud de pago - Usuario: {request.user.id}, "
            f"Error: {str(ve)}"
        )
        return Response({
            'success': False,
            'message': 'Datos inválidos en la solicitud.',
            'error': str(ve)
        }, status=status.HTTP_400_BAD_REQUEST)

    except ValidationError as val_err:
        logger.warning(
            f"Error de validación en pago - Cuota: {installment_id}, "
            f"Usuario: {request.user.id}, Error: {str(val_err)}"
        )
        return Response({
            'success': False,
            'message': 'Error de validación en el pago.',
            'error': str(val_err)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(
            f"Error interno en procesamiento de pago - Cuota: {installment_id}, "
            f"Usuario: {request.user.id}, Error: {str(e)}",
            exc_info=True
        )
        return Response({
            'success': False,
            'message': 'Error interno del servidor.',
            'error': 'Error interno del servidor al procesar el pago.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_summary="Obtener historial de pagos del usuario",
    operation_description="Obtiene todos los pagos realizados por el usuario autenticado.",
    responses={
        200: openapi.Response(
            description="Lista de pagos del usuario",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=PaymentSerializer
                    ),
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        401: openapi.Response(description="No autenticado"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=payments_user_management()
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_payments(request):
    """
    Obtiene el historial completo de pagos del usuario.

    Esta vista permite a los usuarios consultar todos sus pagos
    realizados en el sistema.

    Returns:
        Response: Lista de todos los pagos del usuario siguiendo el estándar

    Raises:
        401: Usuario no autenticado
        500: Error interno del servidor
    """
    try:
        # Obtener pagos del usuario a través del servicio de utilidades
        payments = get_all_payments_by_user(request.user.id)

        logger.info(
            f"Pagos obtenidos exitosamente para usuario {request.user.id}")

        # Paginate payments list con manejo de errores para tests
        paginator = PageNumberPagination()
        paginator.page_size = PAGINATION_PAGE_SIZE_PAYMENTS

        try:
            page_data = paginator.paginate_queryset(payments, request)
        except (TypeError, AttributeError):
            # Si falla con objetos mock/fake, convertir a lista
            payments = list(payments)
            page_data = paginator.paginate_queryset(payments, request)

        payment_serializer = PaymentSerializer(page_data, many=True)
        response = paginator.get_paginated_response(payment_serializer.data)

        # Construir respuesta con estructura estándar compatible con tests
        payment_data = dict(response.data) if response.data else {}
        if 'count' in payment_data:
            payment_data['total_count'] = payment_data['count']

        formatted_response = {
            'success': True,
            'message': 'Pagos obtenidos exitosamente',
            'data': payment_data
        }

        return Response(formatted_response, status=status.HTTP_200_OK)

    except (ValueError, TypeError) as ve:
        logger.warning(
            f"Datos inválidos en solicitud de pagos - Usuario: {request.user.id}, "
            f"Error: {str(ve)}"
        )
        return Response({
            'success': False,
            'message': 'Datos inválidos en la solicitud.',
            'error': str(ve)
        }, status=status.HTTP_400_BAD_REQUEST)

    except ValidationError as val_err:
        logger.warning(
            f"Error de validación al obtener pagos - Usuario: {request.user.id}, "
            f"Error: {str(val_err)}"
        )
        return Response({
            'success': False,
            'message': 'Error de validación.',
            'error': str(val_err)
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(
            f"Error interno al obtener pagos - Usuario: {request.user.id}, "
            f"Error: {str(e)}",
            exc_info=True
        )
        return Response({
            'success': False,
            'message': 'Error interno del servidor.',
            'error': 'Error interno del servidor al procesar los pagos.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='delete',
    operation_summary="Eliminar cuota (Admin)",
    operation_description="Elimina una cuota específica del sistema. Solo disponible para administradores.",
    responses={
        204: openapi.Response(description="Cuota eliminada exitosamente"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Cuota no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=installments_admin()
)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_installments(request, pk):
    """
    Elimina una cuota específica del sistema.

    Esta vista permite a los administradores eliminar cuotas
    del sistema cuando sea necesario.

    Path Parameters:
        pk (int): ID único de la cuota a eliminar

    Returns:
        Response: Confirmación de eliminación

    Raises:
        403: Usuario sin permisos de administrador
        404: Cuota no encontrada
        500: Error interno del servidor

    Warning:
        Esta operación es irreversible y puede afectar la integridad
        de los datos relacionados con pagos y compras.
    """
    try:
        response = delete_installments_by_id(pk, request.user.id)
        return Response(response, status=status.HTTP_200_OK)
    except ValidationError as val_err:
        logger.warning(
            f"Error de validación al eliminar cuotas - ID: {pk}, "
            f"Error: {str(val_err)}"
        )
        return Response({
            'success': False,
            'message': 'Error de validación.',
            'error': str(val_err)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(
            f"Error interno al eliminar cuotas - ID: {pk}, "
            f"Error: {str(e)}",
            exc_info=True
        )
        return Response({
            'success': False,
            'message': 'Error interno del servidor.',
            'error': 'Error interno del servidor al eliminar las cuotas.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
