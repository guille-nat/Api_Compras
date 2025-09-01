from django.db import transaction, models
from django.core import exceptions
from .models import InventoryMovement, InventoryRecord
from api.storage_location.models import StorageLocation
from api.products.models import Product
from api.users.models import CustomUser
from .utils import get_total_stock
from datetime import date


@transaction.atomic
def transference_inventory(
        product: Product, from_location: StorageLocation, to_location: StorageLocation,
        description: str, quantity: int, reference_id: int, user: CustomUser):
    """
    Transfiere stock de un producto desde una ubicación origen hacia una ubicación destino,
    respetando el lote (`batch_code`) y la fecha de vencimiento (`expiry_date`) cuando existan,
    y registrando los movimientos de inventario resultantes.

    La operación es transaccional y bloquea las filas de inventario involucradas mediante
    `SELECT FOR UPDATE` para evitar condiciones de carrera. Si el producto en origen está
    distribuido en múltiples registros de inventario (p. ej., distintos lotes o vencimientos),
    la función consume siguiendo un orden FEFO (first-expire, first-out), consolidando en
    destino por la clave compuesta `(product, location, batch_code, expiry_date)`:
    - Si ya existe un `InventoryRecord` en destino con esa combinación, incrementa su cantidad.
    - Si no existe, crea uno nuevo con cantidad inicial 0 y suma la transferencia.

    Además, por cada tramo consumido se genera un `InventoryMovement` con `reason=TRANSFER`
    y `reference_type=MANUAL`, dejando traza auditada.

    Args:
        product (Product): Producto a transferir.
        from_location (StorageLocation): Ubicación origen del stock.
        to_location (StorageLocation): Ubicación destino del stock (debe ser distinta de la origen).
        description (str): Descripción libre del motivo/observaciones del movimiento.
        quantity (int): Cantidad total a transferir (debe ser > 0).
        reference_id (int): Identificador externo para enlazar la operación (p. ej. número de orden).
        user (CustomUser): Usuario que ejecuta la transferencia (usado en auditoría).

    Returns:
        dict: Un diccionario con métricas de la operación, por ejemplo:
            {
                "moved": <int>,              # cantidad total transferida
                "movements_count": <int>,    # cantidad de registros InventoryMovement creados
            }

    Raises:
        django.core.exceptions.ValidationError:
            - Si `quantity <= 0`.
            - Si `from_location == to_location`.
            - Si no hay stock en el origen.
            - Si el stock total disponible en el origen es menor a `quantity`.
            - Si durante el consumo se detecta inconsistencia por concurrencia (fallback defensivo).

    Notas:
        - Se prioriza FEFO cuando existen fechas de vencimiento; si no hay vencimiento se ordena por id.
        - Se bloquean filas de origen (y destino en `get_or_create`) con `select_for_update()`.
        - Si un registro de origen queda con cantidad 0 tras la operación, es eliminado.
        - Los `InventoryMovement` creados usan `Reason.TRANSFER` y `RefType.MANUAL`.
        - La consolidación en destino respeta la unicidad `(product, location, batch_code, expiry_date)`.
    """
    # Validaciones iniciales
    if not isinstance(quantity, int) or quantity <= 0:
        raise exceptions.ValidationError("La cantidad debe ser un entero > 0.")
    if from_location == to_location:
        raise exceptions.ValidationError(
            "Origen y destino no pueden ser iguales.")

    # Buscar IR de los location IR con id from_location y otro con to_location
    # Selección de IR origen con LOCK (evitar carreras)
    origin_qs = (
        InventoryRecord.objects
        .select_for_update()
        .filter(product=product, location=from_location)
    )

    # Producto esta en origin (IR)
    total = get_total_stock(origin_qs)
    if total == 0:
        raise exceptions.ValidationError(
            f"No hay stock en {from_location.name}.")
    if total < quantity:
        raise exceptions.ValidationError(
            f"Stock insuficiente en {from_location.name}.")

    # Obtenemos la existencia de batch_code y de expiry_date
    rows = list(origin_qs.order_by("expiry_date__isnull",
                "expiry_date", "id"))  # Enfoque FEFO

    # cantidad de stock solicitado para la transferencia
    remaining = quantity
    i = 0
    movements = []

    # Consumir del origen en orden FEFO, acumulando hacia destino
    while remaining > 0:
        while i < len(rows) and rows[i].quantity <= 0:
            i += 1
        if i == len(rows):
            raise exceptions.ValidationError("Stock insuficiente (carrera).")

        ir_from = rows[i]
        take = min(ir_from.quantity, remaining)

        # Destino con misma composite key (product, to_location, batch, expiry)
        ir_to, created = (
            InventoryRecord.objects
            .select_for_update()
            .get_or_create(
                product=product,
                location=to_location,
                batch_code=ir_from.batch_code,
                expiry_date=ir_from.expiry_date,
                defaults={"quantity": 0, "updated_by": user},
            ))

        # Sumamos el quantity a el destino
        ir_to.quantity = models.F("quantity") + take
        ir_to.updated_by = user
        ir_to.save(update_fields=[
            "quantity", "updated_by", "updated_at"])
        ir_to.refresh_from_db(fields=["quantity"])

        # Restamos el quantity al origen
        ir_from.quantity = models.F("quantity") - take
        ir_from.updated_by = user
        ir_from.save(update_fields=[
            "quantity", "updated_by", "updated_at"])
        ir_from.refresh_from_db(fields=["quantity"])
        # Preguntamos si al restar al origen ese stock = 0
        if ir_from.quantity == 0:
            # Eliminamos el registro origen
            ir_from.delete()

        # Registrar movimiento
        movements.append(InventoryMovement(
            product=product,
            batch_code=ir_from.batch_code,
            expiry_date=ir_from.expiry_date,
            from_location=from_location,
            to_location=to_location,
            quantity=take,
            reason=InventoryMovement.Reason.TRANSFER,
            description=description,
            reference_type=InventoryMovement.RefType.MANUAL,
            reference_id=reference_id,
            created_by=user,
            updated_by=user,
        ))
        remaining -= take

    InventoryMovement.objects.bulk_create(movements)
    return {"moved": quantity, "movements_count": len(movements)}


