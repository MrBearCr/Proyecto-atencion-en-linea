# Filtros Jerárquicos Unificados - Documentación

## Resumen

Se creó un utilitario compartido (`pal/services/filters.py`) para unificar el comportamiento de filtros jerárquicos en los módulos **stock**, **TRA** y **MBRP**. Esto resuelve:

- Implementaciones duplicadas de lógica similar (cada módulo tenía su propio filtrado)
- Inconsistencias en el tratamiento de productos sin jerarquía
- Fallos en la UI cuando la jerarquía no estaba cargada o era parcial

---

## Módulo: `pal/services/filters.py`

### Funciones principales

#### `match_hierarchy_from_map(codigo, jerarquia_map, dept_code, group_code, sub_code, *, missing_strategy)`

Comprueba si un código coincide con filtros jerárquicos usando un **mapa externo** (dict código → (dept, group, sub)).

**Estrategias de faltantes:**
- `"exclude"`: si el código no está en el mapa y hay filtros activos, se excluye
- `"include"`: si el código no está en el mapa y hay filtros activos, se incluye (leniente)

#### `match_hierarchy_from_record(record, dept_code, group_code, sub_code, *, get_dept, get_group, get_sub, missing_strategy)`

Lee jerarquía **directamente del registro** usando funciones getter (ej: `lambda r: r[2]` para leer el departamento del índice 2).

#### `filter_by_hierarchy(records, dept_code, group_code, sub_code, *, get_code, jerarquia_map, get_dept, get_group, get_sub, missing_strategy)`

Función unificada de alto nivel que aplica el filtro jerárquico sobre una colección.

**Dos modos:**
1. **Jerarquía externa**: pasa `get_code` + `jerarquia_map`
2. **Jerarquía en registro**: pasa `get_dept` + `get_group` + `get_sub`

---

## Cambios por módulo

### Stock (`pal/services/stock.py`)

**Antes:**
- Función helper `_coincide_jerarquia` inline que aplicaba fallback "leniente": productos sin jerarquía no se filtraban aunque hubiera filtros activos.
- Dependía del helper interno en `filter_alertas`.

**Ahora:**
- Eliminado `_coincide_jerarquia`.
- `filter_alertas` usa `filter_by_hierarchy` con:
  - `get_code=lambda r: r[0]`
  - `jerarquia_map=producto_jerarquia`
  - `missing_strategy="include"` (leniente para minimizar pérdida de datos)
- Normalización de códigos y jerarquía al cargar desde BD para evitar mismatch por espacios/tipos.

### TRA (`pal/services/tra.py`)

**Antes:**
- Filtros manuales en cascada: 3 bloques `if` secuenciales (dept, group, sub) con list comprehensions independientes.
- Lógica simple pero verbosa.

**Ahora:**
- `filter_ventas_tra` usa `filter_by_hierarchy` con:
  - `get_dept=lambda r: r[2] if len(r) > 2 else None`
  - `get_group=lambda r: r[3] if len(r) > 3 else None`
  - `get_sub=lambda r: r[4] if len(r) > 4 else None`
  - `missing_strategy="exclude"` (estricto)
- Una sola pasada sobre los datos en lugar de tres.

### MBRP

- Reutiliza `filter_ventas_tra` (y por ende, el filtro unificado).
- Consistente con TRA por diseño.

---

## Estrategia por módulo

| Módulo | Estrategia       | Justificación                                                                 |
|--------|------------------|-------------------------------------------------------------------------------|
| Stock  | `include` (leniente) | Minimiza pérdida de datos al filtrar alertas: mejor mostrar productos sin jerarquía que ocultarlos. |
| TRA    | `exclude` (estricto) | Filtrado más preciso: registros TRA siempre traen dept/group/sub de la consulta, omitir incompletos. |
| MBRP   | `exclude` (estricto) | Misma lógica que TRA. |

Puedes ajustar la estrategia en cualquier módulo cambiando el valor de `missing_strategy` en la llamada a `filter_by_hierarchy`.

---

## Problemas resueltos

### 1. Stock: Jerarquía en 0 y filtrado roto

**Causa:**
- `all_jerarquia` (mapa completo) no se propagaba a `producto_jerarquia` (filtrado a códigos en alerta).
- Lógica de filtro demasiado estricta (`all(fila)`) descartaba productos con campos None.

**Solución:**
- Relajado filtro de carga: incluir productos con código válido aunque dept/group/sub sean None.
- Normalización de códigos y strings (`.strip()`) al cargar y al filtrar.
- Fallback: si `producto_jerarquia` queda vacío pero hay filtros activos, se reconstruye desde `all_jerarquia`.

