# Módulo MBRP - Movimiento de Baja Rotación de Producto
## Documentación Completa Unificada

---

## 📊 Resumen Ejecutivo

### ¿Qué es el Módulo MBRP?

El **Módulo MBRP (Movimiento de Baja Rotación de Producto)** es una herramienta especializada de análisis de inventarios que identifica y gestiona productos con **baja o nula actividad comercial**, permitiendo a las empresas:

- **Identificar productos obsoletos** o con riesgo de obsolescencia
- **Liberar capital** inmovilizado en inventario de baja rotación
- **Optimizar espacio** en almacenes y puntos de venta
- **Tomar decisiones** sobre liquidación, descontinuación o promoción

### Beneficios Corporativos

| Beneficio | Impacto | Métrica Clave |
|-----------|---------|---------------|
| **Liberación de Capital** | Reducción de inventario inmovilizado en productos de baja rotación | 20% a 35% en capital liberado |
| **Optimización de Espacio** | Mejor aprovechamiento de almacenes y góndolas | +15% a +25% en espacio disponible |
| **Reducción de Obsolescencia** | Menor riesgo de pérdidas por productos vencidos o fuera de moda | -40% a -60% en pérdidas por obsolescencia |
| **Enfoque Estratégico** | Concentración de recursos en productos rentables | ROI visible en 2-4 meses |

### Diferencias Clave con TRA

| Característica | TRA | MBRP |
|----------------|-----|------|
| **Enfoque** | Productos de ALTA rotación | Productos de BAJA rotación |
| **Objetivo** | Optimizar reposición | Identificar problemas |
| **Métrica Principal** | Clasificación ABC (Pareto) | Índice de Movilidad (IM) |
| **Acción Típica** | Aumentar pedidos | Reducir/liquidar inventario |
| **Usuario Principal** | Compras | Comercial/Finanzas |

---

## 🎯 Índice de Movilidad (IM)

### ¿Qué es el IM?

El **Índice de Movilidad (IM)** es la métrica central del módulo MBRP. Mide la **actividad comercial relativa** de un producto en comparación con todos los productos del período, expresado como un porcentaje del 0% al 100%.

```
┌────────────────────────────────────────────────────────────┐
│  ESCALA DEL ÍNDICE DE MOVILIDAD (IM)                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  100% ███████████████████████████████████████████ MÁXIMA   │
│       │ Producto con mayores ventas del período            │
│       │ Alta demanda - No requiere intervención            │
│       └─────────────────────────────────────────────────   │
│                                                            │
│   50% ████████████████████ MEDIA                           │
│       │ Movilidad moderada                                 │
│       │ Requiere monitoreo                                 │
│       └─────────────────────────────                       │
│                                                            │
│   30% ███████████ UMBRAL MBRP                              │
│       │ Frontera entre rotación aceptable y baja           │
│       │  Inicio de zona de riesgo                          │  
│       └───────────────                                     │
│                                                            │
│   10% ███ BAJA                                             │
│       │ Muy poca actividad                                 │
│       │ 🔴 Requiere acción correctiva                     │
│       └──                                                  │
│                                                            │
│    0% ▓ SIN MOVIMIENTO                                     │
│       │ Producto estancado                                 │
│       │ 🚨 CRÍTICO - Acción inmediata                      │
│       └                                                    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Fórmula del IM

**Normalización Min-Max:**
```
IM = ((Ventas Producto - Ventas Mínimas) / (Ventas Máximas - Ventas Mínimas)) × 100
```

**Donde:**
- **Ventas Producto**: Neto vendido del producto específico
- **Ventas Mínimas**: Menores ventas entre todos los productos del período
- **Ventas Máximas**: Mayores ventas entre todos los productos del período

### Ejemplo Práctico de Cálculo

**Datos del período (enero-marzo 2025, sede Cabudare):**

| Código | Producto | Ventas Netas | IM | Clasificación |
|--------|----------|--------------|-----|---------------|
| A001 | Aceite Motor 10W40 | 1,000 u | **100%** | ⚪ ALTA (excluido de MBRP) |
| B045 | Filtro Aire | 500 u | **50%** | 🟢 ALTA (excluido) |
| C120 | Batería 12V | 300 u | **30%** | 🟡 MEDIA (umbral MBRP) |
| D089 | Cable Arranque | 100 u | **10%** | 🔴 BAJA (crítico) |
| E201 | Llanta Refacción | 10 u | **1%** | 🔴 BAJA (muy crítico) |
| F333 | Accesorio Antiguo | 0 u | **0%** | 🚨 SIN_MOVIMIENTO (emergencia) |

**Cálculos paso a paso:**

```
Ventas Máximas = 1,000 (Producto A001)
Ventas Mínimas = 0 (Producto F333)
Rango = 1,000 - 0 = 1,000