@transaction.atomic
def purchase_entry_inventory(
        product: Product, to_location: StorageLocation, expiry_date: date | None, batch_code: str | None,
        description: str, quantity: int, reference_id: int, user: CustomUser):
    """
    Registra una ENTRADA de inventario asociada a una compra a proveedores.

    Este proceso sigue las reglas de negocio del sistema API_COMPRAS:
    - El inventario se gestiona por ubicación, lote (opcional) y fecha de vencimiento (opcional).
    - Cada variación de stock debe generar un movimiento registrado.
    - Para entradas de compra, el origen es `None` y el destino es la ubicación de almacenamiento.


    Args:
        product (Product): Producto al que corresponde la entrada.
        to_location (StorageLocation): Ubicación destino donde se almacenará el stock.
        expiry_date (date | None): Fecha de vencimiento asociada al lote (opcional).
        batch_code (str | None): Código de lote del producto (opcional).
        description (str): Descripción del movimiento (ej. detalle de la compra).
        quantity (int): Cantidad a ingresar. Debe ser mayor a 0.
        reference_id (int): ID de la compra que origina la entrada.
        user (CustomUser): Usuario que realiza la operación.

    Returns:
        InventoryRecord: El registro de inventario actualizado o creado.

    Raises:
        ValidationError: Si `quantity` <= 0, `reference_id` inválido,
                         o `expiry_date` no es instancia de `date` ni None.
    """
    # Validaciones iniciales
    if not isinstance(quantity, int) or quantity <= 0:
        raise exceptions.ValidationError("La cantidad debe ser un entero > 0.")
    if expiry_date is not None:
        if not isinstance(expiry_date, date):
            raise exceptions.ValidationError(
                "expiry_date debe ser date o None.")
    # Normalización de batch_code
    norm_batch = (batch_code or "").strip() or None
    if norm_batch:
        norm_batch = norm_batch.upper()

    # Buscar IR
    # Selección de IR origen con LOCK (evitar carreras)
    base_qs = (
        InventoryRecord.objects
        .select_for_update()
        .filter(product=product, location=to_location)
    )

    inventory_record = base_qs.filter(
        batch_code=norm_batch, expiry_date=expiry_date).first()

    # Verifica si existe un registro con el mismo batch_code y  expiry_date
    if inventory_record:
        # Modificamos ese registro coincidente
        inventory_record.quantity = models.F("quantity") + quantity
        inventory_record.updated_by = user
        inventory_record.save(
            update_fields=["quantity", "updated_by", "updated_at"])
        inventory_record.refresh_from_db(fields=["quantity"])
    else:
        # Creamos registro nuevo si no se encontró coincidencia
        inventory_record = InventoryRecord.objects.create(
            product=product,
            location=to_location,
            batch_code=norm_batch,
            expiry_date=expiry_date,
            quantity=quantity,
            updated_by=user,
        )

    # Registrar movimiento
    # Movimiento: entrada por compra → from=None, to=to_location
    InventoryMovement.objects.create(
        product=product,
        batch_code=norm_batch,
        expiry_date=expiry_date,
        from_location=None,
        to_location=to_location,
        quantity=quantity,
        reason=InventoryMovement.Reason.PURCHASE_ENTRY,
        description=description,
        reference_type=InventoryMovement.RefType.PURCHASE,
        reference_id=reference_id,
        created_by=user,
        updated_by=user,
    )

    return {"inventory": inventory_record}


