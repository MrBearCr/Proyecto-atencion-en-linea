# Propuesta de Mejora del Índice de Movilidad (IM) en MBRP

## 1. Contexto

El módulo **MBRP (Movimiento de Baja Rotación de Producto)** utiliza hoy un **Índice de Movilidad (IM)** para identificar productos con baja o nula rotación. Este índice se ha vuelto clave en la toma de decisiones sobre liquidación, descontinuación y gestión de inventarios.

Sin embargo, en la práctica han surgido casos donde el comportamiento del IM **no refleja adecuadamente la realidad del negocio**, especialmente para productos de **alto valor y baja rotación “natural”** (ejemplo: neveras) frente a productos de **bajo valor y altísima rotación** (ejemplo: conectores, accesorios pequeños).

Este documento resume:
- Los **problemas actuales** del IM.
- Las **mejoras propuestas** al modelo.
- Los **beneficios concretos** que se obtendrían al implementarlas.

---

## 2. Problemas actuales del Índice de Movilidad

### 2.1 Comparación global de productos muy diferentes

Hoy el IM se calcula comparando todos los productos entre sí dentro de un mismo período (por ejemplo, 30 días y una sede). Esto genera distorsiones importantes:

- Un **conector** de bajo precio puede vender cientos o miles de unidades en 30 días.
- Una **nevera** de alto valor puede vender solo 2–4 unidades en el mismo período.

Aunque ambos productos estén cumpliendo su rol de negocio, el IM los ordena en una sola escala de “movilidad”, lo que provoca:

- Productos caros pero saludables (como una nevera que vende 3–4 unidades al mes) pueden aparecer con **IM bajo**, simplemente porque no pueden competir en volumen con accesorios de rotación masiva.
- La lectura “IM bajo = problema grave” deja de ser confiable para ciertos tipos de producto.

**Riesgo:**
- Toma de decisiones erróneas sobre productos de alto valor (ej. considerar liquidar un producto cuyo desempeño es normal dentro de su categoría).

---

### 2.2 Falta de contexto por categoría (familia de producto)

El IM actual no distingue entre **categorías** (departamento, grupo, subgrupo). Todos los productos entran en la misma “carrera” de movilidad.

Consecuencias:
- Una nevera compite contra conectores, baterías, filtros, etc.
- No tenemos una visibilidad clara de **cómo se comporta un producto dentro de su propia familia** (neveras vs neveras, conectores vs conectores).

**Riesgo:**
- Se pierde la referencia de “qué es buena rotación para este tipo de producto”.
- Se tiende a penalizar a categorías naturalmente lentas (línea blanca, repuestos caros) y a sobrevalorar categorías naturalmente rápidas (consumibles, accesorios).

---

### 2.3 Falta de comparación contra el propio historial del producto

El IM actual es una **foto de un solo período** (por ejemplo, últimos 30 días). No considera:

- Si el producto está mejor, igual o peor que en períodos anteriores.
- Cuál ha sido su **mejor desempeño histórico** en una ventana comparable (por ejemplo, su mejor mes en los últimos 12 meses).

Consecuencias:
- Un producto que siempre ha vendido poco (porque su mercado es pequeño) puede aparecer como “crítico” sin que haya un cambio real en su desempeño.
- Un producto que está cayendo fuertemente en ventas, pero que aún mantiene cierta rotación, puede no resaltarse lo suficiente.

**Riesgo:**
- Falta de capacidad para detectar **caídas de rendimiento** vs. comportamiento “normal” del producto.
- Dificultad para priorizar acciones correctivas en productos que realmente se están deteriorando.

---

## 3. Mejora propuesta del modelo de IM

La propuesta se basa en **enriquecer el IM actual**, agregando contexto de **categoría** y de **historial del propio producto**, sin perder la simplicidad para el usuario final.

### 3.1 IM por categoría (Departamento / Grupo / Subgrupo)

**Objetivo:** evitar comparar productos incomparables (neveras vs conectores) y medir la movilidad dentro de familias homogéneas.

**Idea:**
- Calcular el IM **dentro de la categoría** del producto (idealmente a nivel de **Subgrupo**; si no, al menos por **Grupo** o **Departamento**).
- El índice responde a: 
  > “¿Qué tan bien rota este producto frente a otros de su misma familia?”