IM(A001) = ((1,000 - 0) / 1,000) × 100 = 100% ✅
IM(B045) = ((500 - 0) / 1,000) × 100 = 50%
IM(C120) = ((300 - 0) / 1,000) × 100 = 30% ⚠️ (umbral MBRP)
IM(D089) = ((100 - 0) / 1,000) × 100 = 10% 🔴
IM(E201) = ((10 - 0) / 1,000) × 100 = 1% 🔴
IM(F333) = ((0 - 0) / 1,000) × 100 = 0% 🚨
```

**Interpretación:**
- Productos con IM > 30% (A001, B045): **Excluidos del análisis MBRP** (rotación aceptable)
- Producto con IM = 30% (C120): **Umbral** - requiere monitoreo
- Productos con IM < 30% (D089, E201, F333): **Foco del análisis MBRP** - requieren intervención

---

## 🔍 Clasificación MBRP

### Categorías de Clasificación

A diferencia de TRA (que clasifica en ALTA/MEDIA/BAJA según Pareto), MBRP usa **criterios inversos** basados en el IM:

```
┌──────────────────────────────────────────────────────────────┐
│  CLASIFICACIÓN MBRP - CRITERIOS                              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  🚨 SIN_MOVIMIENTO (IM = 0%)                                 │
│  ├─ Productos sin ventas en el período                       │
│  ├─ Máxima prioridad de intervención                         │
│  └─ Acción: Liquidación inmediata o descontinuación          │
│                                                               │
│  🔴 BAJA (0% < IM ≤ 10%)                                     │
│  ├─ Muy poca actividad comercial                            │
│  ├─ Alta prioridad de intervención                          │
│  └─ Acción: Evaluar descontinuación o promoción agresiva    │
│                                                               │
│  🟡 MEDIA (10% < IM ≤ 30%)                                   │
│  ├─ Rotación moderadamente baja                             │
│  ├─ Prioridad media de intervención                         │
│  └─ Acción: Promociones, reducir pedidos futuros            │
│                                                               │
│  🟢 ALTA (IM > 30%)                                          │
│  ├─ Rotación aceptable                                      │
│  ├─ Normalmente excluido del análisis MBRP                  │
│  └─ Acción: Ninguna (gestión normal)                        │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Estrategias por Categoría

#### 🚨 SIN_MOVIMIENTO (IM = 0%)
**Estrategia: "Acción Inmediata"**

- 🔴 **CRÍTICO** - Producto completamente estancado
- ✅ Liquidación con **descuentos agresivos** (50-70%)
- ✅ **Descontinuar** del catálogo
- ✅ **Transferir** a otras sedes si tienen demanda
- ✅ Evaluar **donación** o destrucción si no es vendible
- ⚠️ Liberar espacio de almacén **inmediatamente**

**Checklist de Acción:**
- [ ] Verificar si producto está activo en sistema
- [ ] Confirmar stock actual en todos los depósitos
- [ ] Revisar última fecha de venta (si existe)
- [ ] Calcular costo de mantener vs liquidar
- [ ] Decidir: Liquidar / Descontinuar / Transferir
- [ ] Ejecutar acción en máximo 30 días

#### 🔴 BAJA (IM ≤ 10%)
**Estrategia: "Intervención Urgente"**

- ✅ Promociones **agresivas** (30-50% descuento)
- ✅ Evaluar **descontinuación** a mediano plazo
- ✅ **No reponer** inventario
- ✅ Análisis de causa raíz (¿por qué no se vende?)
- ⚠️ Monitoreo **semanal** de evolución

**Causas Comunes:**
- Producto obsoleto o fuera de moda
- Precio no competitivo
- Baja visibilidad en punto de venta
- Cambio en preferencias del cliente
- Problema de calidad reportado

**KPIs:**
- Días sin venta: Verificar si >60 días
- Stock actual vs ideal: Reducir a mínimo
- Costo de mantenimiento: Alto vs beneficio bajo

#### 🟡 MEDIA (10% < IM ≤ 30%)
**Estrategia: "Monitoreo y Corrección"**

