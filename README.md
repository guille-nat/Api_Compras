# **API_COMPRAS**

API diseñada para la gestión de compras, pagos, cuotas, inventario y usuarios. Este proyecto incluye validaciones robustas y reglas de negocio para asegurar un manejo eficiente y seguro de las operaciones.

## **Características Principales**
- Gestión de productos e inventario.
- Registro de compras con detalles asociados.
- Manejo de cuotas y pagos con descuentos y recargos.
- Notificaciones automáticas para usuarios sobre el estado de sus compras y pagos.

---

## **Reglas de Negocio**

### **Productos e Inventario**
1. **Stock Disponible**: 
   - Antes de procesar una compra, se valida que el stock del producto sea suficiente.
   - Si el stock no es suficiente, se rechaza la compra con un mensaje detallado.

2. **Actualización de Stock**:
   - Al procesar una compra, el stock del producto se reduce según la cantidad adquirida.

---

### **Compras**
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

### **Pagos y Cuotas**
1. **Descuento por Pronto Pago**:
   - Si una cuota es pagada antes de su fecha de vencimiento, se aplica un descuento adicional del **15%** al monto de la cuota.

2. **Recargo por Pago Tardío**:
   - Si una cuota no se paga dentro del plazo de 30 días desde su emisión, se aplica un recargo del **20%** sobre el monto de la cuota.

3. **Cálculo de Montos en Cuotas**:
   - En compras con más de 6 cuotas, se aplica un incremento del **15%** en el monto de cada cuota.

---

## **Documentación de los Endpoints**
La documentación de los endpoints está disponible en los siguientes enlaces:
- **Swagger UI**: [localhost:8000/doc](http://localhost:8000/doc)
- **ReDoc**: [localhost:8000/redoc](http://localhost:8000/redoc)

Ambos proporcionan una descripción completa de los endpoints disponibles, métodos permitidos, parámetros requeridos y ejemplos de respuestas.

---

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
## **Creado Por...**
Natali Ulla Guillermo Enrique. 
- [Github](https://github.com/guille-nat), 
- [Portfolio](https://nataliullacoder.com/)
- Correo: guillermonatali22@gmail.com

  
