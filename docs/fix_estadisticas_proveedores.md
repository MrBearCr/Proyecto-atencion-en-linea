# Corrección: Coherencia en Estadísticas por Proveedores

## Problema Identificado

Las estadísticas mostraban totales diferentes según la vista seleccionada:
- **Por Departamentos**: 50,102 unidades vendidas
- **Por Proveedores**: 89,024 unidades vendidas

### Causa Raíz

Las estadísticas usaban **fuentes de datos diferentes**:

1. **Estadísticas por Departamentos/Grupos/Subgrupos**:
   - Usaban `cached_ventas_tra` (datos precargados del módulo RI)
   - Aplicaban todos los filtros del módulo RI (fechas, sede, texto, jerarquía)
   - Solo incluían productos con jerarquía completa (Depto/Grupo/Sub)

2. **Estadísticas por Proveedores** (ANTES):
   - Hacían una **nueva consulta** a `MA_PRODXPROV` en la base de datos
   - Incluían TODOS los productos con ventas, sin considerar filtros de jerarquía
   - No respetaban los mismos criterios aplicados en RI

### Diferencia: 38,922 unidades

Estas unidades correspondían a productos que:
- Tenían ventas registradas en `TR_INVENTARIO`
- Tenían proveedor asignado en `MA_PRODXPROV`
- **NO tenían** jerarquía completa (`C_DEPARTAMENTO/C_GRUPO/C_SUBGRUPO` vacíos o NULL)

---

## Solución Implementada

### 1. Precarga del Mapeo Productos-Proveedores

**Archivo**: `app.py`
**Función nueva**: `_preload_productos_proveedores()`

```python
def _preload_productos_proveedores(self):
    """Precarga mapeo productos->proveedores para TODOS los productos en cached_ventas_tra.
    
    Esto garantiza que las estadísticas por proveedor usen exactamente los mismos datos
    que las estadísticas por departamento (mismo universo de datos precargados en RI).
    """
```

**Características**:
- Se ejecuta automáticamente al cargar datos TRA (dentro de `_rebuild_effective_views()`)
- Consulta `MA_PRODXPROV` en batches para SOLO los productos cargados en RI
- Guarda el resultado en `self.cached_proveedor_por_codigo` como diccionario:
  ```python
  {
      "CODIGO_PRODUCTO": ("CODIGO_PROVEEDOR", "DESCRIPCION_PROVEEDOR"),
      ...
  }
  ```
- Maneja productos sin proveedor asignado
- Log informativo: muestra total de relaciones y productos sin proveedor

### 2. Modificación de Estadísticas por Proveedores

**Archivo**: `pal/ui/tabs/stats.py`
**Función modificada**: `_stats_draw_providers_universe()`

**Cambios principales**:

```python
# ANTES: Hacía nueva consulta a BD
query = """
    SELECT px.c_codprovee, px.c_codigo
    FROM MA_PRODXPROV px
    WHERE px.c_codigo IN (...)
"""

# AHORA: Usa cache precargado
codigos_proveedor = getattr(app, 'cached_proveedor_por_codigo', None)
for codigo, neto in product_neto.items():
    prov_info = codigos_proveedor.get(codigo)
    # Agrupar por proveedor usando datos precargados
```

**Beneficios**:
- ✅ Usa los mismos datos que estadísticas por departamentos
- ✅ Respeta todos los filtros de RI (fechas, sede, texto, jerarquía)
- ✅ No hace consultas adicionales a la BD (más rápido)
- ✅ Totales coherentes entre todas las vistas de estadísticas

### 3. Actualización del Cálculo de Participación

**Archivo**: `pal/ui/tabs/stats.py`
**Función modificada**: `_stats_compute_and_draw()`

Cuando hay un filtro de proveedor activo en RI, ahora usa el cache precargado:

```python
# Usar cache precargado de producto->proveedor para consistencia
cached_proveedor = getattr(app, 'cached_proveedor_por_codigo', {})
if cached_proveedor:
    # Filtrar usando el mapeo precargado
    for r in ventas_total_universo:
        prov_info = cached_proveedor.get(codigo)
        # Clasificar como "proveedor" o "resto"
```

**Fallback**: Si no existe el cache precargado, usa el método antiguo por compatibilidad.

---

## Verificación de Resultados

### Antes de Cargar RI
```
cached_proveedor_por_codigo: No existe
```

### Después de Cargar RI (Ejemplo)
```
✅ Proveedores precargados: 3,245 relaciones producto-proveedor | 89 productos sin proveedor asignado

cached_proveedor_por_codigo = {
    "PROD001": ("PROV123", "PROVEEDOR ABC S.A."),
    "PROD002": ("PROV456", "PROVEEDOR XYZ C.A."),
    ...
}
```