- ✅ Promociones **moderadas** (15-30% descuento)
- ✅ **Reducir pedidos** futuros a mínimo
- ✅ Mejorar **visibilidad** en punto de venta
- ✅ Evaluar **reposicionamiento** de precio
- ⚠️ Monitoreo **quincenal**

**Acciones Preventivas:**
- Análisis de tendencia (¿está mejorando o empeorando?)
- Comparación con períodos anteriores
- Benchmarking con sedes similares

**KPIs:**
- Nivel de servicio: >70% (aceptable)
- Stock ideal: 10-15 días máximo
- Revisión: Quincenal

---

## 📐 Métricas Complementarias

### 1. Última Venta (Días sin Venta)

**Fórmula:**
```
Días sin Venta = Fecha Actual - Fecha Última Venta
```

**Interpretación:**
```
Días sin Venta = 0    → Venta hoy (producto activo)
Días sin Venta = 1-30  → Normal (según rotación esperada)
Días sin Venta = 31-60 → Alerta (requiere atención)
Días sin Venta = 61-90 → Crítico (acción urgente)
Días sin Venta > 90    → Emergencia (liquidar/descontinuar)
Días sin Venta = -1    → Nunca se ha vendido (producto nuevo o problema)
```

**Integración con IM:**

| IM | Días sin Venta | Severidad | Acción |
|----|----------------|-----------|--------|
| 0% | >90 | 🚨 MÁXIMA | Liquidar inmediatamente |
| ≤5% | >90 | 🔴 CRÍTICA | Evaluar descontinuación |
| ≤10% | 60-90 | 🟠 ALTA | Promoción agresiva |
| ≤20% | 30-60 | 🟡 MEDIA | Monitoreo cercano |
| ≤30% | <30 | 🟢 BAJA | Seguimiento normal |

### 2. Stock Actual vs Rotación

**Concepto:** Productos con IM bajo y stock alto son los más críticos (capital inmovilizado).

**Matriz de Decisión:**

```
┌──────────────────────────────────────────────────────────────┐
│  MATRIZ IM vs STOCK ACTUAL                                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│        Stock Alto                                            │
│            ↑                                                 │
│            │                                                 │
│            │  X MEDIO        X CRÍTICO                       │
│            │  Reducir pedidos  Liquidar urgente              │
│            │                                                 │
│            │  ────────────────────────────                   │
│            │                                                 │
│            │  X OK           X ALERTA                        │
│            │  Normal          Promocionar                    │
│            │                                                 │
│        Stock Bajo                                            │
│            └─────────────────────────────────→               │
│              IM Alto            IM Bajo                      │
│              (>30%)             (<30%)                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Ejemplos:**
- **IM 5% + Stock 200 u**: 🚨 **CRÍTICO** - Liquidar con descuento 50-70%
- **IM 15% + Stock 100 u**: 🟠 **ALERTA** - Promoción 30% y no reponer
- **IM 25% + Stock 50 u**: 🟡 **MEDIO** - Reducir pedidos futuros
- **IM 5% + Stock 5 u**: 🟢 **OK** - Dejar agotar naturalmente

---

## 🔧 Implementación Técnica

### Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  UI MBRP (Tkinter + TTK)                               │ │
│  │  - Filtros jerárquicos (Dept/Grupo/Sub)               │ │
│  │  - Vista con colores por severidad                    │ │
│  │  - Columnas: IM%, Última Venta, Stock, Rotación       │ │
│  │  - Botón "📊 Reporte" para análisis detallado         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE LÓGICA DE NEGOCIO                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  pal/services/mbrp.py                                  │ │
│  │  - calcular_indice_movilidad()                         │ │
│  │  - filtrar_productos_baja_rotacion()                   │ │
│  │  - clasificar_rotacion_mbrp()                          │ │
│  │  - obtener_ultimas_ventas_bulk()                       │ │
│  │  - calcular_dias_sin_venta()                           │ │
│  │  - generar_reporte_baja_rotacion()                     │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  pal/services/filters.py (Unificado con TRA/Stock)    │ │
│  │  - filter_by_hierarchy()                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE ACCESO A DATOS                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  pal/infrastructure/database.py                        │ │
│  │  - obtener_ventas_por_producto_chunk()                │ │
│  │  - fetch_data() con pool de conexiones                │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                        BASE DE DATOS                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  SQL Server                                            │ │
│  │  - Tablas: TR_INVENTARIO, MA_PRODUCTOS                │ │
│  │  - Consultas: Ventas netas, última venta, stock       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Funciones Principales

#### 1. Cálculo del Índice de Movilidad

```python
def calcular_indice_movilidad(ventas_data: List, 
                              total_ventas_periodo: float = None) -> Dict[str, float]:
    """
    Calcula el IM para cada producto mediante normalización min-max.
    
    Complejidad: O(n) donde n = número de productos
    
    Returns:
        dict: Mapeo código -> IM (0.0 a 100.0)
    """
    # Extraer ventas por código
    ventas_por_codigo = {str(item[0]): float(item[5]) for item in ventas_data}
    
    # Encontrar máximo y mínimo
    max_ventas = max(ventas_por_codigo.values())
    min_ventas = min(ventas_por_codigo.values())
    rango = max_ventas - min_ventas
    
    if rango == 0:
        return {codigo: 50.0 for codigo in ventas_por_codigo.keys()}
    
    # Normalizar 0-100%
    indices_movilidad = {}
    for codigo, ventas in ventas_por_codigo.items():
        im = ((ventas - min_ventas) / rango) * 100
        indices_movilidad[codigo] = round(im, 1)
    
    return indices_movilidad
