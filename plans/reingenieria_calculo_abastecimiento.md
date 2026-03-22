# Plan de Implementación: Reingeniería de la Fórmula de Abastecimiento

Este plan detalla la corrección de la lógica de cálculo en `AbastecimientoService` para asegurar que el ajuste de los parámetros (`dias_stock`, `umbral_quiebre`, `dias_analisis_ventas`) sea predecible y cumpla con la visión del usuario.

## 1. El Problema Actual
Actualmente, el parámetro `dias_stock` se usa como **Meta** (multiplicador de stock) y como **Ventana** (periodo de análisis). Al aumentar la meta, se amplía el periodo de análisis, lo que diluye el promedio de ventas diarias. El resultado es que la sugerencia final no aumenta como se espera.

## 2. Nueva Arquitectura del Cálculo

### A. La Ventana de Análisis (El "Retrovisor")
Se usará un periodo de análisis fijo para calcular el `promedio_diario`.
- Se priorizará `dias_analisis_ventas` de la base de datos (Ej: 90 días).
- Si no está configurado, usaremos un estándar de **90 días**.
- El `promedio_diario` será estable: `ventas_90_dias / 90`.

### B. El Gatillo (¿Cuándo pedir?) - `umbral_quiebre`
Se usará como barrera de entrada para la sugerencia.
- **Cálculo de Cobertura:** `stock_actual / promedio_diario`.
- **Condición:** Solo si `cobertura < umbral_quiebre` (Ej: 15 días), se genera la sugerencia.
- **Caso 0:** Si `stock_actual == 0`, la cobertura es 0, por lo que el gatillo **siempre se dispara**.

### C. La Meta (¿Cuánto pedir?) - `dias_stock`
Será el multiplicador para el `stock_ideal`.
- **Fórmula:** `promedio_diario * dias_stock * 1.25 * 1.15`.
- **Sugerencia:** `stock_ideal - stock_actual`.
- **Resultado Esperado:** Si el usuario sube `dias_stock` de 30 a 60, la sugerencia **se duplicará**, ya que el `promedio_diario` ahora es independiente y estable.

## 3. Lógica de "Resurrección" para Productos en 0
Si un producto tiene `stock_actual == 0` y no tiene ventas en los últimos 90 días:
- El sistema buscará un historial más amplio (ej. 365 días).
- Si aun así es 0, pero el producto es "Rojo" (Prioritario), se sugerirá un **Stock Mínimo Base** (Ej: 1 unidad o basado en un parámetro de seguridad).

## 4. Cambios en el Código (`pal/services/abastecimiento.py`)

1.  Modificar `calcular_sugerencias` y `calcular_abastecimiento_global`.
2.  Eliminar la "Lógica de Cascada" que variaba según el `dias_obj`.
3.  Implementar el cálculo de `promedio_diario` usando una ventana de tiempo fija extraída de los parámetros.

## 5. Verificación
- **Escenario 1:** Sede con 30 días de stock objetivo -> Sugerencia X.
- **Escenario 2:** Cambiar a 60 días de stock objetivo -> Sugerencia debe ser aproximadamente 2X.
- **Escenario 3:** Producto con 20 días de stock y `umbral_quiebre` de 10 -> Sugerencia debe ser 0.
- **Escenario 4:** Producto con 20 días de stock y `umbral_quiebre` de 25 -> Sugerencia debe activarse.

---
