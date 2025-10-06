# Módulo TRA - Tiempo de Reposición de Artículos
## Documentación Completa Unificada

---

## 📊 Resumen Ejecutivo

### ¿Qué es el Módulo TRA?

El **Módulo TRA (Tiempo de Reposición de Artículos)** es una herramienta estratégica de análisis de inventarios que permite a las empresas optimizar sus operaciones comerciales mediante:

- **Clasificación inteligente** de productos según su rotación y representación en ventas
- **Predicción precisa** de necesidades de reabastecimiento
- **Optimización de capital** invertido en inventario
- **Reducción de quiebres** de stock y obsolescencia

### Beneficios Corporativos

| Beneficio | Impacto | Métrica Clave |
|-----------|---------|---------------|
| **Optimización de Inventario** | Reducción de capital inmovilizado en productos de baja rotación | -15% a -25% en inventario ocioso |
| **Mejor Disponibilidad** | Aumento en disponibilidad de productos de alta rotación | +20% a +35% en nivel de servicio |
| **Decisiones Informadas** | Compras basadas en datos históricos y proyecciones | Reducción de 30% en errores de compra |
| **Análisis Estratégico** | Identificación de oportunidades y productos problemáticos | ROI medible en 3-6 meses |

### Casos de Uso Principales

#### 1️⃣ **Gerencia de Compras**
- Priorizar pedidos según rotación ABC
- Calcular cantidades óptimas de reorden
- Identificar productos para negociación con proveedores

#### 2️⃣ **Gerencia Comercial**
- Detectar productos estrella (alta representación)
- Identificar categorías con crecimiento/decrecimiento
- Planificar promociones en productos de baja rotación

#### 3️⃣ **Gerencia de Operaciones**
- Optimizar espacio en almacén según rotación
- Proyectar necesidades de personal para picking
- Reducir costos de mantenimiento de inventario

#### 4️⃣ **Dirección General**
- Dashboard ejecutivo de indicadores clave
- Análisis de portafolio de productos
- Benchmarking entre sucursales/sedes

---

## 🎯 Metodología de Clasificación ABC

### Principio de Pareto Aplicado

El módulo utiliza el **Principio 80/20** (Pareto) adaptado para inventarios:

- **80%** de las ventas provienen del **20%** de los productos → **ALTA rotación**
- **15%** adicional de ventas del siguiente **20%** de productos → **MEDIA rotación**
- **5%** final de ventas del restante **60%** de productos → **BAJA rotación**

### Categorías de Clasificación