**Impacto esperado:**
- Una nevera se compara contra otras neveras; si vende 4 unidades y la mejor de su subgrupo vende 5, su IM de categoría será alto.
- Un conector se compara contra otros conectores; allí sí es válido hablar de volúmenes altos y muy alta rotación.

---

### 3.2 IM contra el propio historial del producto (auto‑benchmark)

**Objetivo:** medir si un producto está hoy mejor o peor que en su **mejor desempeño histórico** en condiciones similares.

**Idea:**
- Para cada producto, analizar una ventana histórica (por ejemplo, últimos 12 meses).
- Dividir esa historia en períodos comparables (ej. ventanas de 30 días).
- Identificar el **máximo de unidades vendidas** en cualquier ventana de 30 días (su “mejor mes típico”).
- Comparar el período actual de 30 días contra ese máximo.

El índice responde a:
> “¿En qué porcentaje del **mejor nivel histórico** está hoy este producto?”

Ejemplo para una nevera:
- Mejor período de 30 días en los últimos 12 meses: 5 unidades.
- Período actual de 30 días: 4 unidades.
- El indicador histórico sería cercano al 80%, lo que sugiere un comportamiento **sano**.

**Impacto esperado:**
- Productos caros con baja rotación “natural” dejan de ser catalogados automáticamente como problemáticos si están dentro de su rango histórico normal.
- Productos que han caído respecto a su propio histórico se detectan rápidamente, aunque sigan vendiendo “algo”.

---

### 3.3 Índice combinado y matriz de decisión

Para no sobrecargar al usuario con múltiples indicadores, la propuesta es combinar las dos visiones en una lógica sencilla:

1. **IM por categoría**: cómo se comporta frente a productos similares.
2. **IM histórico (auto‑benchmark)**: cómo se comporta frente a su mejor versión histórica.

Con ambos índices, se puede:

- Mostrar ambos valores en un reporte más analítico, o
- Construir un **índice combinado** y una **matriz de decisión** que clasifique productos en categorías claras, por ejemplo:

- **Sano**: IM categoría alto + IM histórico alto.
- **Categoría débil**: IM categoría bajo + IM histórico alto (problema de familia, no de producto puntual).
- **Producto en deterioro**: IM categoría alto + IM histórico bajo (el producto está perdiendo fuerza frente a su propio pasado).
- **Crítico real**: IM categoría bajo + IM histórico bajo (producto claramente problemático y candidato a acciones fuertes de MBRP).

Esta matriz permite dirigir las decisiones de MBRP de forma más precisa y defensible.

---

## 4. Qué se resolvería con esta mejora

### 4.1 Decisiones más justas para productos de alto valor

- Las **neveras, equipos de alto costo y rotación lenta pero sana** dejarán de ser penalizadas simplemente porque venden menos unidades que un consumible.
- Se evitarán propuestas de **liquidación o descontinuación injustificadas** sobre productos que cumplen su función en el portafolio.

### 4.2 Mejor identificación de productos realmente problemáticos

- El sistema podrá diferenciar entre:
  - Productos que **siempre han vendido poco** (pero se mantienen estables).
  - Productos que **han caído** significativamente frente a su mejor comportamiento histórico.
- El foco del MBRP se moverá hacia productos que realmente están **perdiendo movilidad**, no solo hacia los que son inherentemente de baja rotación.

### 4.3 Visión más estratégica por categoría

- Al tener IM por categoría, será posible detectar:
  - Familias completas con problemas de rotación (ej. cierta línea de productos que está desactualizada o mal posicionada).
  - Productos dentro de una categoría que destacan positivamente y pueden ser candidatos a promoción, mayor stock o expansión a otras sedes.

### 4.4 Mayor confianza del negocio en el MBRP

- Al alinear mejor el indicador con la **realidad económica y comercial** de cada tipo de producto, las áreas de Compras, Comercial y Finanzas podrán:
  - Confiar más en las alertas del MBRP.
  - Justificar decisiones ante la gerencia con indicadores más intuitivos y defendibles.

---


Con estos cambios, el módulo MBRP evolucionará de un enfoque puramente volumétrico a un enfoque **más contextual, inteligente y alineado con la realidad del negocio**, preservando la simplicidad operativa pero aumentando considerablemente la calidad de la información para la toma de decisiones.