```

#### 2. Última Venta (Bulk)

```python
def obtener_ultimas_ventas_bulk(db_manager, 
                                codigos_productos: List[str], 
                                sede_codigo: str = None) -> Dict[str, datetime]:
    """
    Obtiene fechas de última venta para múltiples productos de forma eficiente.
    
    Complejidad: O(1) query con GROUP BY
    
    Returns:
        dict: Mapeo código -> fecha última venta
    """
    placeholders = ','.join(['?' for _ in codigos_productos])
    query = f"""
    SELECT c_Codarticulo, MAX(f_fecha) as ultima_venta
    FROM TR_INVENTARIO 
    WHERE c_Codarticulo IN ({placeholders})
    AND c_Concepto = 'VEN'
    AND n_Cantidad > 0
    """
    
    if sede_codigo:
        query += " AND c_Deposito LIKE ?"
        params = list(codigos_productos) + [sede_codigo]
    else:
        params = list(codigos_productos)
        
    query += " GROUP BY c_Codarticulo"
    result = db_manager.fetch_data(query, params)
    
    return {str(row[0]): row[1] for row in result}
```

#### 3. Clasificación MBRP

```python
def clasificar_rotacion_mbrp(ventas_data: List) -> List:
    """
    Clasifica productos según IM (inverso a TRA).
    
    Criterios:
    - IM = 0%: SIN_MOVIMIENTO
    - IM ≤ 10%: BAJA
    - IM ≤ 30%: MEDIA
    - IM > 30%: ALTA (normalmente excluida)
    
    Returns:
        list: Ventas con clasificación añadida
    """
    indices_movilidad = calcular_indice_movilidad(ventas_data)
    
    ventas_clasificadas = []
    for item in ventas_data:
        codigo = str(item[0])
        im = indices_movilidad.get(codigo, 0.0)
        
        if im == 0.0:
            rotacion = "SIN_MOVIMIENTO"
        elif im <= 10.0:
            rotacion = "BAJA"
        elif im <= 30.0:
            rotacion = "MEDIA"
        else:
            rotacion = "ALTA"
        
        item_list = list(item) + [rotacion]
        ventas_clasificadas.append(tuple(item_list))
    
    return ventas_clasificadas
