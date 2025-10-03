# Índice de Movilidad (IM) - Módulo MBRP

## Qué es el Índice de Movilidad

El **Índice de Movilidad (IM)** es un indicador que mide la actividad comercial de un producto en relación con otros productos del mismo período, expresado como un porcentaje del 0% al 100%.

### Interpretación del IM:
- **100%** = Producto con las mayores ventas del período (máxima movilidad)
- **0%** = Producto sin ventas o con ventas mínimas (sin movilidad)
- **50%** = Producto con movilidad media

## Cómo se Calcula el IM

### Fórmula:
```
IM = ((Ventas del Producto - Ventas Mínimas) / (Ventas Máximas - Ventas Mínimas)) × 100
```

### Parámetros utilizados:

1. **Ventas del Producto**: Cantidad neta vendida del producto específico en el período
2. **Ventas Mínimas**: Menores ventas encontradas entre todos los productos del período
3. **Ventas Máximas**: Mayores ventas encontradas entre todos los productos del período

### Proceso de Cálculo:

1. **Extracción de datos**:
   ```sql
   SELECT c_Codarticulo, SUM(CASE 
       WHEN c_Concepto = 'VEN' THEN n_Cantidad
       WHEN c_Concepto = 'DEV' THEN -n_Cantidad 
       ELSE 0 
   END) AS neto
   FROM TR_INVENTARIO 
   WHERE f_fecha BETWEEN fecha_inicio AND fecha_fin
   AND c_Deposito LIKE sede_codigo
   ```

2. **Normalización**:
   - Se encuentra el valor máximo y mínimo de ventas netas
   - Se aplica la fórmula de normalización min-max
   - El resultado se multiplica por 100 para obtener el porcentaje

3. **Casos especiales**:
   - Si todos los productos tienen las mismas ventas → IM = 50% para todos
   - Si un producto no tiene datos → IM = 0%

## Ejemplo Práctico

### Datos del período:
- Producto A: 1000 unidades vendidas
- Producto B: 500 unidades vendidas  
- Producto C: 100 unidades vendidas
- Producto D: 0 unidades vendidas

### Cálculos:
- **Ventas Máximas**: 1000 (Producto A)
- **Ventas Mínimas**: 0 (Producto D)
- **Rango**: 1000 - 0 = 1000

#### Resultados IM:
- **Producto A**: ((1000 - 0) / 1000) × 100 = **100%** ✅ (Alta movilidad)
- **Producto B**: ((500 - 0) / 1000) × 100 = **50%** (Movilidad media)
- **Producto C**: ((100 - 0) / 1000) × 100 = **10%** ⚠️ (Baja movilidad)
- **Producto D**: ((0 - 0) / 1000) × 100 = **0%** 🚨 (Sin movilidad)

## Aplicación en el Módulo MBRP

### Criterios de Clasificación MBRP:

- **🚨 SIN_MOVIMIENTO**: IM = 0% (productos críticos)
- **🔴 BAJA**: IM ≤ 10% (muy poca rotación)
- **🟡 MEDIA**: IM ≤ 30% (rotación moderadamente baja)
- **🟢 ALTA**: IM > 30% (se excluye normalmente del análisis MBRP)

### Colores en la Interface:

- **IM < 5%**: Rojo intenso + negrita (críticos)
- **IM 5-10%**: Rosa intenso + negrita (muy bajo)
- **IM 10-20%**: Naranja claro (bajo)
- **IM > 20%**: Gris claro (menos importante para MBRP)

### Filtrado Automático:
El módulo MBRP aplica un filtro automático con umbral del **30%**, mostrando solo productos con IM ≤ 30% para enfocar el análisis en productos de baja rotación.

## Ventajas del IM sobre Métricas Tradicionales

### vs. Clasificación ABC tradicional:
- **IM**: Normalizado 0-100%, fácil interpretación
- **ABC**: Basado en porcentajes acumulados, menos intuitivo

### vs. Análisis de Pareto:
- **IM**: Considera toda la distribución de ventas
- **Pareto**: Se enfoca solo en el 80/20

### vs. Ranking simple:
- **IM**: Proporciona distancia relativa entre productos
- **Ranking**: Solo orden, sin magnitud de diferencia

## Limitaciones y Consideraciones

### Limitaciones:
1. **Dependiente del período**: IM cambia según las fechas seleccionadas
2. **Sensible a outliers**: Productos con ventas extremas afectan la normalización
3. **Contextual**: No considera factores externos (estacionalidad, promociones)

### Recomendaciones de Uso:
- Usar períodos consistentes para comparaciones
- Complementar con análisis de tendencias temporales
- Considerar factores estacionales en la interpretación
- Revisar regularmente para detectar cambios en patrones

## Integración con Otras Métricas

El IM se complementa con:

### Última Venta:
- **Propósito**: Detectar productos estancados
- **Cálculo**: Días transcurridos desde la última transacción de venta
- **Integración**: Productos con IM bajo + muchos días sin venta = críticos

### Stock Actual:
- **Propósito**: Evaluar sobrestocking
- **Integración**: IM bajo + stock alto = candidatos a liquidación

### Reporte de Productos Críticos:
Combina todas las métricas para identificar productos que requieren acción inmediata:
- IM ≤ 5% AND Días sin venta > 90

## Implementación Técnica

### Archivo: `pal/services/mbrp.py`

#### Función Principal:
```python
def calcular_indice_movilidad(ventas_data: List, total_ventas_periodo: float = None) -> Dict[str, float]:
    # Extrae ventas por código
    ventas_por_codigo = {}
    for item in ventas_data:
        codigo = str(item[0])
        neto = float(item[5]) if item[5] is not None else 0.0
        ventas_por_codigo[codigo] = neto
    
    # Encuentra máximo y mínimo
    max_ventas = max(ventas_values)
    min_ventas = min(ventas_values)
    rango_ventas = max_ventas - min_ventas
    
    # Calcula IM normalizado
    for codigo, ventas in ventas_por_codigo.items():
        im = ((ventas - min_ventas) / rango_ventas) * 100
        indices_movilidad[codigo] = round(im, 1)
    
    return indices_movilidad
```

### Integración con Base de Datos:
- **Tabla**: `TR_INVENTARIO`
- **Campos**: `c_Codarticulo`, `n_Cantidad`, `c_Concepto`, `f_fecha`, `c_Deposito`
- **Filtros**: Conceptos 'VEN' y 'DEV', rango de fechas, depósito específico

## Casos de Uso Empresariales

### 1. Identificación de Productos Obsoletos
- Filtrar por IM < 5% y > 90 días sin venta
- Candidatos para descontinuación o liquidación

### 2. Optimización de Inventario
- IM bajo + stock alto = reducir pedidos
- IM alto + stock bajo = aumentar pedidos

### 3. Análisis de Portafolio
- Revisar productos con IM decreciente mes a mes
- Identificar tendencias de declive temprano

### 4. Estrategias Comerciales
- Productos IM 10-30%: promociones para reactivar
- Productos IM < 10%: evaluar descontinuación
- Productos IM 0%: acción inmediata requerida