```
┌─────────────────────────────────────────────────────────────┐
│  CLASIFICACIÓN ABC - DISTRIBUCIÓN TÍPICA                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ALTA (20% productos, 80% ventas)                           │
│  ████████████████████████████████████████████               │
│  • Rotación frecuente                                       │
│  • Stock de seguridad alto                                  │
│  • Pedidos frecuentes, entregas rápidas                     │
│  • Seguimiento diario                                       │
│                                                             │
│  MEDIA (20% productos, 15% ventas)                          │
│  ███████████                                                │
│  • Rotación moderada                                        │
│  • Stock intermedio                                         │
│  • Pedidos quincenales                                      │
│  • Seguimiento semanal                                      │
│                                                             │
│  BAJA (60% productos, 5% ventas)                            │
│  ████                                                       │
│  • Rotación baja o nula                                     │
│  • Stock mínimo                                             │
│  • Pedidos ocasionales                                      │
│  • Revisión mensual / Considerar descontinuar               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Estrategias por Categoría

#### 🟢 Productos ALTA Rotación
**Estrategia: "Just-in-Time Plus"**

- ✅ Mantener **stock de seguridad elevado** (30-45 días)
- ✅ **Pedidos frecuentes** con entregas semanales o quincenales
- ✅ Monitoreo **diario** de disponibilidad
- ✅ Acuerdos especiales con proveedores (descuentos por volumen)
- ⚠️ **Alta prioridad** en reposición ante quiebre

**KPIs:**
- Nivel de servicio: >95%
- Días de cobertura: 30-45 días
- Rotación mensual: >3 veces

#### 🟡 Productos MEDIA Rotación
**Estrategia: "Balance Controlado"**

- ✅ Stock **moderado** (15-30 días)
- ✅ Pedidos **quincenales o mensuales**
- ✅ Monitoreo **semanal** de tendencias
- ✅ Análisis de estacionalidad
- ⚠️ Atención a cambios de tendencia

**KPIs:**
- Nivel de servicio: >85%
- Días de cobertura: 15-30 días
- Rotación mensual: 1-3 veces

#### 🔴 Productos BAJA Rotación
**Estrategia: "Minimización y Evaluación"**

- ✅ Stock **mínimo** (5-15 días o pedido bajo demanda)
- ✅ Pedidos **ocasionales** o bajo pedido
- ✅ **Evaluación mensual** de continuidad
- ⚠️ Considerar **liquidación** o **descontinuación**
- ⚠️ Liberar capital para productos de mayor rotación

**KPIs:**
- Nivel de servicio: >70% (aceptable)
- Días de cobertura: 5-15 días
- Rotación mensual: <1 vez
- **Acción:** Revisión trimestral para descontinuar

---

## 📐 Fórmulas y Cálculos Técnicos

### 1. Clasificación ABC por Porcentaje Acumulado

**Paso 1: Ordenar productos por ventas (descendente)**
```
Productos ordenados: P₁, P₂, P₃, ..., Pₙ
Ventas ordenadas:    V₁ ≥ V₂ ≥ V₃ ≥ ... ≥ Vₙ
```

**Paso 2: Calcular neto acumulado**
```
NA(i) = Σ(Vⱼ) para j = 1 hasta i
NT = Σ(Vⱼ) para j = 1 hasta n
```

**Paso 3: Calcular porcentaje acumulado**
```
PA(i) = (NA(i) / NT) × 100
```

**Paso 4: Clasificar según rangos**
```
Si PA(i) ≤ 80%  → ALTA
Si 80% < PA(i) ≤ 95% → MEDIA
Si PA(i) > 95% → BAJA
```

**Ejemplo Práctico:**

| Producto | Ventas | Neto Acum. | % Acum. | Clasificación |
|----------|--------|------------|---------|---------------|
| A | 500,000 | 500,000 | 50% | **ALTA** |
| B | 200,000 | 700,000 | 70% | **ALTA** |
| C | 100,000 | 800,000 | 80% | **ALTA** |
| D | 80,000 | 880,000 | 88% | **MEDIA** |
| E | 70,000 | 950,000 | 95% | **MEDIA** |
| F | 50,000 | 1,000,000 | 100% | **BAJA** |

**Total ventas período:** 1,000,000

### 2. Stock Ideal y Tiempo de Reposición

#### Fórmula Base: Promedio Diario de Ventas (PDV)
```
PDV = Neto Ventas / Días del Período
```

#### Stock Ideal (SI)
```
SI = PDV × Días de Buffer × Factor de Seguridad

Donde:
- Días de Buffer: 30 días (por defecto)
- Factor de Seguridad: 1.0 a 1.5 (según criticidad)
```

#### Días Restantes de Stock (DR)
```
DR = Stock Actual / PDV

Interpretación:
- DR > 30 días: Sobrestockeado
- 15 ≤ DR ≤ 30: Nivel óptimo
- DR < 15 días: Alerta de reposición
- DR < 7 días: Crítico - reposición urgente
```

**Ejemplo de Cálculo:**

```
Producto: Aceite Motor 10W40
Ventas período (365 días): 1,825 unidades
Stock actual: 150 unidades
Buffer deseado: 30 días

PDV = 1,825 / 365 = 5 unidades/día

Stock Ideal = 5 × 30 × 1.2 = 180 unidades
             (con factor seguridad 20%)

Días Restantes = 150 / 5 = 30 días

Acción: Stock en nivel óptimo, sin necesidad de reposición inmediata
```

### 3. Porcentaje de Representación

#### Representación Individual
```
RI(i) = (Ventas Producto i / Total Ventas Período) × 100
```

#### Categorización por Representación
```
RI ≥ 5%  → Producto ESTRELLA (crítico para negocio)
1% ≤ RI < 5% → Producto IMPORTANTE
0.1% ≤ RI < 1% → Producto REGULAR
RI < 0.1% → Producto MARGINAL (candidato a descontinuar)
```

**Ejemplo:**

| Producto | Ventas | Total | Rep. % | Categoría |
|----------|--------|-------|--------|-----------|
| Aceite A | 500,000 | 10M | 5.0% | **ESTRELLA** |
| Filtro B | 250,000 | 10M | 2.5% | **IMPORTANTE** |
| Batería C | 80,000 | 10M | 0.8% | **REGULAR** |
| Accesorio D | 5,000 | 10M | 0.05% | **MARGINAL** |

---

## 🔧 Implementación Técnica

### Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  UI/UX (Tkinter + TTK)                                 │ │
│  │  - Filtros jerárquicos (Dept/Grupo/Sub)                │ │
│  │  - Búsqueda de texto                                   │ │
│  │  - Paginación adaptativa                               │ │
│  │  - Exportación CSV                                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE LÓGICA DE NEGOCIO                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  pal/services/tra.py                                   │ │
│  │  - filter_ventas_tra()                                 │ │
│  │  - clasificar_rotacion_tra()                           │ │
│  │  - obtener_stock_ideal_tra()                           │ │
│  │  - calcular_porcentajes_representacion()               │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  pal/services/filters.py (Unificado)                   │ │
│  │  - filter_by_hierarchy()                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE ACCESO A DATOS                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  pal/infrastructure/database.py                        │ │
│  │  - obtener_ventas_por_producto_chunk()                 │ │
│  │  - fetch_data() con pool de conexiones                 │ │
│  │  - Thread-safe operations                              │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                        BASE DE DATOS                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  SQL Server                                            │ │
│  │  - Tablas: TR_INVENTARIO, MA_PRODUCTOS                 │ │
│  │  - Índices optimizados                                 │ │
│  │  - Vistas materializadas (opcional)                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Principales

#### 1. Servicio TRA (`pal/services/tra.py`)

**Funciones Principales:**

```python
def filter_ventas_tra(ventas, dept_code=None, group_code=None, 
                      sub_code=None, search_text="", 
                      filter_rotacion="TODAS", favoritos=None)
    """
    Filtra datos de ventas según múltiples criterios.
    Complejidad: O(n) donde n = número de productos
    """