```

#### 4. Reporte de Baja Rotación

```python
def generar_reporte_baja_rotacion(ventas_data: List, 
                                  db_manager, 
                                  sede_codigo: str = None) -> Dict:
    """
    Genera reporte ejecutivo de productos de baja rotación.
    
    Returns:
        dict: Estadísticas y productos críticos
    """
    indices_movilidad = calcular_indice_movilidad(ventas_data)
    codigos = [str(item[0]) for item in ventas_data]
    ultimas_ventas = obtener_ultimas_ventas_bulk(db_manager, codigos, sede_codigo)
    
    # Clasificar
    sin_movimiento = sum(1 for im in indices_movilidad.values() if im == 0.0)
    baja_rotacion = sum(1 for im in indices_movilidad.values() if 0.0 < im <= 10.0)
    media_rotacion = sum(1 for im in indices_movilidad.values() if 10.0 < im <= 30.0)
    alta_rotacion = sum(1 for im in indices_movilidad.values() if im > 30.0)
    
    # Productos críticos (IM ≤ 5% y >90 días sin venta)
    productos_criticos = []
    for item in ventas_data:
        codigo = str(item[0])
        im = indices_movilidad.get(codigo, 0.0)
        ultima_venta = ultimas_ventas.get(codigo)
        dias_sin_venta = calcular_dias_sin_venta(ultima_venta)
        
        if im <= 5.0 and dias_sin_venta > 90:
            productos_criticos.append({
                'codigo': codigo,
                'descripcion': str(item[1]),
                'im': im,
                'dias_sin_venta': dias_sin_venta
            })
    
    return {
        "total_productos": len(ventas_data),
        "sin_movimiento": sin_movimiento,
        "baja_rotacion": baja_rotacion,
        "media_rotacion": media_rotacion,
        "alta_rotacion": alta_rotacion,
        "productos_criticos": len(productos_criticos),
        "detalle_criticos": productos_criticos[:10],
        "porcentaje_baja_rotacion": round((baja_rotacion + sin_movimiento) / len(ventas_data) * 100, 1)
    }
```

### Consultas SQL Optimizadas

#### Ventas Netas (reutiliza consulta TRA)
```sql
-- Misma consulta base que TRA
SELECT 
    i.c_Codarticulo AS codigo,
    COALESCE(p.C_DESCRI, 'SIN DESCRIPCIÓN') AS descripcion,
    COALESCE(p.C_DEPARTAMENTO, '') AS departamento,
    COALESCE(p.C_GRUPO, '') AS grupo,
    COALESCE(p.C_SUBGRUPO, '') AS subgrupo,
    SUM(CASE 
        WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
        WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
        ELSE 0 
    END) AS neto
FROM TR_INVENTARIO i WITH (NOLOCK)
LEFT JOIN MA_PRODUCTOS p WITH (NOLOCK) 
    ON i.c_Codarticulo = p.C_CODIGO
WHERE i.f_fecha BETWEEN @FechaInicio AND @FechaFin
    AND i.c_Concepto IN ('VEN', 'DEV')
    AND i.c_Deposito LIKE @Sede
GROUP BY 
    i.c_Codarticulo,
    p.C_DESCRI,
    p.C_DEPARTAMENTO,
    p.C_GRUPO,
    p.C_SUBGRUPO
ORDER BY neto ASC  -- ⚠️ Orden ascendente (de menor a mayor) para MBRP
OFFSET @StartRow ROWS 
FETCH NEXT @ChunkSize ROWS ONLY;
```

#### Última Venta (Bulk)
```sql
-- Obtener última venta para múltiples productos
SELECT 
    c_Codarticulo, 
    MAX(f_fecha) as ultima_venta
FROM TR_INVENTARIO WITH (NOLOCK)
WHERE c_Codarticulo IN (@Codigo1, @Codigo2, ..., @CodigoN)
    AND c_Concepto = 'VEN'
    AND n_Cantidad > 0
    AND c_Deposito LIKE @Sede
GROUP BY c_Codarticulo;
```

**Índices Recomendados:**
```sql
-- Mismo índice que TRA (reutilizable)
CREATE NONCLUSTERED INDEX IX_TR_INVENTARIO_MBRP 
ON TR_INVENTARIO (f_fecha, c_Concepto, c_Deposito)
INCLUDE (c_Codarticulo, n_Cantidad);

