from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import datetime, date
import logging
from .models import Report
from .services import (
    product_rotation_by_location,
    products_movements_input_vs_output,
    sales_summary,
    most_sold_products,
    payment_methods_analysis,
    overdue_installments
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_product_rotation_report(self, report_id, parameters):
    """Genera reporte de rotación de productos de forma asíncrona."""
    try:
        report = Report.objects.get(id=report_id)
        report.status = Report.Status.PROCESSING
        report.save()

        logger.info(
            f"Generando reporte de rotación de productos (ID: {report_id})")

        from_date = datetime.fromisoformat(parameters['from_date']).date()
        to_date = datetime.fromisoformat(parameters['to_date']).date()

        result = product_rotation_by_location(
            location_id=parameters['location_id'],
            graphic=parameters.get('graphic', True),
            from_date=from_date,
            to_date=to_date,
            download_graphic=parameters.get('download_graphic', False),
            excel=parameters.get('excel', False),
            language_graphic=parameters.get('language_graphic', 'es')
        )

        if hasattr(result, 'content'):
            filename = f"product_rotation_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            # HttpResponse en Django usa un diccionario interno _headers o se puede acceder con []
            content_type = ''
            try:
                if hasattr(result, '_headers') and 'content-type' in result._headers:
                    # (header_name, header_value)
                    content_type = result._headers['content-type'][1]
                elif hasattr(result, '__getitem__'):
                    content_type = result.get('Content-Type', '')
            except (KeyError, AttributeError, TypeError):
                content_type = ''

            if 'zip' in content_type.lower():
                filename += '.zip'
            elif 'png' in content_type.lower() or 'image' in content_type.lower():
                filename += '.png'
            elif 'excel' in content_type.lower() or 'spreadsheet' in content_type.lower():
                filename += '.xlsx'
            else:
                # Si no se puede detectar, usar .bin en lugar de asumir .xlsx
                filename += '.bin'

            report.file.save(filename, ContentFile(result.content), save=False)
        elif isinstance(result, dict):
            logger.info(
                f"Reporte {report_id} completado sin archivo (respuesta JSON)")

        report.status = Report.Status.COMPLETED
        report.completed_at = timezone.now()
        report.save()

        logger.info(
            f"Reporte de rotación de productos completado (ID: {report_id})")

        return {
            'report_id': report_id,
            'status': 'completed',
            'file_url': report.file.url if report.file else None
        }

    except Exception as exc:
        logger.error(
            f"Error generando reporte {report_id}: {str(exc)}", exc_info=True)

        try:
            report = Report.objects.get(id=report_id)
            report.status = Report.Status.FAILED
            report.error_message = str(exc)
            report.completed_at = timezone.now()
            report.save()
        except Exception as e:
            logger.error(f"Error updating report status: {str(e)}")

        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_movements_input_output_report(self, report_id, parameters):
    """Genera reporte de movimientos entrada/salida de forma asíncrona."""
    try:
        report = Report.objects.get(id=report_id)
        report.status = Report.Status.PROCESSING
        report.save()

        logger.info(f"Generando reporte de movimientos (ID: {report_id})")

        from_date = datetime.fromisoformat(parameters['from_date']).date()
        to_date = datetime.fromisoformat(parameters['to_date']).date()

        result = products_movements_input_vs_output(
            from_date=from_date,
            to_date=to_date,
            download_graphic=parameters.get('download_graphic', False),
            excel=parameters.get('excel', False),
            graphic=parameters.get('graphic', True),
            type_graphic=parameters.get('type_graphic', 'pie'),
            language_graphic=parameters.get('language_graphic', 'es')
        )

        if hasattr(result, 'content'):
            filename = f"movements_report_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content_type = ''
            try:
                if hasattr(result, '_headers') and 'content-type' in result._headers:
                    content_type = result._headers['content-type'][1]
                elif hasattr(result, '__getitem__'):
                    content_type = result.get('Content-Type', '')
            except (KeyError, AttributeError, TypeError):
                content_type = ''

            if 'zip' in content_type.lower():
                filename += '.zip'
            elif 'png' in content_type.lower() or 'image' in content_type.lower():
                filename += '.png'
            elif 'excel' in content_type.lower() or 'spreadsheet' in content_type.lower():
                filename += '.xlsx'
            else:
                filename += '.bin'

            report.file.save(filename, ContentFile(result.content), save=False)
        elif isinstance(result, dict):
            logger.info(
                f"Reporte {report_id} completado sin archivo (respuesta JSON)")

        report.status = Report.Status.COMPLETED
        report.completed_at = timezone.now()
        report.save()

        logger.info(f"Reporte de movimientos completado (ID: {report_id})")

        return {
            'report_id': report_id,
            'status': 'completed',
            'file_url': report.file.url if report.file else None
        }

    except Exception as exc:
        logger.error(
            f"Error generando reporte {report_id}: {str(exc)}", exc_info=True)

        try:
            report = Report.objects.get(id=report_id)
            report.status = Report.Status.FAILED
            report.error_message = str(exc)
            report.completed_at = timezone.now()
            report.save()
        except Exception as e:
            logger.error(f"Error updating report status: {str(e)}")

        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_sales_summary_report(self, report_id, parameters):
    """Genera reporte de resumen de ventas de forma asíncrona."""
    try:
        report = Report.objects.get(id=report_id)
        report.status = Report.Status.PROCESSING
        report.save()

        logger.info(
            f"Generando reporte de resumen de ventas (ID: {report_id})")

        from_date = datetime.fromisoformat(parameters['from_date']).date()
        to_date = datetime.fromisoformat(parameters['to_date']).date()

        result = sales_summary(
            from_date=from_date,
            to_date=to_date,
            month_compare=parameters.get('month_compare', 2),
            language_graphic=parameters.get('language_graphic', 'es')
        )

        if hasattr(result, 'content'):
            filename = f"sales_summary_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            report.file.save(filename, ContentFile(result.content), save=False)

        report.status = Report.Status.COMPLETED
        report.completed_at = timezone.now()
        report.save()

        logger.info(
            f"Reporte de resumen de ventas completado (ID: {report_id})")

        return {
            'report_id': report_id,
            'status': 'completed',
            'file_url': report.file.url if report.file else None
        }

    except Exception as exc:
        logger.error(
            f"Error generando reporte {report_id}: {str(exc)}", exc_info=True)

        try:
            report = Report.objects.get(id=report_id)
            report.status = Report.Status.FAILED
            report.error_message = str(exc)
            report.completed_at = timezone.now()
            report.save()
        except Exception as e:
            logger.error(f"Error updating report status: {str(e)}")

        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_top_products_report(self, report_id, parameters):
    """Genera reporte de productos más vendidos de forma asíncrona."""
    try:
        report = Report.objects.get(id=report_id)
        report.status = Report.Status.PROCESSING
        report.save()

        logger.info(
            f"Generando reporte de productos más vendidos (ID: {report_id})")

        from_date = datetime.fromisoformat(parameters['from_date']).date()
        to_date = datetime.fromisoformat(parameters['to_date']).date()

        result = most_sold_products(
            from_date=from_date,
            to_date=to_date,
            limit=parameters.get('limit', 10),
            excel=parameters.get('excel', False),
            graphic=parameters.get('graphic', True),
            download_graphic=parameters.get('download_graphic', False),
            language_graphic=parameters.get('language_graphic', 'es')
        )

        if hasattr(result, 'content'):
            filename = f"top_products_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content_type = ''
            try:
                if hasattr(result, '_headers') and 'content-type' in result._headers:
                    content_type = result._headers['content-type'][1]
                elif hasattr(result, '__getitem__'):
                    content_type = result.get('Content-Type', '')
            except (KeyError, AttributeError, TypeError):
                content_type = ''

            if 'zip' in content_type.lower():
                filename += '.zip'
            elif 'png' in content_type.lower() or 'image' in content_type.lower():
                filename += '.png'
            elif 'excel' in content_type.lower() or 'spreadsheet' in content_type.lower():
                filename += '.xlsx'
            else:
                filename += '.bin'

            report.file.save(filename, ContentFile(result.content), save=False)
        elif isinstance(result, dict):
            logger.info(
                f"Reporte {report_id} completado con datos JSON (sin archivo)")

        report.status = Report.Status.COMPLETED
        report.completed_at = timezone.now()
        report.save()

        logger.info(
            f"Reporte de productos más vendidos completado (ID: {report_id})")

        return {
            'report_id': report_id,
            'status': 'completed',
            'file_url': report.file.url if report.file else None
        }

    except Exception as exc:
        logger.error(
            f"Error generando reporte {report_id}: {str(exc)}", exc_info=True)

        try:
            report = Report.objects.get(id=report_id)
            report.status = Report.Status.FAILED
            report.error_message = str(exc)
            report.completed_at = timezone.now()
            report.save()
        except Exception as e:
            logger.error(f"Error updating report status: {str(e)}")

        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_payment_methods_report(self, report_id, parameters):
    """Genera reporte de métodos de pago de forma asíncrona."""
    try:
        report = Report.objects.get(id=report_id)
        report.status = Report.Status.PROCESSING
        report.save()

        logger.info(f"Generando reporte de métodos de pago (ID: {report_id})")

        from_date = datetime.fromisoformat(parameters['from_date']).date()
        to_date = datetime.fromisoformat(parameters['to_date']).date()

        result = payment_methods_analysis(
            from_date=from_date,
            to_date=to_date,
            excel=parameters.get('excel', False),
            download_graphic=parameters.get('download_graphic', False),
            language_graphic=parameters.get('language_graphic', 'es')
        )

        if hasattr(result, 'content'):
            filename = f"payment_methods_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content_type = ''
            try:
                if hasattr(result, '_headers') and 'content-type' in result._headers:
                    content_type = result._headers['content-type'][1]
                elif hasattr(result, '__getitem__'):
                    content_type = result.get('Content-Type', '')
            except (KeyError, AttributeError, TypeError):
                content_type = ''

            if 'zip' in content_type.lower():
                filename += '.zip'
            elif 'png' in content_type.lower() or 'image' in content_type.lower():
                filename += '.png'
            elif 'excel' in content_type.lower() or 'spreadsheet' in content_type.lower():
                filename += '.xlsx'
            else:
                filename += '.bin'

            report.file.save(filename, ContentFile(result.content), save=False)
        elif isinstance(result, dict):
            logger.info(
                f"Reporte {report_id} completado sin archivo (respuesta JSON)")

        report.status = Report.Status.COMPLETED
        report.completed_at = timezone.now()
        report.save()

        logger.info(f"Reporte de métodos de pago completado (ID: {report_id})")

        return {
            'report_id': report_id,
            'status': 'completed',
            'file_url': report.file.url if report.file else None
        }

    except Exception as exc:
        logger.error(
            f"Error generando reporte {report_id}: {str(exc)}", exc_info=True)

        try:
            report = Report.objects.get(id=report_id)
            report.status = Report.Status.FAILED
            report.error_message = str(exc)
            report.completed_at = timezone.now()
            report.save()
        except Exception as e:
            logger.error(f"Error updating report status: {str(e)}")

        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_overdue_installments_report(self, report_id, parameters):
    """Genera reporte de cuotas vencidas de forma asíncrona."""
    try:
        report = Report.objects.get(id=report_id)
        report.status = Report.Status.PROCESSING
        report.save()

        logger.info(f"Generando reporte de cuotas vencidas (ID: {report_id})")

        from_date = datetime.fromisoformat(parameters['from_date']).date()
        to_date = datetime.fromisoformat(parameters['to_date']).date()

        result = overdue_installments(
            from_date=from_date,
            to_date=to_date,
            language_graphic=parameters.get('language_graphic', 'es'),
            download_graphic=parameters.get('download_graphic', False),
            output_format='excel',
            excel=parameters.get('excel', False),
            graphic=parameters.get('graphic', True)
        )

        if hasattr(result, 'content'):
            filename = f"overdue_installments_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content_type = ''
            try:
                if hasattr(result, '_headers') and 'content-type' in result._headers:
                    content_type = result._headers['content-type'][1]
                elif hasattr(result, '__getitem__'):
                    content_type = result.get('Content-Type', '')
            except (KeyError, AttributeError, TypeError):
                content_type = ''

            if 'zip' in content_type.lower():
                filename += '.zip'
            elif 'png' in content_type.lower() or 'image' in content_type.lower():
                filename += '.png'
            elif 'excel' in content_type.lower() or 'spreadsheet' in content_type.lower():
                filename += '.xlsx'
            else:
                filename += '.bin'

            report.file.save(filename, ContentFile(result.content), save=False)
        elif isinstance(result, dict):
            logger.info(
                f"Reporte {report_id} completado sin archivo (respuesta JSON)")

        report.status = Report.Status.COMPLETED
        report.completed_at = timezone.now()
        report.save()

        logger.info(f"Reporte de cuotas vencidas completado (ID: {report_id})")

        return {
            'report_id': report_id,
            'status': 'completed',
            'file_url': report.file.url if report.file else None
        }

    except Exception as exc:
        logger.error(
            f"Error generando reporte {report_id}: {str(exc)}", exc_info=True)

        try:
            report = Report.objects.get(id=report_id)
            report.status = Report.Status.FAILED
            report.error_message = str(exc)
            report.completed_at = timezone.now()
            report.save()
        except Exception as e:
            logger.error(f"Error updating report status: {str(e)}")

        raise self.retry(exc=exc, countdown=60)
