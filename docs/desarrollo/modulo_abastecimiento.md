# Módulo LOGÍSTICA - Abastecimiento entre Sucursales

> **Nota**: Este módulo forma parte del sistema de LOGÍSTICA.

## Submódulos del Módulo LOGÍSTICA

| # | Submódulo | Estado | Descripción |
|---|-----------|--------|-------------|
| 1 | **Abastecimiento** | 🔄 En desarrollo | Transferencia CDT → Sucursales |
| 2 | **Autorizaciones** | 🔄 En desarrollo | Transferencias Sede→Sede (requieren autorización) |

> **Estructura de Abastecimiento entre Sucursales**:
> - Pestaña "Sugerencias CDT" - Transferencias sugeridas desde CDT (sin autorización)
> - Pestaña "Transferencias Sede→Sede" - Transferencias entre sedes (requieren autorización)
> - Pestaña "Autorizaciones" - Detalles de transferencias pendientes por autorizar

> **Historial**: Este módulo fue iniciado previamente pero se hizo rollback. La migración `desuso/010_agregar_modulo_logistica.sql` existe como referencia pero NO se ejecutó en BD.

---

## Visión General

Sistema de transferencia de mercancía entre sedes/sucursales desde un Centro de Distribución (CDT), con lógica de distribución proporcional, y autorización de supervisor.

---

## Fase 1: Arquitectura y Configuración Base

### 1.1 Definición de Centros de Distribución
- [ ] **Módulo LOGISTICA**: Registrar en BD (migración nueva)
- [ ] **Permiso base**: `logistica.ver`
- [ ] **Agregar permisos granulares**:
  - [ ] `abastecimiento.ver` - Ver módulo de abastecimiento
  - [ ] `abastecimiento.generar` - Generar sugerencias de transferencia
  - [ ] `abastecimiento.autorizar` - Autorizar transferencias entre sedes
  - [ ] `abastecimiento.exportar` - Exportar reportes a Excel
  - [ ] `abastecimiento.configurar` - Configurar parámetros de días de stock
- [ ] **Roles de autorización**:
  - [ ] `Gerente Logistica` - Puede autorizar transferencias Sede→Sede
  - [ ] `Subgerente Logistica` - Puede autorizar transferencias Sede→Sede

### 1.2 Configuración de Sedes (YA EXISTE)
> La configuración de sedes ya existe en Admin > Sedes_Almacenes. Ver `pal_global_settings` (setting_key = "sedes_config").

- [ ] **Agregar campo CDT**: Agregar campo `es_cdt: boolean` al JSON de configuración de sedes
- [ ] **Actualizar UI**: Agregar checkbox "Es Centro de Distribución" en `pal/ui/tabs/sedes_config.py`

### 1.3 Variables de Criterios de Stock
- [ ] **Período de análisis**: Días desde última fecha de liquidación (configurable por producto/categoría)
- [ ] **Cálculo de promedio**: `(ventas_período / días_período)` = promedio ventas diarias
- [ ] **Días de stock objetivo**: Variable configurable (ej: 7, 14, 30 días)
- [ ] **Fórmula**: `stock_necesario = promedio_diario * días_deseados`
- [ ] **Tabla**: `parametros_abastecimiento` (días_por_defecto, días_por_categoria, etc.)

### 1.4 Almacenes "Vendibles" por Sucursal (YA EXISTE)
> La configuración de almacenes por sede ya existe en Admin > Sedes_Almacenes. Los almacenes "tratables" se configuran en cada sede y representan los depósitos que cuentan como stock disponible para venta.

- [ ] **Verificar**: Confirmar que `almacenes_tratables` en el JSON de sedes_config cumple con la función de almacenes "vendibles"

---

## Fase 2: Motor de Cálculo de Abastecimiento

### 2.1 Algoritmo de Sugerencia de Transferencia
- [ ] **Entrada**: Sucursal destino, código de producto, días de stock deseados
- [ ] **Paso 1**: Calcular stock actual en almacenes vendibles de la sucursal
- [ ] **Paso 2**: Calcular promedio de ventas diarias desde última liquidación
- [ ] **Paso 3**: Determinar stock necesario = `promedio * días_deseados`
- [ ] **Paso 4**: Si `stock_actual < stock_necesario`, calcular déficit
- [ ] **Paso 5**: Buscar stock disponible en CDT u otras sucursales

