# Plan de Implementación: Recepciones Parciales de Transferencias (TRS -> REC)

Este plan detalla la implementación de la lógica para soportar recepciones parciales de mercancía asociada a una Orden de Transferencia (`TRS`). El objetivo es permitir que una transferencia pueda ser recibida en múltiples entregas, generando un correlativo `REC-xxxxxx` único por cada recepción.

## 1. Cambios en Base de Datos (Schema)

Se crearán nuevas tablas para registrar las recepciones y se modificarán las existentes para rastrear el progreso.

### Nuevas Tablas

#### `pal_recepciones_maestro`
Cabecera de cada evento de recepción física.
- `id` (PK, INT IDENTITY)
- `numero_recepcion` (NVARCHAR 20, UNIQUE, NOT NULL) -> Ej: `REC-000001`
- `transferencia_id` (INT, FK -> `pal_transferencias_maestro.id`)
- `fecha_recepcion` (DATETIME, DEFAULT GETDATE())
- `usuario_recibe` (INT)
- `observaciones` (TEXT, NULL)
- `estado` (NVARCHAR 20, DEFAULT 'completada') -> Por si se requiere anular una recepción.

#### `pal_recepciones_detalle`
Detalle de los productos recibidos en un evento específico.
- `id` (PK, INT IDENTITY)
- `recepcion_id` (INT, FK -> `pal_recepciones_maestro.id`)
- `sugerencia_id` (INT, FK -> `pal_sugerencias_transferencia.id`) -> Vincula con el item original de la TRS.
- `cantidad_recibida` (DECIMAL 18,2, NOT NULL)

### Modificaciones en Tablas Existentes

#### `pal_sugerencias_transferencia` (Items de la TRS)
- Agregar `cantidad_recibida_total` (DECIMAL 18,2, DEFAULT 0)
    - *Propósito:* Saber cuánto se ha recibido acumulado de este item sin tener que sumar todas las recepciones cada vez.
- Agregar `estado_recepcion` (NVARCHAR 20, DEFAULT 'pendiente')
    - Valores: `pendiente`, `parcial`, `completada`.

#### `pal_transferencias_maestro` (Cabecera TRS)
- El estado `recibida` se mantendrá para compatibilidad, pero su lógica cambiará:
    - `en_transito`: Ningún item recibido.
    - `recibida_parcial`: Al menos un item recibido parcialmente.
    - `recibida_total`: Todos los items completados (o cerrados forzosamente).

## 2. Lógica de Negocio (`pal/services/abastecimiento.py`)

Se actualizará la clase `AbastecimientoService` con los siguientes métodos:

1.  **`generar_numero_recepcion()`**:
    - Genera el siguiente correlativo `REC-xxxxxx`.
    
2.  **`registrar_recepcion(transferencia_id, items_recibidos, usuario_id, observaciones)`**:
    - **Input:** `items_recibidos` es una lista de dicts `[{'sugerencia_id': 1, 'cantidad': 20}, ...]`.
    - **Flujo:**
        1.  Validar que las cantidades no excedan lo pendiente (opcional, configurable).
        2.  Crear registro en `pal_recepciones_maestro` (`REC-...`).
        3.  Para cada item:
            - Insertar en `pal_recepciones_detalle`.
            - Actualizar `pal_sugerencias_transferencia`:
                - `cantidad_recibida_total += cantidad`
                - `estado_recepcion` = `completada` si total >= sugerida, sino `parcial`.
        4.  Evaluar estado global de la Transferencia (`TRS`):
            - Si todos los items están `completada` -> Estado TRS `recibida_total`.
            - Si hay items pendientes -> Estado TRS `recibida_parcial`.

## 3. Estrategia de Migración

1.  Crear un script de migración SQL (`docs/migrations/012_crear_tablas_recepciones.sql`) que:
    - Cree las nuevas tablas.
    - Agregue las columnas a las tablas existentes.
    - (Opcional) Migre datos antiguos si existen transferencias marcadas como `recibida` (asumir recepción total).

## 4. Verificación

- **Test Unitario:** Crear un test que simule el flujo completo:
    1.  Crear TRS con 2 productos (Cant: 50, 50).
    2.  Registrar Recepción 1 (Parcial): Prod A (20), Prod B (0).
        - Verificar estados: TRS (`recibida_parcial`), Item A (`parcial`), Item B (`pendiente`).
        - Verificar saldo: Item A (30 pendientes).
    3.  Registrar Recepción 2 (Final): Prod A (30), Prod B (50).
        - Verificar estados: TRS (`recibida_total`), Items (`completada`).

---