@transaction.atomic
def exit_sale_inventory(
    product: Product, from_location: StorageLocation,
    description: str, quantity: int, reference_id: int, user: CustomUser
):
    """
    Registra una salida de inventario por venta (`EXIT_SALE`) desde una ubicación origen.

    La operación es transaccional y bloquea los registros de inventario de origen
    mediante `SELECT FOR UPDATE` para evitar condiciones de carrera. Si el producto en
    origen está distribuido en varios registros de inventario (p. ej., distintos lotes
    o fechas de vencimiento), la función consume stock siguiendo la estrategia FEFO
    (first-expire, first-out).

    Por cada tramo consumido se genera un `InventoryMovement` con:
    - `reason = InventoryMovement.Reason.EXIT_SALE`
    - `reference_type = InventoryMovement.RefType.SALE`

    Args:
        product (Product): Producto a vender (egreso de stock).
        from_location (StorageLocation): Ubicación origen del stock a descontar.
        description (str): Descripción libre del motivo/observaciones de la salida.
        quantity (int): Cantidad total a egresar (debe ser > 0).
        reference_id (int): Identificador externo de la venta/orden asociada.
        user (CustomUser): Usuario ejecutor de la operación (para auditoría).

    Returns:
        dict: Diccionario con métricas de la operación:
            {
                "moved": <int>,              # cantidad total egresada
                "movements_count": <int>,    # cantidad de movimientos generados
            }

    Raises:
        django.core.exceptions.ValidationError:
            - Si `quantity <= 0`.
            - Si no hay stock en el origen.
            - Si el stock total disponible es menor a `quantity`.
            - Si ocurre inconsistencia por concurrencia durante el consumo.

    Notas:
        - Se aplica FEFO cuando hay fechas de vencimiento; si no existen, se ordena por id.
        - Si un `InventoryRecord` llega a cantidad 0 tras la operación, se elimina.
        - Cada movimiento conserva el `batch_code` y `expiry_date` originales del tramo.
        - Se recomienda usar este método dentro del flujo de confirmación de ventas,
          junto con validaciones de negocio adicionales (ej. estado de la orden).
    """
    # Validaciones iniciales
    if not isinstance(quantity, int) or quantity <= 0:
        raise exceptions.ValidationError("La cantidad debe ser un entero > 0.")
    # Buscar IR
    # Selección de IR origen con LOCK (evitar carreras)
    origin_qs = (
        InventoryRecord.objects
        .select_for_update()
        .filter(product=product, location=from_location)
    )

    # Producto esta en el (IR)
    total = get_total_stock(origin_qs)
    if total == 0:
        raise exceptions.ValidationError(
            f"No hay stock en {from_location.name}.")
    if total < quantity:
        raise exceptions.ValidationError(
            f"Stock insuficiente en {from_location.name}.")

    # Obtenemos la existencia de batch_code y de expiry_date
    rows = list(origin_qs.order_by("expiry_date__isnull",
                                   "expiry_date", "id"))  # Enfoque FEFO

    # cantidad de stock solicitado para la salida de venta
    remaining = quantity
    i = 0
    movements = []

    # Consumir en orden FEFO
    while remaining > 0:
        while i < len(rows) and rows[i].quantity <= 0:
            i += 1
        if i == len(rows):
            raise exceptions.ValidationError("Stock insuficiente (carrera).")

        ir_from = rows[i]
        take = min(ir_from.quantity, remaining)

        # Restamos el quantity según lo indica la compra
        InventoryRecord.objects.filter(pk=ir_from.pk).update(
            quantity=models.F("quantity") - take,
            updated_by=user,
        )
        ir_from.refresh_from_db(fields=["quantity"])
        # Preguntamos si al restar, ese stock = 0
        if ir_from.quantity == 0:
            # Eliminamos el registro con stock vació
            ir_from.delete()
        # Registrar movimiento
        movements.append(InventoryMovement(
            product=product,
            batch_code=ir_from.batch_code,
            expiry_date=ir_from.expiry_date,
            from_location=from_location,
            to_location=None,
            quantity=take,
            reason=InventoryMovement.Reason.EXIT_SALE,
            description=description,
            reference_type=InventoryMovement.RefType.SALE,
            reference_id=reference_id,
            created_by=user,
            updated_by=user,
        ))
        remaining -= take

    InventoryMovement.objects.bulk_create(movements)
    return {"moved": quantity, "movements_count": len(movements)}


