from django.core import exceptions
from django.db import transaction, models
from api.purchases.models import Purchase
from decimal import Decimal, ROUND_HALF_UP
from .models import Installment, InstallmentAuditLog, Payment
from datetime import timedelta
from django.utils import timezone
from api.users.models import CustomUser
from .utils import get_installments_by_id, get_installments_discount, calculate_surcharge_over_installments
from typing import Optional
from dateutil.relativedelta import relativedelta
from api.utils import validate_id
from api.services import send_installment_mora_notification


@transaction.atomic
def create_installments_for_purchase(purchase_id: int) -> dict:
    """
    Genera y persiste las cuotas (Installments) asociadas a una compra existente.

    Dado el identificador de una compra válida, este método crea las cuotas
    correspondientes dividiendo el monto total (`total_amount`) de la compra
    entre la cantidad de cuotas (`total_installments_count`).
    Cada cuota se genera con estado inicial `PENDING`, sin recargos ni descuentos,
    y con fecha de vencimiento mensual a partir de la fecha de compra.

    Reglas y validaciones aplicadas:
        - La compra debe existir en la base de datos.
        - `total_installments_count` debe ser un entero positivo.
        - `total_amount` debe ser un Decimal positivo.
        - El cálculo del monto por cuota se realiza en base al total_amount,
          sin considerar recargos (>6 cuotas) ni descuentos (pronto pago),
          dado que éstos se aplican en otras etapas del flujo de negocio.
        - Las fechas de vencimiento se generan en intervalos de 30 días
          desde la fecha de la compra.

    Efectos:
        - Se insertan múltiples registros en la tabla Installment,
          uno por cada cuota.
        - El proceso se ejecuta dentro de una transacción atómica:
          si ocurre algún error, no se crean cuotas parciales.

    Parámetros:
        purchase_id (int): Identificador de la compra.

    Excepciones:
        django.core.exceptions.ValidationError:
            - Si la compra no existe.
            - Si el número de cuotas no es válido.
            - Si el monto total no es válido.

    Retorno:
        dict: Respuesta estándar con información de la operación
            - success (bool): True si la operación fue exitosa
            - message (str): Mensaje descriptivo de la operación
            - data (dict): Datos de la operación
                - purchase_id (int): ID de la compra
                - installments_created (int): Número de cuotas creadas
                - total_amount (Decimal): Monto total de la compra
    """
    validate_id(purchase_id, "Purchase")

    purchase = Purchase.objects.filter(id=purchase_id).first()

    if not purchase:
        raise exceptions.ValidationError("La compra no existe.")

    if not isinstance(purchase.total_installments_count, int) or purchase.total_installments_count <= 0:
        raise exceptions.ValidationError(
            "El número de cuotas debe de ser un entero positivo.")
    if not isinstance(purchase.total_amount, Decimal) or purchase.total_amount <= 0:
        raise exceptions.ValidationError(
            "El monto total debe de ser un número decimal positivo.")

    installment_list = []

    surcharge, amount = calculate_surcharge_over_installments(
        purchase.total_installments_count, purchase.total_amount)

    if surcharge:
        amount_per_installment = amount / purchase.total_installments_count
    else:
        amount_per_installment = purchase.total_amount / purchase.total_installments_count

    if not isinstance(amount_per_installment, Decimal):
        amount_per_installment = Decimal(
            amount_per_installment).quantize(Decimal('0.01'))
    due_date_installment = purchase.purchase_date
    for i in range(1, purchase.total_installments_count + 1):
        due_date_installment = purchase.purchase_date + relativedelta(months=i)
        installment_list.append(
            Installment(
                purchase=purchase,
                num_installment=i,
                base_amount=amount_per_installment,
                surcharge_pct=Decimal('15.0') if surcharge else Decimal('0.0'),
                discount_pct=Decimal('0.0'),
                amount_due=amount_per_installment,
                due_date=due_date_installment,
                state=Installment.State.PENDING,
                paid_amount=Decimal('0.0'),
                paid_at=None
            )
        )

    Installment.objects.bulk_create(installment_list)

    return {
        "success": True,
        "message": f"Se crearon {len(installment_list)} cuotas exitosamente para la compra {purchase_id}.",
        "data": {
            "purchase_id": purchase_id,
            "installments_created": len(installment_list),
            "total_amount": purchase.total_amount
        }
    }