### 2.2 Control de Stock Comprometido
- [ ] **Registro de compromisos**: Tabla `compromisos_stock` (producto_id, sucursal_origen, sucursal_destino, cantidad, fecha, estado)
- [ ] **Cálculo de disponible**: `stock_físico - compromisos_pendientes = disponible_real`
- [ ] **Lógica de "ya comprometido"**: El sistema debe conocer cuánto ya está asignado a la sucursal analizada
- [ ] **Mostrar disponible**: UI debe indicar qué cantidad queda libre para otras sucursales

### 2.3 Distribución Proporcional (Overflow)

> **Caso**: Cuando el CDT no tiene suficiente stock para satisfacer toda la demanda de las sedes.

- [ ] **Detectar overflow**: Si `sum(demandas_sedes) > disponible_en_CDT`
- [ ] **Calcular peso de cada sede**:
  - [ ] Obtener promedio de ventas diarias de cada sede desde última liquidación
  - [ ] Calcular peso porcentual: `peso_sede = ventas_sede / sum(ventas_todas_sedes)`
  - [ ] Ejemplo: Barinas vende 50/día, Cabudare 80/día, Guanare 20/día → Total 150
    - Barinas: 50/150 = 33%
    - Cabudare: 80/150 = 53%
    - Guanare: 20/150 = 14%
- [ ] **Aplicar distribución**: Asignar a cada sede el % disponible según su peso
  - [ ] Si CDT tiene 100 unidades disponibles:
    - Barinas: 33 unidades
    - Cabudare: 53 unidades
    - Guanare: 14 unidades
- [ ] **Registrar truncamiento**: Guardar nota de que la solicitud fue ajustada y por qué

---

## Flujo de Autorizaciones

> **Nota**: El **Centro de Notificaciones** existente se utiliza para organizar este flujo.

| Tipo de Transferencia | Requiere Autorización | Roles que pueden autorizar |
|---------------------|----------------------|---------------------------|
| **CDT → Sucursal** | ❌ No (solo sugerencia) | N/A |
| **Sucursal → Sucursal** | ✅ Sí (obligatoria) | Gerente de Logística o Subgerente de Logística |

### Reglas de Notificación y Autorización

- [ ] **Notificaciones**: Se envían a AMBOS roles (Gerente y Subgerente de Logística)
- [ ] **Popup de alertas pendientes (URGENTE)**:
  - [ ] **Al iniciar sesión**: Verificar si hay transferencias pendientes por autorizar
  - [ ] **Si existen**: Mostrar popup emergente inmediatamente: "⚠️ Transferencias Pendientes por Autorizar"
  - [ ] El popup debe mostrar:
    - Lista de transferencias pendientes (sucursal origen → destino, producto, cantidad)
    - Botón "Autorizar" que redirija al submódulo de autorizaciones
    - Botón "Cerrar" para minimizar (la notificación queda como leída)
  - [ ] Al hacer clic en "Autorizar": cerrar popup y abrir el submódulo de autorizaciones con los detalles de la transferencia
  - [ ] Si no hay pendientes, no mostrar popup
- [ ] **Estado "pendiente"**: Cuando se crea una solicitud entre sedes
- [ ] **Prevención de doble autorización**:
  - [ ] Al crear la solicitud, se marca con estado "pendiente"
  - [ ] Cuando un usuario con rol autorizado hace clic en "Autorizar":
    1. Verificar estado actual de la solicitud
    2. Si ya está "aprobada", mostrar mensaje: "Esta solicitud ya fue autorizada por [usuario]" y bloquear acción
    3. Si está "pendiente", cambiar a "aprobada", registrar usuario, fecha y hora exactas
  - [ ] **Transacción atómica**: Usar bloqueos o transacciones para evitar race conditions
- [ ] **Log de auditoría**: Registrar quién autorizó y cuándo

### Validación de Órdenes de Compra (ODC)

- [ ] **Verificar ODC activas**: Al sugerir transferencia, buscar si el producto tiene ODC vigente hacia la sucursal destino.
  - **Estructura de Datos ODC**:
    - `MA_ODC`: Cabeceras de ODC. Campos clave: `c_DOCUMENTO` (PK), `d_fecha`, `c_status`, `c_CODLOCALIDAD`.
    - `TR_ODC`: Detalle de productos. Campos: `c_DOCUMENTO` (FK), `c_CODARTICULO`, `n_cantidad` (cantidad ordenada).
  - **Lógica Propuesta**:
    1. Seleccionar todas las ODC con `c_status = 'DPE'` (pendientes).
    2. Para cada una, obtener sus productos desde `TR_ODC` mediante `c_DOCUMENTO`.
    3. Enriquecer cada producto obtenido (descripciones, etc.) usando la lógica de `database.py`.