-- Índice adicional para última venta
CREATE NONCLUSTERED INDEX IX_TR_INVENTARIO_ULTIMA_VENTA
ON TR_INVENTARIO (c_Codarticulo, c_Concepto, f_fecha DESC)
WHERE c_Concepto = 'VEN' AND n_Cantidad > 0;
```

---

## 📊 Interpretación de Resultados

### Dashboard MBRP - Vista Principal

```
┌──────────────────────────────────────────────────────────────┐
│  ANÁLISIS MBRP - Período: 01/01/2025 - 31/03/2025           │
│  Sede: Cabudare (0301)                                       │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  📈 RESUMEN EJECUTIVO                                        │
│  ├─ Total productos analizados: 2,450                        │
│  ├─ Productos filtrados (IM ≤ 30%): 735 (30%)               │
│  ├─ SIN MOVIMIENTO (IM = 0%): 48 (2%)                        │
│  ├─ BAJA rotación (IM ≤ 10%): 245 (10%)                     │
│  ├─ MEDIA rotación (IM ≤ 30%): 442 (18%)                    │
│  └─ Valor inmovilizado estimado: Bs. 2,500,000              │
│                                                               │
│  🚨 PRODUCTOS CRÍTICOS (Top 5)                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Código │ Descripción    │ IM%  │ Última Venta │ Stock││  │
│  ├────────┼────────────────┼──────┼──────────────┼──────┤│  │
│  │ F333   │ Accesorio Ant. │ 0.0% │ 150 días    │ 120 u││  │
│  │ E201   │ Llanta Refac.  │ 0.5% │ 95 días     │ 45 u ││  │
│  │ D089   │ Cable Arranque │ 2.3% │ 78 días     │ 80 u ││  │
│  │ G445   │ Funda Asiento  │ 3.1% │ 62 días     │ 35 u ││  │
│  │ H102   │ Limpia Vidrios │ 4.8% │ 45 días     │ 90 u ││  │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  💰 IMPACTO FINANCIERO ESTIMADO                              │
│  ├─ Capital inmovilizado en IM < 10%: Bs. 1,200,000         │
│  ├─ Potencial liberación con liquidación 50%: Bs. 600,000   │
│  └─ Ahorro anual en costos de almacenaje: Bs. 120,000       │
│                                                               │
│  ⚡ ACCIONES RECOMENDADAS                                    │
│  ├─ 48 productos: Liquidar inmediatamente (IM = 0%)         │
│  ├─ 93 productos: Promoción agresiva 50% (IM < 5%)          │
│  ├─ 152 productos: Promoción moderada 30% (IM 5-10%)        │
│  └─ 442 productos: Reducir pedidos futuros (IM 10-30%)      │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Códigos de Color en la Interfaz