@transaction.atomic
def update_state_installment(installment_id: int, nw_state: str, user: CustomUser):
    """
    Actualiza el estado de una cuota (Installment) existente.

    Permite modificar el estado de una cuota a uno nuevo válido 
    (PENDING, PAID, OVERDUE). Valida que la cuota exista, que el estado 
    solicitado sea permitido y que el nuevo estado no sea igual al actual.

    Parámetros:
        installment_id (int): Identificador de la cuota a modificar.
        nw_state (str): Nuevo estado solicitado (case-insensitive).
        user (CustomUser): Usuario que realiza la actualización.

    Excepciones:
        django.core.exceptions.ValidationError:
            - Si el estado solicitado no es válido.
            - Si la cuota no existe.
            - Si la cuota ya está en el estado solicitado.

    Retorno:
        dict: Respuesta estándar con información de la operación
            - success (bool): True si la operación fue exitosa
            - message (str): Mensaje descriptivo de la operación
            - data (dict): Datos de la operación
                - installment (Installment): Instancia de la cuota actualizada
                - old_state (str): Estado anterior
                - new_state (str): Estado nuevo
    """
    validate_id(installment_id, "Installment")

    if nw_state.upper() not in Installment.State.values:
        raise exceptions.ValidationError(
            f"El estado debe ser uno de los siguientes: {', '.join(Installment.State.values)}.")
    installment = Installment.objects.select_for_update().filter(
        id=installment_id).first()

    if not installment:
        raise exceptions.ValidationError(
            f"La cuota con el id {installment_id} no existe.")

    norm_nw_state = nw_state.upper()

    if installment.state == Installment.State.PAID and (norm_nw_state == Installment.State.OVERDUE or norm_nw_state == Installment.State.PENDING):
        raise exceptions.ValidationError(
            "No se puede cambiar el estado de una cuota PAGADA a PENDING o OVERDUE.")

    if installment.state == norm_nw_state:
        raise exceptions.ValidationError(
            f"La cuota ya se encuentra en el estado {norm_nw_state}.")
    old_state = installment.state

    installment.state = norm_nw_state
    installment.updated_by = user
    installment.save(update_fields=['state', 'updated_at', 'updated_by'])
    installment.refresh_from_db(fields=['state'])

    InstallmentAuditLog.objects.create(
        installment=installment,
        updated_by=user,
        reason=f"TRANSITION: {old_state} → {norm_nw_state}",
        delta_json={"state": [old_state, norm_nw_state]}
    )

    return {
        "success": True,
        "message": f"Cuota actualizada al estado {norm_nw_state} exitosamente.",
        "data": {
            "installment": installment,
            "old_state": old_state,
            "new_state": norm_nw_state
        }
    }