- [ ] **Si existe ODC activa**:
  - [ ] Mostrar advertencia clara: "⚠️ ADVERTENCIA: Ya existe una ODC activa para este producto"
  - [ ] La sugerencia cambia a "No transferir" o similar
  - [ ] Color diferente en la UI (naranja/amarillo)
- [ ] **Flujo de autorización**:
  - [ ] Si usuario NO tiene permiso `abastecimiento.autorizar`:
    - [ ] Mostrar botón "Solicitar Autorización"
    - [ ] Crear solicitud de autorización
  - [ ] Si usuario SÍ tiene permiso `abastecimiento.autorizar`:
    - [ ] Mostrar botón "Forzar Transferencia"
- [ ] **Integración**: Consumir datos del módulo de compras existente (tablas `MA_ODC` y `TR_ODC`).

### Validación de Productos "ROJOS" (Inviables para Traslado)

> Productos que por su naturaleza (fragilidad, costo, regulación, etc.) no deben transferirse entre sedes específicas.

- [ ] **Lista de productos ROJOS por sede**: La prohibición es **origin → destino**, no global
  - Ejemplo: Producto X puede transferirse de CDT → Barinas, pero NO de CDT → Cabudare
  - Ejemplo: Producto Y puede transferirse de Sede A → Sede B, pero NO de Sede B → Sede A
- [ ] **Tabla propuesta**: `productos_no_trasladables`
  ```sql
  CREATE TABLE productos_no_trasladables (
      id INT IDENTITY(1,1) PRIMARY KEY,
      producto_codigo NVARCHAR(15) NOT NULL,
      sede_origen NVARCHAR(50), -- NULL = todas las sedes origen
      sede_destino NVARCHAR(50) NOT NULL,
      motivo NVARCHAR(255) NOT NULL,
      fecha_agregado DATETIME DEFAULT GETDATE(),
      usuario_agrega INT,
      activo BIT DEFAULT 1
  );
  ```
- [ ] **UI de gestión**: Sección en configuración para agregar/eliminar productos de la lista ROJA
  - [ ] Selector de producto
  - [ ] Selector de sede origen (opcional, si se deja vacío aplica a todas)
  - [ ] Selector de sede destino (obligatorio)
  - [ ] Campo de motivo
- [ ] **En sugerencia de transferencia**:
  - [ ] Verificar si el producto está en lista ROJA para esa sede origen → destino
  - [ ] Si está en lista: mostrar advertencia "⚠️ PRODUCTO NO TRASLADABLE - [motivo]"
  - [ ] Mostrar color diferente en la UI (rojo)
  - [ ] Por defecto NO permitir transferencia
- [ ] **Flujo de autorización para productos ROJOS**:
  - [ ] Si usuario NO tiene permiso `abastecimiento.autorizar`:
    - [ ] Mostrar botón "Solicitar Autorización"
    - [ ] Crear solicitud de autorización (igual que transferencias Sede→Sede)
    - [ ] Notificar a Gerente/Subgerente de Logística
  - [ ] Si usuario SÍ tiene permiso `abastecimiento.autorizar`:
    - [ ] Mostrar botón "Forzar Transferencia"
    - [ ] Al hacer clic: registrar en auditoría quién forzó, motivo, fecha
    - [ ] La transferencia se procesa normalmente pero marcada como "forzada"

---

## Fase 4: Interfaz de Usuario y Reportes

### 4.1 Dashboard de Abastecimiento
- [ ] **Resumen por sucursal**: Stock actual vs necesario, déficit total
- [ ] **Alertas**: Productos bajo umbral de días de stock
- [ ] **Gráficos**: Distribución de transferencias sugeridas por sucursal

### 4.2 Filtros Avanzados
- [ ] **Por departamento**
- [ ] **Por grupo**
- [ ] **Por subgrupo**
- [ ] **Por marca**
- [ ] **Por proveedor**
- [ ] **Por sucursal origen/destino**
- [ ] **Rango de fechas (última liquidación)**