def clasificar_rotacion_tra(ventas_data, total_ventas=None)
    """
    Clasifica productos en ALTA/MEDIA/BAJA según ABC.
    Complejidad: O(n log n) por ordenamiento
    """

def paginate_tra(datos, current_page, page_size)
    """
    Paginación eficiente de resultados.
    Complejidad: O(1) para acceso por índice
    """

def obtener_stock_ideal_tra(neto_ventas, dias_periodo=365, 
                            dias_buffer=30)
    """
    Calcula stock ideal basado en ventas históricas.
    Complejidad: O(1)
    """

def calcular_porcentajes_representacion(ventas_data)
    """
    Calcula % de representación de cada producto.
    Complejidad: O(n)
    """
```

#### 2. Filtros Unificados (`pal/services/filters.py`)

```python
def filter_by_hierarchy(records, dept_code=None, group_code=None, 
                       sub_code=None, *, get_dept, get_group, 
                       get_sub, missing_strategy="exclude")
    """
    Filtrado jerárquico unificado para TRA/MBRP/Stock.
    
    Estrategias:
    - "exclude": Excluye registros sin jerarquía (estricto)
    - "include": Incluye registros sin jerarquía (leniente)
    
    TRA usa "exclude" por defecto.
    """
```

### Consultas SQL Optimizadas

#### Consulta Principal TRA
```sql
-- Obtener ventas netas por producto con paginación
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
HAVING SUM(CASE 
    WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
    WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
    ELSE 0 
END) > 0
ORDER BY neto DESC
OFFSET @StartRow ROWS 
FETCH NEXT @ChunkSize ROWS ONLY;
```

**Índices Recomendados:**
```sql
-- Índice compuesto para performance óptima
CREATE NONCLUSTERED INDEX IX_TR_INVENTARIO_TRA 
ON TR_INVENTARIO (f_fecha, c_Concepto, c_Deposito)
INCLUDE (c_Codarticulo, n_Cantidad);

-- Índice en MA_PRODUCTOS para JOIN
CREATE NONCLUSTERED INDEX IX_MA_PRODUCTOS_CODIGO 
ON MA_PRODUCTOS (C_CODIGO)
INCLUDE (C_DESCRI, C_DEPARTAMENTO, C_GRUPO, C_SUBGRUPO);
```

### Optimizaciones de Performance

#### 1. Adaptive Chunking
Ajuste dinámico del tamaño de chunks según latencia:

```python
target_latency = 2.0  # 2 segundos por chunk
initial_chunk_size = 500

if chunk_latency < target_latency * 0.7:
    chunk_size = min(chunk_size * 1.5, max_chunk_size)
elif chunk_latency > target_latency * 1.3:
    chunk_size = max(chunk_size * 0.7, min_chunk_size)
```

#### 2. Cache con TTL
```python
cache_ttl = timedelta(hours=2)
cache_key = f"tra_{fecha_inicio}_{fecha_fin}_{sede}"

# Verificar cache antes de consultar BD
if cache válido:
    return datos_cacheados
else:
    datos = consultar_bd()
    guardar_en_cache(datos, ttl=cache_ttl)
    return datos