@transaction.atomic
def pay_installment(installment_id: int, paid_amount: Decimal,
                    payment_method: str, external_ref: Optional[str]):
    """
    Procesa el pago de una cuota (Installment) específica.

    Valida el método de pago, verifica el estado de la cuota, calcula el descuento aplicable,
    actualiza los campos relevantes de la cuota y registra el pago en la base de datos.

    Parámetros:
        installment_id (int): Identificador de la cuota a pagar.
        paid_amount (Decimal): Monto pagado por el usuario.
        payment_method (str): Método de pago utilizado.
        external_ref (str | None): Referencia externa del pago (opcional).

    Excepciones:
        django.core.exceptions.ValidationError:
            - Si el método de pago no es válido.
            - Si la cuota no existe.
            - Si la cuota ya está pagada.
            - Si el monto pagado es insuficiente.

    Retorno:
        dict: Respuesta estándar con información de la operación
            - success (bool): True si la operación fue exitosa
            - message (str): Mensaje descriptivo de la operación
            - data (dict): Datos de la operación
                - installment (Installment): Instancia de la cuota pagada
                - payment (Payment): Instancia del pago registrado
                - amount_paid (Decimal): Monto pagado
                - discount_applied (Decimal): Descuento aplicado
    """
    payment_method = payment_method.upper()
    if payment_method not in Payment.Method.values:
        raise exceptions.ValidationError(
            f"El método de pago debe ser uno de los siguientes: {', '.join(Payment.Method.values)}.")

    validate_id(installment_id, "Installment")

    installment = Installment.objects.select_for_update().filter(
        id=installment_id).first()
    if not installment:
        raise exceptions.ValidationError(
            f"La cuota con el id {installment_id} no existe.")

    # Obtengo el porcentaje de descuento aplicable
    discount_pct = get_installments_discount(installment)

    if installment.state == Installment.State.PAID:
        raise exceptions.ValidationError(
            "La cuota ya se encuentra en estado PAGADO.")

    if not paid_amount or not isinstance(paid_amount, Decimal) or paid_amount <= 0:
        raise exceptions.ValidationError(
            "El monto pagado debe ser un número decimal positivo.")

    # Calculo el descuento final
    final_discount = discount_pct + installment.discount_pct
    # Formateo el descuento
    final_discount = final_discount.quantize(
        Decimal('0.01'), ROUND_HALF_UP)

    amount_due = (
        installment.base_amount
        * (1 + installment.surcharge_pct / Decimal('100'))
        * (1 - final_discount / Decimal('100'))
    )

    # Formateo el monto a pagar
    amount_due = amount_due.quantize(Decimal('0.01'), ROUND_HALF_UP)

    if paid_amount < amount_due:
        raise exceptions.ValidationError(
            f"El monto pagado debe ser al menos {amount_due}.")

    installment.discount_pct = final_discount
    installment.amount_due = amount_due
    installment.paid_amount = paid_amount
    installment.paid_at = timezone.now()
    installment.state = Installment.State.PAID
    installment.save(update_fields=['discount_pct', 'amount_due',
                     'paid_amount', 'paid_at', 'state', 'updated_at'])
    installment.refresh_from_db(fields=[
                                'discount_pct', 'amount_due', 'paid_amount', 'paid_at', 'state'])

    # Crear el pago
    Payment.objects.create(
        installment=installment,
        amount=paid_amount,
        payment_method=payment_method,
        external_ref=external_ref
    )

    # Normalize values placed into JSONField to ensure they are JSON-serializable
    delta = {
        "state": [Installment.State.PENDING, Installment.State.PAID],
        "payment_method": payment_method,
        "external_ref": external_ref,
        # store decimals and datetimes as strings to avoid json serialization issues
        "paid_amount": str(paid_amount),
        "discount_pct": str(installment.discount_pct),
        "surcharge_pct": str(installment.surcharge_pct),
        "paid_at": installment.paid_at.isoformat() if installment.paid_at else None,
    }

    InstallmentAuditLog.objects.create(
        installment=installment,
        updated_by=None,
        reason=(
            f"ACTION: apply_payment; "
            f"STATE: PENDING→PAID; "
            f"PAYMENT_METHOD: {payment_method}; "
            f"EXTERNAL_REF: {external_ref}; "
            f"PAID_AMOUNT: {paid_amount}"
        ),
        delta_json=delta,
    )
    payment = Payment.objects.filter(installment=installment).last()

    response = update_state_paid_purchase(purchase=installment.purchase)

    if response.get("success") is False:
        raise exceptions.ValidationError(
            "Error al actualizar el estado de la compra asociada.")

    return {
        "success": True,
        "message": f"Cuota {installment.num_installment} pagada exitosamente.",
        "data": {
            "installment": installment,
            "payment": payment,
            "amount_paid": paid_amount,
            "discount_applied": final_discount
        }
    }