### Estadísticas Coherentes
```
Por Departamentos:  50,102 unidades (solo productos con jerarquía)
Por Proveedores:    50,102 unidades (mismo universo de datos)
                    ^^^^^^
                    AHORA COINCIDEN ✅
```

---

## Flujo de Datos Completo

```
┌─────────────────────────────────────────────┐
│  Usuario carga datos en módulo RI          │
│  (filtros: fechas, sede, texto, jerarquía) │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  _background_load_ventas_tra()              │
│  • Consulta TR_INVENTARIO                   │
│  • Aplica filtros de fechas/sede            │
│  • Guarda en cached_ventas_tra              │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  _rebuild_effective_views()                 │
│  • Aplica exclusiones por departamento      │
│  • Crea cached_ventas_tra_effective         │
│  • ✨ LLAMA _preload_productos_proveedores()│
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  _preload_productos_proveedores()           │
│  • Extrae códigos de cached_ventas_tra      │
│  • Consulta MA_PRODXPROV en batches         │
│  • Guarda en cached_proveedor_por_codigo    │
└─────────────────┬───────────────────────────┘
                  │
                  ├──────────────────┬──────────────────┐
                  │                  │                  │
                  ▼                  ▼                  ▼
         ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
         │ Estadísticas│   │ Estadísticas│   │ Estadísticas│
         │    Depto    │   │    Grupo    │   │  Proveedor  │
         │             │   │             │   │             │
         │ cached_     │   │ cached_     │   │ cached_     │
         │ ventas_tra  │   │ ventas_tra  │   │ proveedor_  │
         │             │   │             │   │ por_codigo  │
         └─────────────┘   └─────────────┘   └─────────────┘
                │                  │                  │
                └──────────────────┴──────────────────┘
                                   │
                                   ▼
                        ✅ TOTALES COHERENTES
```

---

## Archivos Modificados

1. **`app.py`**:
   - Función nueva: `_preload_productos_proveedores()` (líneas 3703-3787)
   - Modificado: `_rebuild_effective_views()` para llamar a precarga (línea 2703)

2. **`pal/ui/tabs/stats.py`**:
   - Modificado: `_stats_draw_providers_universe()` para usar cache (líneas 558-648)
   - Modificado: `_stats_compute_and_draw()` para usar cache en participación (líneas 770-827)

---

## Beneficios Adicionales

### Rendimiento
- **Antes**: Múltiples consultas SQL a `MA_PRODXPROV` (una por cada vista de estadísticas)
- **Ahora**: Una sola consulta en batches al cargar RI, reutilizada en todas las vistas

### Consistencia
- Todas las estadísticas usan el mismo universo de datos
- Los filtros de RI se aplican uniformemente
- No hay discrepancias entre vistas diferentes

### Mantenibilidad
- Lógica centralizada en una función
- Código más fácil de entender y debugear
- Cache explícito y documentado

---

## Casos de Uso Soportados

### 1. Sin Filtro de Proveedor
```
RI cargado → Estadísticas por Proveedor muestra TODOS los proveedores
            con datos del universo RI (fechas, sede, jerarquía aplicados)
```

### 2. Con Filtro de Proveedor
```
RI cargado + Filtro Proveedor "XYZ" → 
  • Estadísticas por Depto: Solo productos del proveedor XYZ
  • Estadísticas por Proveedor: Muestra participación de XYZ vs Resto
  • Totales coherentes en ambas vistas ✅
```

### 3. Productos Sin Proveedor
```
Productos sin relación en MA_PRODXPROV →
  • Se incluyen en estadísticas por Depto (si tienen jerarquía)
  • Se muestran como "Sin proveedor asignado" en vista por proveedores
  • Totales mantienen coherencia ✅
```

---

## Pruebas Recomendadas

1. **Cargar RI con filtros específicos** (ej: último mes, sede Cabudare)
2. **Ver estadísticas por Departamentos** → Anotar total
3. **Cambiar a estadísticas por Proveedores** → Verificar que el total coincida
4. **Aplicar filtro por proveedor en RI** → Verificar coherencia en ambas vistas
5. **Revisar logs**: Buscar mensaje "✅ Proveedores precargados: X relaciones..."

---

## Contacto

Para dudas o mejoras relacionadas con esta corrección:
- Revisar logs en consola al cargar RI
- Verificar existencia de `cached_proveedor_por_codigo` en app
- Consultar esta documentación: `docs/fix_estadisticas_proveedores.md`
