# Registro de Cambios (CHANGELOG)

Todos los cambios notables en el proyecto **PAL (Proyecto Atención en Línea)** serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere al [Versionado Semántico](https://semver.org/lang/es/).

---

## 1.5.0 - 10/02/2026

### 🆕 Añadido

#### Consolidación de Configuración de Módulos en BD
- **Archivos modificados**: `app.py`, `db_config.ini`, `docs/migrations/008_seed_global_modules.sql`
- **Razón**: Eliminar la redundancia entre el archivo `.ini` y la base de datos, centralizando la configuración.
- **Cambios**:
  - Eliminada la sección `[Modules]` de `db_config.ini`.
  - Refactorizada la carga inicial para diferir el inicio de servicios hasta después del login.
  - Implementada carga de configuración global de módulos desde `pal_global_settings`.
  - `_post_login_setup` ahora cruza permisos de usuario con habilitación global.
- **Beneficio**: Única fuente de verdad en la base de datos, facilidad de administración global y por usuario.

---

## 1.4.1 - 10/02/2026

### 🐛 Corregido

#### Visibilidad del Módulo 'Clientes'
- **Archivos modificados**: `app.py`
- **Problema**: El módulo 'clientes' permanecía visible incluso cuando se deshabilitaba para un usuario específico.
- **Solución**: Se incluyó el flag 'clientes' en la lógica de actualización de permisos post-login y se agregó a la configuración inicial por defecto.
- **Beneficio**: Respeto total de la configuración de visibilidad de módulos por usuario desde la base de datos.

---

## 1.4.0 - 4/02/2026


### 🆕 Añadido

#### Función "Ver proveedores" en RI y MBRP
- **Archivos modificados**: 
  - `pal/infrastructure/database.py` (nueva consulta SQL)
  - `pal/ui/tabs/tra.py` (habilitar modo árbol y clic derecho)
  - `pal/ui/tabs/mbrp.py` (habilitar modo árbol y clic derecho)
  - `app.py` (lógica de menú contextual y carga de hijos)
- **Razón**: Los usuarios necesitaban consultar rápidamente los proveedores asociados a un producto y sus últimas compras sin salir de los módulos de rotación.
- **Solución**: 
  - Se habilitó el modo jerárquico (árbol) en las tablas de RI (TRA) y MBRP.
  - Se implementó un menú contextual con clic derecho: "🔍 Ver proveedores".
  - Se agregó el campo `n_costo` (costo de compra) a la visualización.
  - Se implementó un sistema de permisos para controlar qué usuarios pueden usar la función.
- **Mejoras en MBRP**:
  - Sede predeterminada cambiada a **00 - ICH**.
  - Etiquetas de rotación actualizadas: **Baja**, **Baja-moderada**, **Critico**.
  - Estilos visuales ajustados y columna Ventas centrada.
- **Gestión de Sesión**:
  - Tiempo de expiración aumentado a **5 horas**.
- **Mejoras en Exportación**:
  - Inclusión de **Último Proveedor** en Excel de TRA y MBRP (requiere permiso).
- **Beneficio**: 
  - Acceso instantáneo a la cadena de suministro y costos por producto.
  - Visibilidad de números de compra, fechas y costos directamente en la tabla de análisis.
  - Control de seguridad mediante permisos RBAC.
- **Detalles técnicos**:
  - **Consulta**: Join entre `MA_PRODXPROV` y `MA_PROVEEDORES` incluyendo `n_costo`.
  - **Permisos**: Nuevos códigos `tra.ver_proveedores` y `mbrp.ver_proveedores`.
  - **Migración**: Creada `docs/migrations/007_agregar_permiso_ver_proveedores.sql`.

#### Filtro de Proveedor en Estadísticas TRA/RI
- **Archivos modificados**: 
  - `pal/ui/tabs/stats.py` (lógica de filtrado y estado)
- **Razón**: Al seleccionar un proveedor en TRA, las estadísticas mostraban productos de todos los proveedores en lugar de solo los del proveedor seleccionado.
- **Problema**: Vista inicial mostraba "Proveedor vs Resto de Proveedores", haciendo imposible drill-down cuando el proveedor tenía baja participación de mercado.
- **Solución**: 
  - Iniciar directamente en vista de departamentos para el proveedor seleccionado
  - Mejorar lógica de selección de datos para respetar filtro de proveedor
  - Agregar detección de cambios de proveedor para resetear estado de estadísticas
- **Beneficio**: 
  - Los usuarios ahora pueden analizar cualquier proveedor sin importar su participación de mercado
  - Drill-down inmediato: Departamento → Grupo → Subgrupo → Producto
  - Coherencia total entre filtro TRA y visualización estadística
- **Detalles técnicos**:
  - **Nueva lógica de estado**: `_stats_last_proveedor_key` para detectar cambios
  - **Vista inicial**: `level: "dept"` con `subset: "provider"` para proveedor seleccionado
  - **Breadcrumb**: Muestra "Proveedor: [Nombre] / [Departamento]" durante navegación

#### Permiso Granular para Ver Costo y Utilidad en Reportes
- **Archivos modificados**: 
  - `pal/infrastructure/database.py` (sistema de permisos)
  - `pal/services/exports.py` (exportaciones)
  - `app.py` (llamadas a exportación)
- **Razón**: Necesidad de controlar qué usuarios pueden visualizar información sensible de costos y márgenes de utilidad en los reportes exportados
- **Solución**: Se implementó un nuevo permiso `ver_costo_utilidad` que afecta a todos los módulos de reporte (TRA, MBRP, Stock)
- **Beneficio**: 
  - Control granular de acceso a información financiera sensible
  - Columnas condicionales en Excel según permisos del usuario
  - Mayor seguridad y cumplimiento de políticas empresariales
- **Detalles técnicos**:
  - **Nuevos permisos**: `tra.ver_costo_utilidad`, `mbrp.ver_costo_utilidad`, `stock.ver_costo_utilidad`
  - **Campos agregados**: `Precio`, `Costo`, `Utilidad %`
  - **Cálculo de utilidad**: `((precio - costo) / costo) * 100`
  - **Origen de datos**: `n_precio1` y `n_costoact` de tabla `MA_PRODUCTOS`
  - **Asignación por defecto**: Solo roles Administrador y Supervisor
  - **Queries modificados**: `obtener_ventas_por_producto_chunk()` ahora incluye precio y costo en SELECT

### 🔧 Cambiado

#### Etiqueta "Días de Stock" en módulo TRA (RI)
- **Archivos modificados**:
  - `pal/ui/tabs/tra.py`
  - `docs/modulo_tra_completo.md`
- **Razón**: La etiqueta "Días Restantes" generaba dudas sobre el significado exacto; "Días de Stock" comunica mejor que el indicador se refiere a días de cobertura de inventario.
- **Cambio**: En la grilla de TRA y en la documentación técnica se renombró "Días Restantes" a "Días de Stock", manteniendo la fórmula `Stock Actual / PDV`.
- **Impacto**: Mejora de claridad para usuarios finales sin afectar la lógica de cálculo.

#### "Días de Stock" en módulo MBRP
- **Archivos modificados**:
  - `pal/ui/tabs/mbrp.py`
  - `app.py`
  - `docs/modulo_mbrp_completo.md`
- **Razón**: Se necesitaba la misma métrica de cobertura de inventario que en TRA para analizar productos de baja rotación, utilizando el rango de fechas específico del módulo MBRP.
- **Cambio**: Se agregó una nueva columna "Días de Stock" en la grilla MBRP y se reutilizó la lógica existente (`Stock Actual / PDV`) tomando como base las ventas netas del período MBRP.
- **Impacto**: Permite identificar rápidamente sobrestocks (muchos días de stock con IM bajo) dentro del portafolio de baja rotación.

#### Descripciones cortas de producto en toda la app
- **Archivos modificados**:
  - `pal/infrastructure/database.py`
  - `pal/services/stock.py`
  - `app.py`
- **Razón**: Las descripciones largas (`C_DESCRI`) generaban textos muy extensos en listados, alertas, mensajes de WhatsApp y gráficos.
- **Cambio**: Todas las consultas que mostraban descripciones de producto pasan a usar `cu_descripcion_corta` (o `SIN DESCRIPCIÓN` si viene nulo/vacío), eliminando el uso de `C_DESCRI` como texto principal.
- **Impacto**: Interfaces más legibles, etiquetas más cortas en estadísticas y mensajes de WhatsApp con textos más compactos.

#### Mejora de gráficos en pestaña Estadísticas (TRA/RI)
- **Archivos modificados**:
  - `pal/ui/tabs/stats.py`
- **Razón**: Con muchos segmentos pequeños (p.ej. varios grupos con 0,2%), se necesitaba una forma alternativa de visualizar la distribución sin perder legibilidad ni interacción.
- **Cambios**:
-  - Se mantiene el gráfico de pastel con etiquetas visibles en todos los segmentos, complementado por una tabla de detalle lateral.
-  - Se agregó un selector de tipo de gráfico para alternar entre "Pie (porcentaje)" y "Barras horizontales"; las barras se muestran en orden descendente y son clicables para drill-down (Departamento → Grupo → Subgrupo → Producto, limitado a top 25).
- **Impacto**: Mejora de legibilidad y navegación en las estadísticas, ofreciendo una vista alternativa más cómoda cuando hay muchos segmentos.

#### Queries SQL Optimizados con Campos de Precio y Costo
- **Archivos modificados**: `pal/infrastructure/database.py`
- **Razón**: Necesidad de traer precio y costo desde origen de datos para cálculos de utilidad
- **Cambio**: Agregados campos `COALESCE(p.n_precio1, 0) AS precio` y `COALESCE(p.n_costoact, 0) AS costo` en CTEs de ventas
- **Impacto**: Los datos ahora incluyen 2 campos adicionales (posiciones 6 y 7 en tuplas de resultados)

#### Firmas de Funciones de Exportación Extendidas
- **Archivos modificados**: `pal/services/exports.py`
- **Funciones afectadas**: `export_tra_excel()`, `export_mbrp_excel()` (Stock pendiente)
- **Nuevos parámetros**: `permissions_manager`, `current_user_id`
- **Compatibilidad**: Parámetros opcionales, mantiene compatibilidad hacia atrás

---

## [1.0.1] - 2025-01-12

### 🆕 Añadido

#### Jerarquía Drill-Down Interactiva en Exportación TRA/RI
- **Archivos modificados**: `pal/services/exports.py`
- **Razón**: Los usuarios necesitaban explorar datos jerárquicos (Departamento → Grupo → Subgrupo) de forma interactiva en Excel
- **Beneficio**: Navegación intuitiva con botones [+]/[-] para expandir/colapsar niveles, similar a la app
- **Detalles técnicos**: Implementado usando agrupación de filas con 3 niveles de outline

#### Instrucciones Visuales en Reportes Excel
- **Archivos modificados**: `pal/services/exports.py`
- **Razón**: Usuarios no encontraban los controles de agrupación
- **Beneficio**: Panel de instrucciones con iconos visuales y pasos claros

### 🔧 Cambiado

#### Gráficos Adaptativos en Reportes TRA
- **Archivos modificados**: `pal/services/exports.py`
- **Razón**: Gráficos de pastel eran ilegibles con >8 categorías
- **Cambio**: Lógica automática (≤8 → pastel, >8 → barras)
- **Beneficio**: Mejor legibilidad visual

### 🐛 Corregido

#### Referencias de Celda Incorrectas en Gráficos TRA
- **Problema**: Gráficos no se generaban o mostraban datos vacíos
- **Solución**: Corregidas referencias de `Reference()` y agregada tabla resumida auxiliar
- **Impacto**: Gráficos ahora funcionan en todos los casos

#### Símbolos de Esquema No Visibles
- **Problema**: Botones [+]/[-] no visibles en algunas instalaciones de Excel
- **Solución**: Forzar propiedades de outline: `ws_h.sheet_view.showOutlineSymbols = True`

### 📚 Documentación

- **WARP.md**: Traducido completamente a español y agregadas directrices de desarrollo
- **CHANGELOG.md**: Creado este archivo para documentar cambios futuros

---

## [1.0.0] - 2025-01-12 🎉

**Primera versión beta en producción**

### 🎯 Funcionalidades Principales

- **Módulo TRA**: Análisis de rotación ABC/Pareto (80/20)
- **Módulo MBRP**: Índice de Movilidad para productos de baja rotación
- **Módulo Stock**: Alertas multinivel (Crítica/Media/Leve) con favoritos
- **Mensajería WhatsApp**: Envío masivo y programado (Graph API v18+)
- **Seguridad**: Autenticación bcrypt + RBAC + Fernet encryption
- **Auditoría**: Log dual (archivo + BD) con rotación automática
- **Exportación**: Excel multi-hoja con gráficos y formato profesional
- **Rendimiento**: Chunking adaptativo, caché multinivel, threading

### 📝 Requisitos

- Windows 10/11
- Python 3.8+
- SQL Server 2016+
- ODBC Driver for SQL Server

### 🚀 Estado

**Fase**: Beta en Producción  
**Estabilidad**: Funcional, en uso por usuarios finales

---

## Convenciones

### Tipos de Cambios
- 🆕 **Añadido**: Nueva funcionalidad
- 🔧 **Cambiado**: Modificación a funcionalidad existente
- 🐛 **Corregido**: Corrección de bugs
- 🔒 **Seguridad**: Vulnerabilidades
- 📚 **Documentación**: Solo documentación
- ⚡ **Rendimiento**: Optimizaciones

### Versionado Semántico (MAJOR.MINOR.PATCH)
- **MAJOR**: Breaking changes
- **MINOR**: Nueva funcionalidad compatible
- **PATCH**: Corrección de bugs

---

**Última actualización**: 2025-01-12