@transaction.atomic
def adjustment_inventory(
    product: Product, from_location: StorageLocation, expiry_date: date | None, batch_code: str | None,
    description: str, quantity: int, reference_id: int, user: CustomUser,
    aggregate: bool | None, remove: bool | None, adjusted_other: bool | None,
    modify_expiry_date: date | None,
    modify_batch_code: str | None,
    modify_location: StorageLocation | None,
):
    """
    Realiza un ajuste de inventario en un `InventoryRecord` existente, permitiendo:
    - Agregar stock.
    - Quitar stock.
    - Ajustar el registro a otro estado (cambio de lote, vencimiento o ubicación).

    La operación es transaccional y siempre genera un `InventoryMovement`
    con motivo `ADJUSTMENT` (o `RETURN_ENTRY` si la enumeración lo contempla),
    garantizando trazabilidad de la variación.

    Reglas de negocio:
        - Solo puede elegirse **una opción** entre `aggregate`, `remove` o `adjusted_other`.
        - Si se informan `batch_code` y `expiry_date`, deben proveerse en conjunto.
        - Si se solicita mover a otra ubicación, esta debe existir.
        - Si un registro queda en cantidad cero, puede eliminarse según las reglas de stock.
        - La unicidad `(product, location, batch_code, expiry_date)` debe respetarse.

    Args:
        product (Product): Producto a ajustar.
        from_location (StorageLocation): Ubicación origen del inventario.
        expiry_date (date | None): Fecha de vencimiento del lote (si aplica).
        batch_code (str | None): Código de lote (si aplica).
        description (str): Descripción libre del ajuste (motivo u observaciones).
        quantity (int): Cantidad a ajustar. Debe ser > 0.
        reference_id (int): Identificador externo que vincula el ajuste (ej. orden).
        user (CustomUser): Usuario que ejecuta el ajuste.
        aggregate (bool | None): Si True, suma la cantidad al stock existente.
        remove (bool | None): Si True, descuenta la cantidad del stock existente.
        adjusted_other (bool | None): Si True, aplica modificaciones adicionales
            (fecha de vencimiento, batch_code, ubicación).
        modify_expiry_date (date | None): Nueva fecha de vencimiento (solo si `adjusted_other=True`).
        modify_batch_code (str | None): Nuevo código de lote (solo si `adjusted_other=True`).
        modify_location (StorageLocation | None): Nueva ubicación de almacenamiento
            (solo si `adjusted_other=True`).

    Raises:
        ValidationError:
            - Si `quantity <= 0`.
            - Si `expiry_date` no es instancia de `date` ni None.
            - Si se informa solo uno de `batch_code` o `expiry_date`.
            - Si más de una bandera (`aggregate`, `remove`, `adjusted_other`) está activa,
              o si ninguna lo está.
            - Si `modify_location` no existe en base de datos.

    Returns:
        dict: Diccionario con los objetos afectados:
            {
                "inventory": InventoryRecord,   # Registro actualizado tras el ajuste
                "movement": InventoryMovement,  # Movimiento de inventario generado
            }
    """
    if not isinstance(quantity, int) or quantity <= 0:
        raise exceptions.ValidationError("La cantidad debe ser un entero > 0.")
    if expiry_date is not None:
        if not isinstance(expiry_date, date):
            raise exceptions.ValidationError(
                "expiry_date debe ser date o None.")
    # Normalización de batch_code
    norm_batch = (batch_code or "").strip() or None
    if norm_batch:
        norm_batch = norm_batch.upper()

    if (bool(aggregate) and bool(adjusted_other) and bool(remove)) or (not bool(aggregate) and not bool(adjusted_other) and not bool(remove)):
        raise exceptions.ValidationError(
            "Debe de elegir una opción (Agregar - Quitar - Ajustar Otro).")
    # No tiene que pasar: 1) Los 3 sean False, 2) 2 sean True, 3) 3 sean True

    if bool(norm_batch) != bool(expiry_date):
        raise exceptions.ValidationError(
            "Debe informar 'batch_code' y 'expiry_date' juntos, o ninguno."
        )
    # Buscar IR
    # Selección de IR origen con LOCK (evitar carreras)
    base_qs = (
        InventoryRecord.objects
        .select_for_update()
        .filter(product=product, location=from_location)
    )
    # Verificar si posen batch_code and expiry_date
    match_batch = norm_batch if norm_batch else None
    match_exp = expiry_date if expiry_date else None

    inventory_record = base_qs.filter(
        batch_code=match_batch, expiry_date=match_exp).first()
    if inventory_record:
        # Modificamos ese registro coincidente
        # SUMA sin condición gte
        if not adjusted_other:
            if aggregate:
                inventory_record.quantity = models.F("quantity") + quantity
            if remove:
                inventory_record.quantity = models.F("quantity") - quantity
        else:
            if aggregate:
                inventory_record.quantity = models.F("quantity") + quantity
            if remove:
                inventory_record.quantity = models.F("quantity") - quantity
            if modify_expiry_date:
                inventory_record.expiry_date = modify_expiry_date
            if modify_batch_code:
                inventory_record.batch_code = modify_batch_code
            if modify_location:
                storage = StorageLocation.objects.filter(
                    pk=modify_location.pk).exists()
                if bool(storage):
                    inventory_record.location = modify_location
                else:
                    raise exceptions.ValidationError(
                        f"La ubicación seleccionada '{modify_location}' no existe")
        inventory_record.updated_by = user
        inventory_record.save(
            update_fields=["quantity", "updated_by", "updated_at"])
        inventory_record.refresh_from_db(fields=["quantity"])

        movement = InventoryMovement.objects.create(
            product=product,
            batch_code=modify_batch_code if modify_batch_code else norm_batch,
            expiry_date=modify_expiry_date if modify_expiry_date else expiry_date,
            from_location=from_location,
            to_location=modify_location if bool(
                modify_location) and bool(storage) else None,
            quantity=quantity,
            reason=(InventoryMovement.Reason.RETURN_ENTRY
                    if hasattr(InventoryMovement.Reason, "RETURN_ENTRY")
                    else InventoryMovement.Reason.ADJUSTMENT),
            description=description,
            reference_type=InventoryMovement.RefType.MANUAL,
            reference_id=reference_id,
            created_by=user,
            updated_by=user,
        )

        return {"inventory": inventory_record, "movement": movement}


