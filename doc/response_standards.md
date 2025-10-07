# Estándares de Respuesta para API de Compras

## Estructura de Respuestas Estándar

Todas las respuestas de la API deben seguir la siguiente estructura consistente:

```json
{
    "success": true/false,
    "message": "Mensaje descriptivo",
    "data": {
        // Datos específicos de la respuesta (opcional)
    }
}
```

## Códigos de Estado HTTP

### Éxito (2xx)

- **200 OK**: Operación exitosa
- **201 Created**: Recurso creado exitosamente
- **204 No Content**: Operación exitosa sin contenido de respuesta

### Error del Cliente (4xx)

- **400 Bad Request**: Datos inválidos o malformados
- **401 Unauthorized**: Usuario no autenticado
- **403 Forbidden**: Usuario autenticado pero sin permisos
- **404 Not Found**: Recurso no encontrado
- **409 Conflict**: Conflicto con el estado actual del recurso

### Error del Servidor (5xx)

- **500 Internal Server Error**: Error interno del servidor

## Mensajes de Error por Permisos

### 403 Forbidden - Acceso Denegado

#### Usuario intenta acceder a compra de otro usuario

```json
{
    "success": false,
    "message": "No tienes permisos para acceder a esta compra. Solo puedes ver tus propias compras.",
    "data": {
        "error_type": "access_denied",
        "resource": "purchase",
        "action": "view"
    }
}
```

#### Usuario intenta modificar compra de otro usuario

```json
{
    "success": false,
    "message": "No tienes permisos para modificar esta compra. Solo puedes modificar tus propias compras.",
    "data": {
        "error_type": "access_denied",
        "resource": "purchase",
        "action": "modify"
    }
}
```

#### Usuario no admin intenta acceder a funciones de administrador

```json
{
    "success": false,
    "message": "Esta función requiere permisos de administrador. Contacta a un administrador si necesitas realizar esta acción.",
    "data": {
        "error_type": "admin_required",
        "resource": "admin_function",
        "action": "access"
    }
}
```

#### Usuario intenta cancelar compra pagada (solo admin)

```json
{
    "success": false,
    "message": "Solo los administradores pueden cancelar compras que ya han sido pagadas.",
    "data": {
        "error_type": "admin_required",
        "resource": "purchase",
        "action": "cancel_paid",
        "current_status": "PAID"
    }
}
```

#### Usuario intenta reactivar compra cancelada (solo admin)

```json
{
    "success": false,
    "message": "Solo los administradores pueden reactivar compras canceladas.",
    "data": {
        "error_type": "admin_required",
        "resource": "purchase", 
        "action": "reactivate_cancelled",
        "current_status": "CANCELLED"
    }
}
```

### 404 Not Found - Recurso No Encontrado

#### Compra no existe

```json
{
    "success": false,
    "message": "La compra solicitada no existe o ha sido eliminada.",
    "data": {
        "error_type": "not_found",
        "resource": "purchase",
        "resource_id": 123
    }
}
```

#### Usuario no existe

```json
{
    "success": false,
    "message": "El usuario especificado no existe.",
    "data": {
        "error_type": "not_found",
        "resource": "user",
        "resource_id": 456
    }
}
```

### 400 Bad Request - Datos Inválidos

#### Datos faltantes o inválidos

```json
{
    "success": false,
    "message": "Los datos proporcionados son inválidos. Revisa los campos requeridos.",
    "data": {
        "error_type": "validation_error",
        "invalid_fields": ["field1", "field2"],
        "details": {
            "field1": "Este campo es requerido",
            "field2": "Debe ser un número positivo"
        }
    }
}
```

#### Transición de estado inválida

```json
{
    "success": false,
    "message": "No se puede cambiar el estado de la compra de PAID a OPEN. Las transiciones válidas son: [CANCELLED]",
    "data": {
        "error_type": "invalid_transition",
        "current_status": "PAID",
        "requested_status": "OPEN",
        "allowed_transitions": ["CANCELLED"]
    }
}
```

## Mensajes de Éxito

### Operaciones exitosas

```json
{
    "success": true,
    "message": "Compra actualizada exitosamente.",
    "data": {
        "purchase_id": 123,
        "updated_fields": ["status"],
        "new_values": {
            "status": "PAID"
        }
    }
}
```

## Buenas Prácticas para Mensajes

1. **Ser específicos**: Los mensajes deben indicar claramente qué está pasando
2. **Ser útiles**: Sugerir qué hacer para resolver el problema
3. **Ser consistentes**: Usar la misma estructura y terminología
4. **Ser seguros**: No revelar información sensible en los mensajes de error
5. **Ser amigables**: Usar un tono profesional pero accesible

## Logging de Errores de Permisos

Para cada error de permisos, se debe hacer log con el siguiente formato:

```python
logger.warning(f"Access denied - User {user.username} (ID: {user.id}) attempted to {action} {resource} {resource_id}")
```

Ejemplos:

- `Access denied - User juan.perez (ID: 5) attempted to view purchase 123`
- `Access denied - User maria.garcia (ID: 8) attempted to modify purchase 456`
- `Access denied - User cliente1 (ID: 10) attempted to access admin function analytics`
