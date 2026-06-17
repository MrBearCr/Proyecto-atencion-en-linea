# Plan de Implementación: Trazabilidad y Productos Perecederos

Este plan detalla la implementación de un sistema de trazabilidad para manejar productos que requieren **Control de Lotes (Interno/Fábrica)** y **Fechas de Vencimiento**.

El objetivo es permitir que al recibir una Transferencia (`TRS`), el usuario pueda desglosar la cantidad recibida en uno o más lotes específicos, generando un registro inmutable de qué unidades entraron al sistema.

## 1. Cambios en Base de Datos (Schema)

Se requiere una nueva tabla para almacenar el detalle granular de cada recepción.

### Nueva Tabla: `pal_recepciones_lotes`
Esta tabla actuará como "hija" de `pal_recepciones_detalle`. Un detalle de recepción (ej: 50 Leches) puede tener múltiples registros en esta tabla (ej: 20 del Lote A, 30 del Lote B).

- `id` (PK, INT IDENTITY)
- `recepcion_detalle_id` (INT, FK -> `pal_recepciones_detalle.id`)
- `lote_interno` (NVARCHAR 50, UNIQUE constraint scope) -> Generado automáticamente o manual.
- `lote_fabrica` (NVARCHAR 50, NULL) -> Dato externo del proveedor.
- `fecha_vencimiento` (DATE, NULL) -> Para perecederos.
- `cantidad` (DECIMAL 18,2, NOT NULL) -> Cantidad específica de este lote.
- `fecha_registro` (DATETIME, DEFAULT GETDATE())

*Nota:* La suma de `cantidad` en esta tabla debe coincidir con `cantidad_recibida` en `pal_recepciones_detalle`.

## 2. Lógica de Negocio (`pal/services/abastecimiento.py`)

Se actualizará `AbastecimientoService` para manejar la complejidad añadida.

### Método `generar_lote_interno(producto_codigo)`
- Genera un código único para identificación interna.
- Formato propuesto: `L-{AAMMDD}-{HHMM}-{ALFANUM}`
- Ejemplo: `L-260321-1430-A1`

### Actualización de `registrar_recepcion`
El método `registrar_recepcion` ya acepta una lista de items. Ahora, cada item podrá contener una lista opcional de `lotes`.

**Estructura de Datos Entrada:**
```json
[
  {
    "sugerencia_id": 101,
    "cantidad": 50,
    "lotes": [
      {
        "lote_fabrica": "LF-999",
        "vencimiento": "2026-12-01",
        "cantidad": 20
      },
      {
        "lote_fabrica": "LF-888",
        "vencimiento": "2027-01-01",
        "cantidad": 30
      }
    ]
  }
]
```

**Flujo:**
1.  Insertar `pal_recepciones_detalle`.
2.  Si el item tiene `lotes`:
    - Validar que `sum(lotes.cantidad) == item.cantidad`.
    - Iterar lotes:
        - Generar `lote_interno` si no viene.
        - Insertar en `pal_recepciones_lotes`.

## 3. Interfaz de Usuario (`pal/ui/tabs/abastecimiento.py`)

La ventana modal de recepción necesita una actualización significativa.

### Modificaciones en `on_cerrar_orden` (Modal de Recepción)
1.  **Nueva Columna:** Agregar columna "Lotes 📝" al Treeview de recepción.
    - Si el producto tiene lotes definidos, mostrar icono "✅".
    - Si no, mostrar icono "⚠️" (si es perecedero) o vacío.
2.  **Botón/Acción:** Doble clic en columna "Lotes" o botón "Gestionar Lotes".
3.  **Sub-Modal "Gestión de Lotes":**
    - Título: "Lotes para {Producto}"
    - Lista actual de lotes ingresados.
    - Formulario:
        - Lote Fábrica (Entry)
        - Vencimiento (DateEntry o Entry YYYY-MM-DD)
        - Cantidad (Entry)
        - Botón "Agregar Lote".
    - Validación: La suma de cantidades debe igualar a la cantidad total a recibir del producto.
    - Botón "Guardar y Cerrar".

## 4. Estrategia de Migración

1.  Crear script SQL `docs/migrations/013_crear_tabla_lotes.sql`.
2.  Actualizar `pal/infrastructure/database.py` para incluir la creación de la tabla.
3.  Implementar lógica en Backend.
4.  Implementar UI.

## 5. Consideraciones Futuras (Out of Scope por ahora)
- **Inventario por Lotes:** Este plan solo cubre la *Recepción*. El sistema actual de inventario (`MA_DEPOPROD`) probablemente no soporta lotes. Para un control total, se necesitaría una tabla paralela de stock por lote (`pal_stock_lotes`) que se incremente con estas recepciones y se decremente con ventas/traslados. *Por ahora, nos limitaremos al registro de entrada (trazabilidad de ingreso).*

---