@transaction.atomic
def return_output_inventory(
    product: Product, from_location: StorageLocation, expiry_date: date | None, batch_code: str | None,
    description: str, quantity: int, reference_id: int, user: CustomUser
):
    """
    Registra una SALIDA de inventario desde una ubicación específica, asociada a una devolución o ajuste manual.

    Este proceso cumple las reglas de negocio del sistema API_COMPRAS:
    - El inventario se gestiona por producto, ubicación, lote (opcional) y fecha de vencimiento (opcional).
    - Toda variación de stock debe generar un movimiento de inventario para trazabilidad.
    - Para salidas, si el producto tiene vencimiento se aplica control estricto (FEFO en otros casos).

    Args:
        product (Product): Producto a descontar.
        from_location (StorageLocation): Ubicación origen de la salida.
        expiry_date (date | None): Fecha de vencimiento asociada al lote (opcional).
        batch_code (str | None): Código de lote del producto (opcional).
        description (str): Descripción del movimiento.
        quantity (int): Cantidad a retirar. Debe ser > 0.
        reference_id (int): Identificador de la referencia externa (ej. devolución o ajuste).
        user (CustomUser): Usuario que realiza la operación.

    Returns:
        InventoryRecord: El registro de inventario actualizado tras la salida.

    Raises:
        ValidationError:
            - Si la cantidad es inválida (<= 0).
            - Si `expiry_date` no es `date` ni `None`.
            - Si se informa solo uno de los campos (`batch_code` o `expiry_date`).
            - Si no existe el `InventoryRecord` esperado.
            - Si el stock disponible es insuficiente para cubrir la salida.
    """
    # Validaciones iniciales
    if not isinstance(quantity, int) or quantity <= 0:
        raise exceptions.ValidationError("La cantidad debe ser un entero > 0.")
    if expiry_date is not None:
        if not isinstance(expiry_date, date):
            raise exceptions.ValidationError(
                "expiry_date debe ser date o None.")

    # Normalización de batch_code
    norm_batch = (batch_code or "").strip() or None
    if norm_batch:
        norm_batch = norm_batch.upper()

    if bool(norm_batch) != bool(expiry_date):
        raise exceptions.ValidationError(
            "Debe informar 'batch_code' y 'expiry_date' juntos, o ninguno."
        )

    # Buscar IR
    # Selección de IR origen con LOCK (evitar carreras)
    base_qs = (
        InventoryRecord.objects
        .select_for_update()
        .filter(product=product, location=from_location)
    )
    # Verificar si posen batch_code and expiry_date
    match_batch = norm_batch if norm_batch else None
    match_exp = expiry_date if expiry_date else None

    inventory_record = base_qs.filter(
        batch_code=match_batch, expiry_date=match_exp).first()
    if not inventory_record:
        raise exceptions.ValidationError(
            f"No existe  registro de inventario en '{from_location.name}' para "
            f"producto={product.id} lote={match_batch} vence={match_exp}."
        )

    # Modificamos ese registro coincidente
    updated = (
        InventoryRecord.objects.filter(
            pk=inventory_record.pk, quantity__gte=quantity
        ).update(
            quantity=models.F("quantity") - quantity,
            updated_by=user
        )
    )
    if updated == 0:
        inventory_record.refresh_from_db(fields=["quantity"])
        raise exceptions.ValidationError(
            f"Stock insuficiente para producto={product.id} "
            f"(disp={inventory_record.quantity}, req={quantity}) en '{from_location.name}' "
            f"(lote={match_batch}, vence={match_exp})."
        )

    # Registrar movimiento
    # Movimiento: salida por devolución → from=from_location, to=None
    movement = InventoryMovement.objects.create(
        product=product,
        batch_code=match_batch,
        expiry_date=match_exp,
        from_location=from_location,
        to_location=None,
        quantity=quantity,
        reason=(InventoryMovement.Reason.RETURN_OUTPUT
                if hasattr(InventoryMovement.Reason, "RETURN_OUTPUT")
                else InventoryMovement.Reason.ADJUSTMENT),
        description=description,
        reference_type=InventoryMovement.RefType.MANUAL,
        reference_id=reference_id,
        created_by=user,
        updated_by=user,
    )
    inventory_record.refresh_from_db(fields=["quantity"])

    return {"inventory": inventory_record, "movement": movement}


