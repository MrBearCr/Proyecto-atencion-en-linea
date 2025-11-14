# Registro de Cambios (CHANGELOG)

Todos los cambios notables en el proyecto **PAL (Proyecto Atención en Línea)** serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere al [Versionado Semántico](https://semver.org/lang/es/).

---

## [Sin publicar] - En desarrollo

### 🆕 Añadido

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