### 2. TRA/MBRP: Combos siempre en "Todos"

**Causa:**
- Los diccionarios de jerarquías (`tra_dept_dict`, etc.) no se cargaban al abrir la pestaña si la carga unificada fallaba.
- La carga unificada quedaba en 0 elementos por un LEFT JOIN que devolvía filas vacías mal procesadas.

**Solución:**
- Añadido fallback explícito en `cargar_jerarquia_unificada`: si `total_items == 0`, ejecutar `cargar_jerarquia_tra()` y `cargar_jerarquia_mbrp()`.
- En setup de pestañas TRA/MBRP: llamar a `cargar_jerarquia_unificada()` si detectan diccionarios vacíos y hay conexión.

### 3. Filtros no respetados en Stock

**Causa:**
- `aplicar_filtro_stock` podía fallar con `NoneType.get()` si `self.group_dict` no estaba inicializado.
- `producto_jerarquia` vacío → `filter_by_hierarchy` con estrategia `"exclude"` descartaba todo.

**Solución:**
- Hardening de `aplicar_filtro_stock`: usar `getattr(self, 'dept_dict', {}) or {}` para fallback seguro.
- Estrategia `"include"` en Stock.

---

## Testing

### Casos cubiertos

1. **Stock con jerarquía parcial:**
   - Seleccionar Dept → Grupo → Sub: debe refinar progresivamente.
   - Productos sin dept/group/sub aún deben aparecer si estrategia es `"include"`.

2. **TRA/MBRP con jerarquía completa:**
   - Seleccionar Dept → debe filtrar por dept (índice 2).
   - Seleccionar Dept + Group → debe filtrar por ambos.

3. **Productos sin jerarquía:**
   - Stock (leniente): se muestran aunque tengas filtros activos.
   - TRA/MBRP (estricto): se ocultan si no tienen campos dept/group/sub.

### Ejecución manual

```bash
# Reiniciar app
python app.py

# Limpiar cache de jerarquías si es necesario
Remove-Item .\jerarquia_cache.json -Force

# Validar logs:
# - "Jerarquía UNIFICADA ... N elementos" debe ser > 0
# - Al aplicar filtros en Stock: "Filtro jerárquico aplicado - de X a Y"
# - TRA/MBRP: combos de Dept/Group/Sub deben tener opciones
```

---

## Migración y breaking changes

### Breaking changes: **Ninguno**

- Las firmas públicas de `filter_alertas` (Stock) y `filter_ventas_tra` (TRA) **no cambiaron**.
- La UI sigue llamando a las mismas funciones con los mismos parámetros.
- Solo cambió la implementación interna (refactor a util compartido).

### Cambios de comportamiento

- **Stock:**
  - Antes: productos sin jerarquía se incluían siempre (incluso con filtros activos).
  - Ahora: productos sin jerarquía se incluyen siempre (sin cambio, estrategia `"include"`).
  - **No hay cambio observable** en la mayoría de casos.

- **TRA/MBRP:**
  - Antes: 3 filtros secuenciales con comparación directa `str(r[2]) == str(dept_code)`.
  - Ahora: 1 filtro unificado con normalización `.strip()`.
  - **Comportamiento mejorado**: más robusto ante espacios y tipos inconsistentes.

---

## Configuración avanzada

### Cambiar estrategia de Stock a estricta

Si quieres que Stock oculte productos sin jerarquía al aplicar filtros:

```python
# En pal/services/stock.py, línea ~111:
datos_filtrados = filter_by_hierarchy(
    datos_filtrados,
    dept_code=dept_code,
    group_code=group_code,
    sub_code=sub_code,
    get_code=lambda r: r[0],
    jerarquia_map=producto_jerarquia or {},
    missing_strategy="exclude",  # <- cambiar de "include" a "exclude"
)
```

### Añadir logging detallado

En `filter_by_hierarchy`, añade prints de debug:

```python
if missing_strategy not in esstrategias_validas:
    print(f"[FILTERS DEBUG] Estrategia inválida: {missing_strategy}, usando 'exclude'")
    missing_strategy = "exclude"
```

---

## Próximos pasos

- [ ] Tests unitarios para `filter_by_hierarchy` (ambos modos).
- [ ] Tests de integración E2E para Stock/TRA/MBRP con fixtures de jerarquías.
- [ ] Optimización: cachear resultados de `filter_by_hierarchy` si se llama múltiples veces con mismos parámetros.
- [ ] Considerar mover normalización de strings a una función helper global.

---

## Contacto

Si encuentras problemas o quieres sugerir mejoras, abre un issue o PR. Los cambios están listos para merge sin breaking changes.