@transaction.atomic
def return_entry_inventory(
    product: Product, to_location: StorageLocation, expiry_date: date | None, batch_code: str | None,
    description: str, quantity: int, reference_id: int, user: CustomUser
):
    """
     Registra una ENTRADA de inventario (ej. devolución o ajuste) en una ubicación específica.

    Este proceso implementa las reglas de negocio del sistema API_COMPRAS:
    - El inventario se gestiona por producto, ubicación y opcionalmente por lote/fecha de vencimiento.
    - Se exige consistencia: 'batch_code' y 'expiry_date' deben informarse juntos o no informarse.
    - Si el registro de inventario (InventoryRecord) ya existe, incrementa la cantidad.
    - Si no existe, crea un nuevo registro de inventario (manejando concurrencia con transacción y 
      posible reintento en caso de condición de carrera).
    - Todo cambio de stock genera un movimiento de inventario (InventoryMovement) con motivo RETURN_ENTRY.

    Args:
        product (Product): Producto al que se ingresa stock.
        to_location (StorageLocation): Ubicación destino donde se almacena el inventario.
        expiry_date (date | None): Fecha de vencimiento del lote (opcional, se exige junto con batch_code).
        batch_code (str | None): Código de lote del producto (opcional, se exige junto con expiry_date).
        description (str): Descripción del movimiento (ej. detalle de la devolución).
        quantity (int): Cantidad ingresada, debe ser > 0.
        reference_id (int): Identificador de referencia externa (ejemplo: devolución, ajuste).
        user (CustomUser): Usuario que ejecuta la operación.

    Returns:
        InventoryRecord: El registro de inventario creado o actualizado.

    Raises:
        ValidationError:
            - Si la cantidad no es un entero positivo.
            - Si expiry_date no es un date válido o es inconsistente con batch_code.
            - Si se informa solo uno de los campos batch_code/expiry_date.
    """
    # Validaciones iniciales
    if not isinstance(quantity, int) or quantity <= 0:
        raise exceptions.ValidationError("La cantidad debe ser un entero > 0.")
    if expiry_date is not None:
        if not isinstance(expiry_date, date):
            raise exceptions.ValidationError(
                "expiry_date debe ser date o None.")

    # Normalización de batch_code
    norm_batch = (batch_code or "").strip() or None
    if norm_batch:
        norm_batch = norm_batch.upper()

    if bool(norm_batch) != bool(expiry_date):
        raise exceptions.ValidationError(
            "Debe informar 'batch_code' y 'expiry_date' juntos, o ninguno."
        )

    # Buscar IR
    # Selección de IR origen con LOCK (evitar carreras)
    base_qs = (
        InventoryRecord.objects
        .select_for_update()
        .filter(product=product, location=to_location)
    )
    # Verificar si posen batch_code and expiry_date
    match_batch = norm_batch if norm_batch else None
    match_exp = expiry_date if expiry_date else None

    inventory_record = base_qs.filter(
        batch_code=match_batch, expiry_date=match_exp).first()
    if inventory_record:
        # Modificamos ese registro coincidente
        # SUMA sin condición gte
        inventory_record.quantity = models.F("quantity") + quantity
        inventory_record.updated_by = user
        inventory_record.save(
            update_fields=["quantity", "updated_by", "updated_at"])
        inventory_record.refresh_from_db(fields=["quantity"])
    else:

        from django.db import IntegrityError
        try:
            inventory_record = InventoryRecord.objects.create(
                product=product,
                location=to_location,
                batch_code=match_batch,
                expiry_date=match_exp,
                quantity=quantity,
                updated_by=user,
            )
        except IntegrityError:
            # Reintento: alguien lo creó entre tu select_for_update y el create.
            inventory_record = InventoryRecord.objects.get(
                product=product, location=to_location,
                batch_code=match_batch, expiry_date=match_exp
            )
            inventory_record.quantity = models.F("quantity") + quantity
            inventory_record.updated_by = user
            inventory_record.save(
                update_fields=["quantity", "updated_by", "updated_at"])
            inventory_record.refresh_from_db(fields=["quantity"])

    # Registrar movimiento
    # Movimiento: entrada por devolución → from=None, to=to_location
    movement = InventoryMovement.objects.create(
        product=product,
        batch_code=match_batch,
        expiry_date=match_exp,
        from_location=None,
        to_location=to_location,
        quantity=quantity,
        reason=(InventoryMovement.Reason.RETURN_ENTRY
                if hasattr(InventoryMovement.Reason, "RETURN_ENTRY")
                else InventoryMovement.Reason.ADJUSTMENT),
        description=description,
        reference_type=InventoryMovement.RefType.MANUAL,
        reference_id=reference_id,
        created_by=user,
        updated_by=user,
    )

    return {"inventory": inventory_record, "movement": movement}