### 4.3 Exportación a Excel
- [ ] **Botón exportar**: Generar archivo .xlsx
- [ ] **Columnas**: Producto, SKU, Descripción, Stock Actual, Stock Necesario, Déficit, Sugerencia Origen, Cantidad Sugerida
- [ ] **Hojas múltiples**: Una hoja por sucursal destino, o resumen consolidado
- [ ] **Aplicar filtros activos**: El Excel respeta los filtros seleccionados en UI

---

## Fase 5: Integración con Módulos Existentes

### 5.1 Inventario (Stock)
> **Importante**: El módulo `stock.py` genera alertas de **quiebres de stock** para productos de alta/media rotación. NO proporciona stock general.

- [ ] **Datos de stock**: Consumir directamente de tabla `MA_DEPOPROD` (c_codarticulo, c_coddeposito, n_cantidad)
- [ ] **Alertas de stock**: Usar `stock.py` para mostrar productos en quiebre en la UI

### 5.2 Ventas
- [ ] **Fuente de datos**: Tabla `TR_INVENTARIO` (contiene movimientos de inventario/ventas)
- [ ] **Última Liquidación**: Tabla `MA_HISTORICO_COSTO_PRECIO`
  - Campo: `d_fechaCambio` = fecha de última liquidación
  - Filtro: `c_procesoOrigen = 'REGISTRO DE FACTURA'` (indica que el producto se liquidó)
  - Campo clave: `c_codarticulo` = código del producto
- [ ] **Cálculo de promedio**: `(ventas_período / días_período)` = promedio ventas diarias
- [ ] **Período**: Desde `d_fechaCambio` hasta fecha actual
- [ ] **Consultas existentes**: Usar métodos como `obtener_ventas_persisted_tra()` o `obtener_ventas_por_producto_chunk()`

### 5.3 Órdenes de Compra
- [ ] Integrar con módulo de compras (ODC) usando tablas `MA_ODC` y `TR_ODC`.
- [ ] Verificar estado ODC (`c_status = 'DPE'`).
- [ ] Usar `database.py`: `obtener_tipo_articulo(codigo)` para obtener el tipo del artículo durante el enriquecimiento de datos.

### 5.4 Notifications
- [ ] Notificar a supervisor cuando haya solicitudes pendientes de autorización
- [ ] Notificar a analistas cuando haya nuevas sugerencias de transferencia

---

## Fase 6: Base de Datos

### 6.1 Configuración de Sedes (YA EXISTE)

> **Importante**: La configuración de sedes ya existe en `pal_global_settings` (setting_key = "sedes_config") en formato JSON. NO crear nueva tabla.

**Estructura actual**:
```json
{
    "nombre_sede": {
        "descripcion": "",
        "zona": "",
        "almacenes_tratables": []
    }
}
```

**Lo que hay que agregar**:
- [ ] Campo `es_cdt: boolean` al JSON de cada sede
- [ ] Actualizar UI en `pal/ui/tabs/sedes_config.py` para mostrar checkbox "Es Centro de Distribución"

### 6.2 Tablas Nuevas