```

#### 3. Procesamiento Asíncrono
```python
# Carga en segundo plano sin bloquear UI
threading.Thread(
    target=_background_load_ventas_tra, 
    daemon=True, 
    name="tra_loader"
).start()
```

---

## 📊 Interpretación de Resultados

### Dashboard TRA - Vista Principal

```
┌──────────────────────────────────────────────────────────────┐
│  ANÁLISIS TRA - Período: 01/01/2025 - 31/03/2025             │
│  Sede: Cabudare (0301)                                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   RESUMEN EJECUTIVO                                          │
│  ├─ Total productos analizados: 2,450                        │
│  ├─ Ventas netas período: Bs. 15,500,000                     │
│  ├─ Productos ALTA rotación: 490 (20%)                       │
│  ├─ Productos MEDIA rotación: 490 (20%)                      │
│  └─ Productos BAJA rotación: 1,470 (60%)                     │
│                                                              │
│   TOP 10 PRODUCTOS (Representación)                          │
│  ┌─────────────────────────────────────────────────────┐     │
│  │ Código    │ Descripción      │ Rep. % │ Rotación    │     │
│  ├───────────┼──────────────────┼────────┼─────────────┤     │
│  │ A001      │ Aceite Motor     │ 8.5%   │ ALTA        │     │
│  │ B045      │ Filtro Aire      │ 6.2%   │ ALTA        │     │
│  │ C120      │ Batería 12V      │ 4.8%   │ ALTA        │     │
│  │ ...       │ ...              │ ...    │ ...         │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│   ALERTAS CRÍTICAS                                           │
│  ├─ 15 productos ALTA rotación con stock < 7 días            │
│  ├─ 45 productos BAJA rotación con >60 días de cobertura     │
│  └─ 8 productos sin movimiento en 90 días                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Indicadores Clave (KPIs)

| Indicador | Fórmula | Valor Ideal | Interpretación |
|-----------|---------|-------------|----------------|
| **Índice de Rotación** | (Ventas / Inventario Promedio) | >6 anual | Eficiencia del capital invertido |
| **Días de Cobertura** | (Inventario / Ventas Diarias) | 30-45 días | Nivel de stock vs demanda |
| **Fill Rate** | (Pedidos completos / Total pedidos) × 100 | >95% | Capacidad de satisfacer demanda |
| **Stock Obsoleto** | Productos sin movimiento >90 días | <5% | Riesgo de obsolescencia |

---

## 🛠️ Configuración y Uso

### Activación del Módulo

**Archivo:** `db_config.ini`
```ini
[Modules]
tra = True

[Debug]
tra = False  # Activar para logs detallados
```

### Uso Básico

1. **Seleccionar período de análisis** (7 días a 2 años)
2. **Elegir sede** (Cabudare, Guanare, Barinas)
3. **Hacer clic en "Cargar"** → Carga asíncrona en segundo plano
4. **Aplicar filtros** jerárquicos (Dept → Grupo → Sub)
5. **Buscar productos** específicos por código/descripción
6. **Exportar resultados** a CSV para análisis externo

### Filtros Disponibles

- **Departamento**: Filtro por línea de negocio
- **Grupo**: Sub-categoría dentro del departamento
- **Subgrupo**: Categoría más específica
- **Búsqueda de texto**: Código o descripción
- **Filtro por rotación**: TODAS / ALTA / MEDIA / BAJA

---

## 📈 Casos de Uso Prácticos

### Caso 1: Planificación de Compras Mensual

**Objetivo:** Generar orden de compra optimizada

**Pasos:**
1. Analizar TRA del último trimestre
2. Filtrar productos ALTA rotación
3. Identificar productos con DR < 15 días
4. Calcular cantidad óptima: `Stock Ideal - Stock Actual`
5. Priorizar por representación (%) y nivel de servicio

**Resultado esperado:** Lista priorizada de productos a comprar con cantidades exactas

### Caso 2: Liquidación de Inventario

**Objetivo:** Identificar productos para promoción

**Pasos:**
1. Filtrar productos BAJA rotación
2. Identificar productos con DR > 60 días
3. Analizar tendencia de ventas (últimos 3 meses vs histórico)
4. Calcular descuento necesario para agotar en 30 días

**Resultado esperado:** Catálogo de productos para campaña promocional

### Caso 3: Análisis de Portafolio

**Objetivo:** Evaluar líneas de producto

**Pasos:**
1. Agrupar por Departamento
2. Calcular representación % de cada departamento
3. Analizar rotación promedio por departamento
4. Comparar vs períodos anteriores

**Resultado esperado:** Reporte estratégico de líneas de negocio

---



## 📞 Soporte y Contacto

**Equipo de Desarrollo:** Sistema PAL  
**Versión del Módulo:** 2.0  
**Última actualización:** Octubre 2025  
**Documentación:** `docs/modulo_tra_completo.md`

---

**© 2025 Sistema PAL - Todos los derechos reservados**
