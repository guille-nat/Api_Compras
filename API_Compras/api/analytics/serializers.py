from rest_framework import serializers
from .models import Report


class ReportCreateSerializer(serializers.Serializer):
    """Serializer base para la creación de reportes asincrónicos."""

    from_date = serializers.DateField(
        required=True,
        help_text="Fecha inicial del período (YYYY-MM-DD)"
    )
    to_date = serializers.DateField(
        required=False,
        help_text="Fecha final del período (YYYY-MM-DD). Por defecto: hoy"
    )
    excel = serializers.BooleanField(
        default=False,
        help_text="Generar archivo Excel"
    )
    graphic = serializers.BooleanField(
        default=True,
        help_text="Incluir gráfico"
    )
    download_graphic = serializers.BooleanField(
        default=False,
        help_text="Descargar gráfico como PNG en ZIP"
    )
    language_graphic = serializers.ChoiceField(
        choices=['es', 'en'],
        default='es',
        help_text="Idioma de los gráficos"
    )

    def validate(self, attrs):
        from_date = attrs.get('from_date')
        to_date = attrs.get('to_date')

        if to_date and from_date > to_date:
            raise serializers.ValidationError(
                "Start date cannot be after end date"
            )

        return attrs


class ProductRotationReportSerializer(ReportCreateSerializer):
    """Serializer para reportes de rotación de productos."""

    location_id = serializers.IntegerField(
        required=True,
        help_text="ID de la ubicación/almacén a analizar"
    )


class MovementsReportSerializer(ReportCreateSerializer):
    """Serializer para reportes de movimientos entrada/salida."""

    type_graphic = serializers.ChoiceField(
        choices=['pie', 'bar'],
        default='pie',
        help_text="Tipo de gráfico a generar"
    )


class SalesSummaryReportSerializer(ReportCreateSerializer):
    """Serializer para reportes de resumen de ventas."""

    month_compare = serializers.IntegerField(
        default=2,
        min_value=1,
        max_value=12,
        help_text="Número de meses anteriores a comparar"
    )


class TopProductsReportSerializer(ReportCreateSerializer):
    """Serializer para reportes de productos más vendidos."""

    limit = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=100,
        help_text="Número máximo de productos a mostrar"
    )


class PaymentMethodsReportSerializer(ReportCreateSerializer):
    """Serializer para reportes de métodos de pago."""
    pass


class OverdueInstallmentsReportSerializer(ReportCreateSerializer):
    """Serializer para reportes de cuotas vencidas."""

    output_format = serializers.ChoiceField(
        choices=['json', 'excel'],
        default='json',
        help_text="Formato de salida del reporte"
    )


class ReportStatusSerializer(serializers.ModelSerializer):
    """Serializer para consultar el estado de un reporte."""

    report_type_display = serializers.CharField(
        source='get_report_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id',
            'task_id',
            'report_type',
            'report_type_display',
            'status',
            'status_display',
            'file_url',
            'parameters',
            'error_message',
            'created_at',
            'completed_at'
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class ReportListSerializer(serializers.ModelSerializer):
    """Serializer para listar reportes de forma resumida."""

    report_type_display = serializers.CharField(
        source='get_report_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = Report
        fields = [
            'id',
            'task_id',
            'report_type',
            'report_type_display',
            'status',
            'status_display',
            'created_at',
            'completed_at'
        ]
        read_only_fields = fields