| IM % | Color Fondo | Color Texto | Fuente | Severidad |
|------|-------------|-------------|--------|-----------|
| 0% | Rosa intenso (#FFCDD2) | Rojo oscuro (#B71C1C) | **Negrita** | 🚨 CRÍTICA |
| <5% | Rosa intenso (#FFCDD2) | Rojo oscuro (#D32F2F) | **Negrita** | 🔴 MUY ALTA |
| 5-10% | Rosa claro (#FFEBEE) | Negro (#000000) | **Negrita** | 🔴 ALTA |
| 10-20% | Naranja claro (#FFF3E0) | Negro (#000000) | Normal | 🟡 MEDIA |
| 20-30% | Amarillo claro (#FFF8E1) | Negro (#000000) | Normal | 🟢 BAJA |
| >30% | Gris claro (#F5F5F5) | Gris (#666666) | Normal | ⚪ EXCLUIDO |

---

## 🛠️ Configuración y Uso

### Activación del Módulo

**Archivo:** `db_config.ini`
```ini
[Modules]
mbrp = True

[Debug]
mbrp = False  # Activar para logs detallados
```

### Uso Básico

1. **Seleccionar período de análisis** (7 días a 1 año)
   - Recomendado: 90 días para análisis de baja rotación

2. **Elegir sede** (Cabudare, Guanare, Barinas)

3. **Hacer clic en "Cargar"**
   - Carga asíncrona en segundo plano
   - Filtrado automático de productos con IM ≤ 30%

4. **Aplicar filtros** jerárquicos (opcional)
   - Departamento → Grupo → Subgrupo

5. **Revisar columnas**:
   - **IM %**: Índice de Movilidad (principal indicador)
   - **Última Venta**: Días transcurridos desde última venta
   - **Stock Actual**: Unidades en inventario
   - **Rotación**: Clasificación MBRP (SIN_MOVIMIENTO/BAJA/MEDIA)

6. **Generar Reporte** (botón "📊 Reporte")
   - Estadísticas detalladas
   - Top productos críticos
   - Impacto financiero estimado

---

## 📈 Casos de Uso Prácticos

### Caso 1: Liquidación Trimestral de Inventario

**Objetivo:** Liberar capital y espacio mediante liquidación estratégica

**Pasos:**
1. Cargar MBRP del último trimestre
2. Ordenar por IM ascendente (de menor a mayor)
3. Filtrar productos con IM < 10% y >60 días sin venta
4. Calcular valor total de inventario a liquidar
5. Definir descuentos por categoría:
   - IM = 0%: Descuento 70%
   - IM < 5%: Descuento 50%
   - IM 5-10%: Descuento 30%
6. Planificar campaña de liquidación (2-4 semanas)

**Resultado esperado:** 
- Liberación de 15-25% del capital inmovilizado
- Recuperación de 40-60% del valor nominal
- Liberación de espacio en almacén

### Caso 2: Descontinuación de Productos

**Objetivo:** Identificar productos para eliminar del catálogo

**Pasos:**
1. Analizar MBRP de los últimos 6-12 meses
2. Filtrar productos con IM = 0% por más de 2 trimestres consecutivos
3. Verificar si producto está activo en sistema
4. Analizar tendencia histórica (¿siempre fue bajo o es reciente?)
5. Consultar con área comercial sobre viabilidad futura
6. Decidir: Descontinuar / Mantener con stock mínimo / Transferir a otra sede

**Criterios de Descontinuación:**
- IM = 0% en 2+ trimestres consecutivos
- Producto obsoleto o reemplazado por nuevo modelo
- Costo de mantenimiento > Beneficio potencial
- Sin demanda proyectada a futuro

### Caso 3: Optimización de Compras

**Objetivo:** Evitar reponer productos de baja rotación

**Pasos:**
1. Generar MBRP mensualmente
2. Crear "lista negra" de productos con IM < 20%
3. Integrar lista con sistema de compras
4. Bloquear o alertar cuando se intente generar OC de productos en lista
5. Revisar mensualmente y ajustar umbral según necesidad

**Resultado esperado:**
- Reducción de 20-30% en compras innecesarias
- Mejor aprovechamiento del capital de trabajo
- Menor riesgo de obsolescencia

### Caso 4: Análisis de Portafolio por Línea

**Objetivo:** Evaluar salud de líneas de productos

**Pasos:**
1. Agrupar productos MBRP por Departamento
2. Calcular % de productos con IM < 10% por departamento
3. Identificar departamentos problemáticos (>30% productos con baja rotación)
4. Analizar causas raíz:
   - ¿Problema de toda la línea o productos específicos?
   - ¿Tendencia de mercado o problema interno?
   - ¿Competencia más agresiva?
5. Definir estrategia por departamento

**Ejemplo de Análisis:**

| Departamento | Total Productos | IM < 10% | % Problemáticos | Acción |
|--------------|-----------------|----------|-----------------|--------|
| Aceites | 250 | 15 | 6% | ✅ Saludable |
| Llantas | 180 | 45 | 25% | ⚠️ Monitorear |
| Accesorios | 320 | 128 | 40% | 🚨 Revisar catálogo |
| Herramientas | 150 | 8 | 5% | ✅ Saludable |

---

## 🔄 Integración TRA + MBRP

### Visión Completa del Portafolio

Usar **TRA y MBRP en conjunto** proporciona una visión 360° del inventario:

```
┌──────────────────────────────────────────────────────────────┐
│  ANÁLISIS INTEGRAL DE PORTAFOLIO                             │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  TRA (Productos ALTA rotación - Foco: Reposición)            │
│  ├─ 20% de productos                                         │
│  ├─ 80% de ventas                                            │
│  ├─ Acción: Mantener stock óptimo                           │
│  └─ KPI: Nivel de servicio >95%                             │
│                                                               │
│  ──────────────────────────────                              │
│                                                               │
│  MBRP (Productos BAJA rotación - Foco: Liquidación)          │
│  ├─ 30% de productos                                         │
│  ├─ <5% de ventas                                            │
│  ├─ Acción: Reducir/liquidar inventario                     │
│  └─ KPI: Capital liberado                                   │
│                                                               │
│  ──────────────────────────────                              │
│                                                               │
│  ZONA MEDIA (Productos rotación moderada)                    │
│  ├─ 50% de productos                                         │
│  ├─ 15% de ventas                                            │
│  ├─ Acción: Balance entre reposición y control              │
│  └─ KPI: Días de cobertura 15-30                            │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 📞 Soporte y Contacto

**Equipo de Desarrollo:** Sistema PAL  
**Versión del Módulo:** 1.0  
**Última actualización:** Octubre 2025  
**Documentación:** `docs/modulo_mbrp_completo.md`

**Documentación relacionada:**
- `docs/modulo_tra_completo.md` - Módulo complementario TRA
- `docs/filters_unified.md` - Filtros jerárquicos unificados
- `docs/indice_movilidad_MBRP.md` - Documentación técnica del IM

---

**© 2025 Sistema PAL - Todos los derechos reservados**