def fetch_installment_details(installment_id: int) -> dict:
    """
    Obtiene los detalles de una cuota (Installment) específica.

    Recupera la información completa de la cuota indicada y calcula si 
    corresponde aplicar un descuento por pronto pago (5%) en caso de que 
    la cuota esté pendiente y aún no vencida.

    Parámetros:
        installment_id (int): Identificador de la cuota a consultar.

    Excepciones:
        django.core.exceptions.ValidationError:
            - Si el ID no es un entero positivo.
            - Si la cuota no existe.

    Retorno:
        dict: Respuesta estándar con información de la operación
            - success (bool): True si la operación fue exitosa
            - message (str): Mensaje descriptivo de la operación
            - data (dict): Información detallada de la cuota
                - id, purchase_id, num_installment, base_amount,
                  surcharge_pct, discount_pct, amount_due, due_date,
                  state, paid_amount, paid_at
    """
    validate_id(installment_id, "Installment")

    installment = get_installments_by_id(installment_id)

    if not installment:
        raise exceptions.ValidationError(
            f"La cuota con el id {installment_id} no existe.")

    discount_pct = get_installments_discount(installment)

    installment_information = {
        "id": installment.pk,
        "purchase_id": installment.purchase.pk,
        "num_installment": installment.num_installment,
        "base_amount": installment.base_amount,
        "surcharge_pct": installment.surcharge_pct,
        "discount_pct": discount_pct if discount_pct else installment.discount_pct,
        "amount_due": installment.amount_due,
        "due_date": installment.due_date,
        "state": installment.state,
        "paid_amount": installment.paid_amount,
        "paid_at": installment.paid_at
    }

    return {
        "success": True,
        "message": f"Detalles de la cuota {installment.num_installment} obtenidos exitosamente.",
        "data": installment_information
    }


@transaction.atomic
def auto_update_overdue_installments() -> dict:
    """
    Marca automáticamente como vencidas todas las cuotas pendientes cuya fecha
    de vencimiento ya haya pasado.

    Proceso:
        - Busca todas las cuotas en estado `PENDING` cuya `due_date` sea menor
          a la fecha actual.
        - Cambia su estado a `OVERDUE`, asignando `updated_by=None` para
          reflejar que la transición fue automática y no manual.
        - Persiste los cambios en la base de datos con bloqueo de fila
          (`select_for_update`) para garantizar consistencia transaccional.
        - Registra en la tabla `InstallmentAuditLog` un evento de auditoría
          por cada transición, con detalle del estado anterior y el nuevo,
          más la razón estándar:
          `"AUTO TRANSITION: PENDING → OVERDUE"`.

    Consideraciones de negocio:
        - Una cuota entra en mora cuando han pasado 7 días posteriores al
          vencimiento sin pago registrado. En este caso, se marca como
          `OVERDUE` y posteriormente puede aplicarse el recargo por mora
          definido en las reglas de negocio.
        - Este proceso puede ser ejecutado de forma periódica (ej. cron job)
          para mantener actualizado el estado de las cuotas sin depender de
          intervención manual.

    Raises:
        ValidationError: No aplica en este flujo, pero las operaciones son
        atómicas y garantizan consistencia en caso de fallo.

        Side Effects:
        - Modifica cuotas en la tabla `Installment`.
        - Inserta registros en `InstallmentAuditLog`.

    """

    now = timezone.now()
    qs_installments = Installment.objects.select_for_update().filter(
        state=Installment.State.PENDING, due_date__lt=now.date())

    for installment in qs_installments:
        old_state = installment.state
        installment.state = Installment.State.OVERDUE
        installment.updated_by = None
        installment.save(update_fields=['state', 'updated_at', 'updated_by'])
        installment.refresh_from_db(fields=['state'])

        InstallmentAuditLog.objects.create(
            installment=installment,
            updated_by=None,
            reason="AUTO TRANSITION: PENDING → OVERDUE",
            delta_json={"state": [old_state, Installment.State.OVERDUE]}
        )
        send_installment_mora_notification(installment)

    updated_count = qs_installments.count()
    return {
        "success": True,
        "message": f"Se actualizaron {updated_count} cuotas a estado OVERDUE automáticamente.",
        "data": {
            "updated_installments": updated_count
        }
    }