```sql
-- Parámetros de abastecimiento (días de stock por categoría)
CREATE TABLE parametros_abastecimiento (
    id INT IDENTITY(1,1) PRIMARY KEY,
    categoria_id INT,
    dias_stock INT DEFAULT 7,
    fecha_actualizacion DATETIME DEFAULT GETDATE()
);

-- Compromisos de stock (ya comprometido para transferencia)
CREATE TABLE compromisos_stock (
    id INT IDENTITY(1,1) PRIMARY KEY,
    producto_id INT,
    sucursal_origen INT,
    sucursal_destino INT,
    cantidad DECIMAL(10,2),
    fecha_compromiso DATETIME DEFAULT GETDATE(),
    estado NVARCHAR(20) DEFAULT 'pendiente' -- pendiente, confirmado, cancelado
);

-- Auditoría de autorizaciones
CREATE TABLE auditoria_autorizaciones (
    id INT IDENTITY(1,1) PRIMARY KEY,
    usuario_id INT,
    producto_id INT,
    sucursal_origen INT,
    sucursal_destino INT,
    cantidad_original DECIMAL(10,2),
    cantidad_autorizada DECIMAL(10,2),
    motivo TEXT,
    fecha_autorizacion DATETIME DEFAULT GETDATE()
);

-- Sugerencias de transferencia
CREATE TABLE sugerencias_transferencia (
    id INT IDENTITY(1,1) PRIMARY KEY,
    producto_id INT,
    sucursal_destino INT,
    sucursal_origen_sugerida INT,
    cantidad_sugerida DECIMAL(10,2),
    cantidad_disponible DECIMAL(10,2),
    dias_stock_actual INT,
    dias_stock_necesario INT,
    tiene_odc_activa BIT DEFAULT 0,
    es_producto_rojo BIT DEFAULT 0,
    tipo_solicitud NVARCHAR(20) DEFAULT 'normal', -- normal, odc, producto_rojo
    requiere_autorizacion BIT DEFAULT 0,
    fue_autorizada BIT DEFAULT 0,
    usuario_autoriza INT,
    fecha_autorizacion DATETIME,
    fecha_generacion DATETIME DEFAULT GETDATE(),
    estado NVARCHAR(20) DEFAULT 'pendiente' -- pendiente, aprobada, rechazada, exportada
);

-- Productos no trasladables (Lista ROJA) - Por sede origen → destino
CREATE TABLE productos_no_trasladables (
    id INT IDENTITY(1,1) PRIMARY KEY,
    producto_codigo NVARCHAR(15) NOT NULL,
    sede_origen NVARCHAR(50), -- NULL = todas las sedes origen
    sede_destino NVARCHAR(50) NOT NULL,
    motivo NVARCHAR(255) NOT NULL,
    fecha_agregado DATETIME DEFAULT GETDATE(),
    usuario_agrega INT,
    activo BIT DEFAULT 1
);
);
    cantidad_disponible DECIMAL(10,2),
    dias_stock_actual INT,
    dias_stock_necesario INT,
    tiene_odc_activa BIT DEFAULT 0,
    requiere_autorizacion BIT DEFAULT 0,
    fecha_generacion DATETIME DEFAULT GETDATE(),
    estado NVARCHAR(20) DEFAULT 'pendiente' -- pendiente, aprobada, rechazada, exportada
);
```

### 6.3 Índices
- [ ] `idx_compromisos_producto_sede` ON `compromisos_stock(producto_id, sucursal_destino)`
- [ ] `idx_sugerencias_estado` ON `sugerencias_transferencia(estado, fecha_generacion)`

---

## Fase 7: Permisos

| Permiso | Descripción |
|---------|-------------|
| `ver_modulo_abastecimiento` | Acceder al módulo de abastecimiento |
| `generar_sugerencias` | Ejecutar cálculo de sugerencias |
| `exportar_excel_abastecimiento` | Exportar reportes a Excel |
| `autorizar_transferencia` | Autorizar transferencias especiales |
| `ver_todas_sucursales` | Ver datos de todas las sucursales |
| `configurar_parametros` | Modificar parámetros de días de stock |

---

## Tareas 

### Frontend/UI
- [ ] Crear pestaña "Abastecimiento" en el menú
- [ ] **Carga en tiempo real**: Las sugerencias se cargan automáticamente al acceder al módulo (como STOCK), no con botón
- [ ] Panel de filtros con todos los criterios
- [ ] Tabla de resultados con columnas configurables
- [ ] Gráficos de resumen
- [ ] Botón de exportación Excel
- [ ] Modal de autorización de supervisor

### Backend/Lógica
- [ ] Endpoint de cálculo de sugerencias
- [ ] Lógica de distribución proporcional
- [ ] Integración con ventas (período desde liquidación)
- [ ] Validación de ODC activas
- [ ] Registro de compromisos

### Base de Datos
- [ ] Crear tablas nuevas
- [ ] Crear índices de rendimiento
- [ ] Migrar datos si aplica

### Testing
- [ ] Pruebas unitarias de algoritmo de distribución
- [ ] Pruebas de integración con ODC
- [ ] Pruebas de autorización de supervisor

---

## Notas

- **Período de liquidación**: El sistema debe almacenar la última fecha de liquidación por sucursal para calcular el promedio de ventas correctamente.
- **Múltiples CDT**: La arquitectura debe permitir configurar múltiples CDT si es necesario en el futuro.
- **Tiempo real**: Las sugerencias se calculan en tiempo real al cargar el módulo (igual que STOCK), no es un proceso batch.
 