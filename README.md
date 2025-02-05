# **💸API_COMPRAS**

API diseñada para la gestión de compras, pagos, cuotas, inventario y usuarios. Este proyecto incluye validaciones robustas y reglas de negocio para asegurar un manejo eficiente y seguro de las operaciones.

## **🌟Características Principales**

- Gestión de productos e inventario.
- Registro de compras con detalles asociados.
- Manejo de cuotas y pagos con descuentos y recargos.
- Notificaciones automáticas para usuarios sobre el estado de sus compras y pagos.

---

## ✅ **Resumen de Mejoras Aplicadas**

1. Cambio a versión 1.0.1.
2. URIs en inglés y en plural.  
3. Eliminación de la barra final en rutas.
4. Migraciones centralizadas en el root.
5. Documentación clara sobre JWT y Bearer Token.
6. Cambio el nombre de las variables y modelos a inglés.
7. Configuración para que todos los datos String(str) se guarden en minúsculas, excepto los campos claves como "product_code" y "payment_method".
8. Cambio del modelo de usuario a CustomUser donde se modificó e método sve para asegurar que los campos "first_name, last_name, email y username" se guarden en minúsculas.
9. Optimización de la función "get_queryset" de api/user/views.py .

---

## 🔧 **Últimos Archivos Modificados**

1. Cambio de nombre en apps > api.compras => api.purchases | api.pagos => api.payments | api.productos => api.users <.
2. Cambio nombre de las clases modelos y sus atributos.
3. Eliminación de las carpetas individuales de Migrations para unirlas todas en una sola en el root.
4. En api.utils.py se cambio el nombre de la función y los parámetros de "enviar_correo(email_destino, asunto, mensaje_html)" pasar a ser "sendEmail(destination_email, subject, message_html)".

---
---

## ⏳ **Resumen de Mejoras Futuras**

1. Implementación de protección específica contra DDoS.  

---

## **🔒Autenticación con JWT**

El proyecto utiliza **JSON Web Tokens (JWT)** bajo el esquema **Bearer** para la autenticación. Esto asegura que solo usuarios autenticados puedan acceder a las rutas protegidas de la API.

### **Obtener un Token de Acceso**

Para obtener un token de acceso, realiza una petición `POST` al endpoint `/api/token/` con las credenciales del usuario:

```json
{
  "username": "tu_usuario",
  "password": "tu_contraseña"
}
```

### **Uso del Token**

Incluye el token en el encabezado de las peticiones protegidas:

```
   Authorization: Bearer <tu_token>
```

## **💼Reglas de Negocio**

### **📝Productos e Inventario**

1. **Stock Disponible**:
   - Antes de procesar una compra, se valida que el stock del producto sea suficiente.
   - Si el stock no es suficiente, se rechaza la compra con un mensaje detallado.

2. **Actualización de Stock**:
   - Al procesar una compra, el stock del producto se reduce según la cantidad adquirida.

---

### **🛒Compras**

1. **Detalles de Compra**:
   - Cada compra puede incluir uno o más productos.
   - Es obligatorio especificar los productos y la cantidad comprada.

2. **Validación de Cuotas**:
   - El número de cuotas debe ser mayor a 0.
   - Si el número de cuotas supera las 6, cada cuota tendrá un incremento del **15%** en su monto.

3. **Descuento Aplicado**:
   - Es posible aplicar un descuento general al monto total de la compra mediante el campo `descuento_aplicado`.

4. **Fecha de Vencimiento**:
   - La fecha de vencimiento total de la compra se calcula automáticamente con base en la fecha de compra y el número de cuotas (cada cuota tiene un plazo de 30 días).

---

### **💰Pagos y Cuotas**

1. **Descuento por Pronto Pago**:
   - Si una cuota es pagada antes de su fecha de vencimiento, se aplica un descuento adicional del **5%** al monto de la cuota.

2. **Recargo por Pago Tardío**:
   - Si una cuota no se paga dentro del plazo de 30 días desde su emisión, se aplica un recargo del **8%** sobre el monto de la cuota.

3. **Cálculo de Montos en Cuotas**:
   - En compras con más de 6 cuotas, se aplica un incremento del **15%** en el monto de cada cuota.

---

## **📄Documentación de los Endpoints**

La documentación de los endpoints está disponible en los siguientes enlaces:

- **Swagger:** [http://localhost:8000/doc](http://localhost:8000/doc)
- **Redoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

Ambos proporcionan una descripción completa de los endpoints disponibles, métodos permitidos, parámetros requeridos y ejemplos de respuestas.

---

## **📧 Envío de Correos Electrónicos**

El proyecto incluye una funcionalidad para el envío de correos electrónicos a los usuarios, utilizando la configuración de correo de Django. Los correos pueden incluir contenido en formato HTML para proporcionar una presentación visual más profesional.

## **🚀 Configuración del Servicio de Correo**

Para que el sistema de envío de correos funcione correctamente, es necesario configurar las variables de entorno relacionadas con el servidor SMTP en el archivo .env. A continuación, se presenta un ejemplo de configuración:

```bash
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.tu-servidor.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=tu-correo@dominio.com
   EMAIL_HOST_PASSWORD=tu-contraseña
   DEFAULT_FROM_EMAIL="Tu Proyecto <tu-correo@dominio.com>"
```

---

## **Estructura:**

```bash
   api/
   ├── management/
   │   ├── __init__.py          # Archivo vacío
   │   ├── commands/
   │   │   ├── __init__.py      # Archivo vacío
   │   │   ├── actualizar_cuotas.py  # Archivo del comando
```

## *🔧 Estructura del Código*

Utilidad para el Envío de Correos (utils.py)
El módulo utils.py incluye la función enviar_correo, encargada de gestionar el envío de correos electrónicos.

---

## Comando de Prueba para Enviar Correos (prueba_email.py)

Se ha creado un comando de Django para probar el envío de correos electrónicos con contenido HTML

## **🛠 Cómo Ejecutar la Prueba**

Para probar el envío de correos electrónicos, ejecuta el siguiente comando en tu terminal:

```bash
   python manage.py prueba_email
```

Si la configuración es correcta, deberías recibir un correo con el contenido en formato HTML.

---

### **Automatización**

Este comando se puede automatizar utilizando un cron job (Linux) o el programador de tareas de Windows para ejecutarlo a intervalos regulares, garantizando que las cuotas y notificaciones se actualicen automáticamente sin intervención manual.

Ejemplo de configuración en crontab (Linux):

```bash
0 0 * * * /ruta/a/tu/python /ruta/a/tu/proyecto/manage.py actualizar_cuotas
```

## **Instalación y Configuración**

1. Clonar este repositorio:

   ```bash
     git clone <URL_DEL_REPOSITORIO>
     cd API_COMPRAS
   ```

2. Crear y activar un entorno virtual:

   ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   ```

3. Instalar las dependencias:

   ```bash
     pip install -r requirements.txt
   ```

4. Realizar las migraciones:

     ```bash
     python manage.py makemigrations
     python manage.py migrate
     ```

5. Ejecutar el servidor de desarrollo:

     ```bash
     python manage.py runserver
     ```

---

## **💪🏼Creado Por...**

Natali Ulla Guillermo Enrique.

- [Github](https://github.com/guille-nat)
- [Portfolio](https://nataliullacoder.com/)
- Correo: <guillermonatali22@gmail.com>