@transaction.atomic
def auto_update_surcharge_late_installments() -> dict:
    """
    Aplica automáticamente un recargo del 8% a las cuotas vencidas exactamente hace 7 días.

    Busca todas las cuotas en estado `OVERDUE` cuya fecha de vencimiento (`due_date`) 
    sea exactamente 7 días antes de la fecha actual y les aplica un recargo por mora 
    del 8%. Esta función está diseñada para ser ejecutada automáticamente mediante 
    tareas programadas (cron jobs) como parte del proceso de gestión de mora.

    Proceso:
        - Calcula la fecha de filtro restando 7 días a la fecha actual.
        - Busca cuotas en estado `OVERDUE` con `due_date` igual a la fecha calculada.
        - Aplica el recargo del 8% al campo `surcharge_pct` usando `models.F()` 
          para operaciones atómicas a nivel de base de datos.
        - Actualiza los campos `surcharge_pct` y `updated_at` de cada cuota.
        - Registra cada aplicación de recargo en la tabla `InstallmentAuditLog` 
          para trazabilidad completa.

    Reglas de negocio aplicadas:
        - Solo se aplica a cuotas en estado `OVERDUE`.
        - El recargo se aplica exactamente a los 7 días del vencimiento.
        - El porcentaje de recargo es acumulativo (se suma al existente).
        - La transición es automática, sin intervención manual (`updated_by=None`).

    Excepciones:
        No lanza excepciones explícitas, pero las operaciones de base de datos 
        pueden generar errores de integridad que son manejados por la transacción atómica.

    Retorno:
        None. Los cambios se persisten directamente en la base de datos.

    """
    date_filter = timezone.now().date() - timedelta(days=7)
    pct = Decimal('8.0')
    qs_installments = Installment.objects.select_for_update().filter(
        state=Installment.State.OVERDUE, due_date=date_filter)

    if qs_installments.exists():
        for installment in qs_installments:
            old_surcharge_pct = installment.surcharge_pct
            installment.surcharge_pct = models.F(
                'surcharge_pct') + pct
            installment.save(update_fields=['surcharge_pct', 'updated_at'])
            installment.refresh_from_db(fields=['surcharge_pct'])
            new_surcharge_pct = installment.surcharge_pct
            InstallmentAuditLog.objects.create(
                installment=installment,
                updated_by=None,
                reason=f"AUTO TRANSITION: apply surcharge {pct}% for payment overdue exactly 7 days",
                delta_json={"mora": True, "surcharge_pct": [
                    str(old_surcharge_pct), str(new_surcharge_pct)]}
            )

    updated_count = qs_installments.count() if qs_installments.exists() else 0
    return {
        "success": True,
        "message": f"Se aplicó recargo del {pct}% a {updated_count} cuotas vencidas hace 7 días.",
        "data": {
            "updated_installments": updated_count,
            "surcharge_applied": pct
        }
    }


@transaction.atomic
def update_state_paid_purchase(purchase: Purchase) -> dict:
    unpaid_states = [Installment.State.PENDING, Installment.State.OVERDUE]
    all_paid = Installment.objects.filter(
        purchase=purchase, state__in=unpaid_states).count() == 0
    if all_paid:
        purchase.status = Purchase.Status.PAID
        purchase.updated_at = timezone.now()
        purchase.save(update_fields=['status', 'updated_at'])
        return {
            "success": True,
            "message": f"Compra {purchase.pk} marcada como PAGADA exitosamente.",
            "data": {
                "purchase_id": purchase.pk,
                "new_status": Purchase.Status.PAID
            }
        }
    else:
        return {
            "success": False,
            "message": f"La compra {purchase.pk} aún tiene cuotas pendientes de pago.",
            "data": {
                "purchase_id": purchase.pk,
                "current_status": purchase.status
            }
        }


def get_all_installments(user: CustomUser) -> dict:
    installments = (
        Installment.objects
        .select_related("purchase__user")
        .filter(purchase__user=user)
    ).order_by('purchase__id', 'due_date')

    return {
        "success": True,
        "message": f"Se obtuvieron {installments.count()} cuotas para el usuario {user.pk}.",
        "data": {
            "installments": installments,
            "total_count": installments.count()
        }
    }


@transaction.atomic
def delete_installments_by_id(installment_id: int, user_id: int) -> dict:
    validate_id(user_id, "User")
    validate_id(installment_id, "Installment")

    installment = get_installments_by_id(installment_id)

    if not installment:
        raise exceptions.ValidationError(
            f"La cuota con el id {installment_id} no existe.")
    installment.delete()
    return {
        "success": True,
        "message": f"Cuota {installment_id} eliminada exitosamente. Por el usuario {user_id}.",
        "data": {
            "installment_id": installment_id
        }
    }
