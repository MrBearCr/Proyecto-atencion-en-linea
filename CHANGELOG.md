# Changelog

Todas las modificaciones notables a este proyecto serán documentadas en este archivo.

## [1.6.2] - 2026-02-16

### 🔧 Cambiado
- **Corrección de Rango de Fechas en Módulo TRA**
  - **Razón**: Había una discrepancia entre el cálculo por defecto (31 días reales) y la selección manual de "30 días" (30 días reales), lo que causaba inconsistencias en la persistencia.
  - **Cambio**: Se ajustó la fecha de inicio por defecto a `ayer - 29 días` (30 días inclusive) y se actualizó la lógica de `dias_context` en el backend para ser siempre inclusive (`+1`).
- **Optimización de Unicidad de Productos (SELECT DISTINCT)**
  - **Archivo**: `pal/infrastructure/database.py` (función `obtener_ventas_por_producto_chunk`)
  - **Cambio**: Se agregó `DISTINCT` a la consulta de ventas para prevenir la duplicidad de registros cuando existen entradas redundantes en la tabla maestra de productos.

### 🐛 Corregido
- **Duplicidad en Persistencia de Rotación**
  - **Archivo**: `pal/services/tra.py`
  - **Solución**: Se añadió un control explícito de unicidad por código de producto antes de insertar en la tabla `pal_productos_rotacion`, eliminando cualquier posibilidad de duplicados en el "Nodo Maestro".

## [1.6.1] - 2026-02-16

### 🆕 Añadido
- **Filtros de Búsqueda en Reporte de Clientes**
  - **Razón**: Los usuarios necesitaban buscar clientes específicos (RIF o Nombre) dentro de rangos de fechas extensos sin procesar toda la base de datos.
  - **Cambio**: Implementado filtrado dinámico en SQL y nuevos campos de entrada en la UI.
- **Interactividad en Gráficos de Estadísticas**
  - **Cambio**: Implementación de tooltips dinámicos que muestran: Nombre del cliente, Mes, Total USD y desglose de facturas individuales al pasar el cursor sobre los puntos.
  - **Beneficio**: Análisis profundo de tendencias sin necesidad de generar reportes adicionales.

### 🔧 Cambiado
- **Arquitectura de Cálculo de USD (Cross-Server)**
  - **Archivo**: `pal/infrastructure/database.py`
  - **Razón**: Bases de datos en diferentes servidores (172.x y 192.x) impedían la unión de tablas vía SQL directo.
  - **Solución**: La aplicación ahora une `MA_PAGOS` y `FACTOR_DOLAR` en la capa de Python, gestionando factores del dólar de forma eficiente en memoria.
- **Carga por Chunks y Barra de Progreso Determinada**
  - **Cambio**: Migración de carga indeterminada a procesamiento por segmentos (5-10 días por chunk) con barra de progreso porcentual.
  - **Impacto**: UI fluida durante cargas pesadas y feedback visual preciso del avance.

### 🐛 Corregido
- **Error de Conversión de Fecha SQL (22007)**
  - **Problema**: Desajustes en configuraciones regionales de servidores producían errores de conversión de nvarchar a datetime.
  - **Solución**: Uso estricto de `CONVERT(DATETIME, ?, 120)` en todas las consultas de clientes.
- **Advertencias de Glifos (Font Glyphs)**
  - **Problema**: Emojis en tooltips producían errores `UserWarning: Glyph missing` en sistemas sin fuentes completas.
  - **Solución**: Reemplazados emojis por etiquetas de texto estándar.

## [1.6.0] - 2026-02-12

### 🆕 Añadido
- **Persistencia de Rotación (Sistema de Nodo Maestro)**
  - **Razón**: El cálculo de rotación ABC es una operación costosa que antes se repetía innecesariamente para cada usuario.
  - **Cambio**: Se implementó una tabla de persistencia `pal_productos_rotacion` que almacena el neto, promedio diario y clasificación ABC.
  - **Lógica de Nodo**: El primer usuario en realizar la carga del día actúa como "Nodo Maestro", persistiendo los resultados para que el resto de la organización los cargue instantáneamente.
  - **Beneficio**: Reducción del tiempo de carga en el módulo TRA de minutos a milisegundos para los usuarios subsiguientes y menor carga sobre el servidor SQL.
- **Inteligencia de Rotación en Quiebre de Stock**
  - **Cambio**: El monitor de quiebres ahora utiliza un `JOIN` con la tabla de persistencia para filtrar automáticamente productos de **Alta y Media Rotación**.
  - **Beneficio**: Alertas más precisas enfocadas exclusivamente en lo que realmente impacta al negocio, eliminando el ruido de productos de baja rotación.
- **Nueva Migración de Base de Datos**
  - **Archivo**: `docs/migrations/009_crear_tabla_rotacion_productos.sql`
  - **Detalle**: Crea la infraestructura necesaria para la persistencia compartida.

### 🔧 Cambiado
- **Optimización de Carga TRA en app.py**
  - **Cambio**: El método `_background_load_ventas_tra_fast` ahora busca datos persistidos frescos antes de iniciar la carga progresiva por chunks.
  - **Impacto**: Experiencia de usuario "Instant-On" cuando los datos ya han sido calculados por un colega o el sistema.

## [1.5.9] - 2026-02-12

### 🆕 Añadido
- **Módulo de Quiebre de Stock Optimizado**
  - **Razón**: Detección más rápida y directa de ventas perdidas sin depender del procesamiento pesado del módulo TRA.
  - **Cambio**: Implementada consulta SQL directa que cruza Stock 0 con ventas posteriores a la última fecha de compra (`Update_date`).
  - **Beneficio**: Alertas instantáneas y reducción drástica de consumo de recursos en el servidor.
- **Configuraciones Globales (Dashboard de Administración)**
  - **Cambio**: Transformación de la pestaña de Administración en un dashboard interactivo de tarjetas.
  - **Sub-módulos**: Sedes (Servidores), Depósitos (Almacenes tratables), Exclusiones, Usuarios, Roles y Auditoría.
  - **Beneficio**: Navegación más intuitiva y organizada, similar al módulo de Clientes.
- **Restauración de Gestión de Sedes (Servidores)**
  - **Razón**: Recuperar la funcionalidad de configuración de conexiones remotas (IP, BD, Credenciales) necesaria para el módulo de Clientes.
  - **Solución**: Nueva vista `SedesServidoresTab` integrada en Configuraciones Globales.

### 🔧 Cambiado
- **Renombrado de Módulo de Stock a "Quiebre de Stock"**
  - **Razón**: Reflejar con mayor precisión el propósito del módulo (detectar rupturas de inventario con demanda real).
  - **Impacto**: Actualizados menús, pestañas y columnas del sistema.

## [1.5.8] - 2026-02-11

### Agregado
- **Columna 'Marca' en reportes Excel de RI (TRA) y MBRP**
  - **Razón**: Visualización de la marca del producto directamente en las exportaciones para facilitar el análisis.
  - **Solución**: Inserción de la columna en la posición C (columna 3) y desplazamiento de columnas subsiguientes. Se implementó carga masiva optimizada desde `MA_PRODUCTOS`.
  - **Beneficio**: Reportes más completos y listos para toma de decisiones sin pasos manuales.
- **Ajuste de ancho para columna 'Último Proveedor'**
  - **Razón**: Los nombres de proveedores se visualizaban truncados en Excel.
  - **Solución**: Ajuste del ancho de columna a 50 unidades (~350 píxeles).
  - **Beneficio**: Identificación rápida y clara de los proveedores en los reportes de rotación.

### Mejorado
- **Rendimiento de Base de Datos para Módulo TRA**
  - **Problema**: Carga lenta en consultas con rangos de fechas superiores a 180 días.
  - **Solución**: Creación de índices optimizados en `TR_INVENTARIO` y `MA_PRODUCTOS`.
  - **Beneficio**: Mejora sustancial en la velocidad de respuesta de los módulos de análisis.
  - **Archivo de Migración**: `docs/migrations/008_optimizacion_indices_tra.sql`

## [1.5.7] - 2026-02-11

### Corregido
- **Filtros de jerarquía vacíos para usuarios no-admin**
  - **Problema**: Los filtros de departamento, grupo y subgrupo aparecían vacíos para usuarios no-administradores en su primer inicio de sesión, aunque la jerarquía se cargaba correctamente (547 elementos). Los diccionarios `tra_dept_dict`, `tra_group_dict` y `tra_sub_dict` permanecían vacíos.
  - **Razón**: La función `cargar_jerarquia_unificada()` tenía un early return que verificaba un flag (`jerarquias_unificadas_cargadas`) pero no verificaba que los diccionarios realmente tuvieran datos. En la segunda llamada (desde `_inicializar_modulos_paralelo`), salía inmediatamente dejando los diccionarios vacíos.
  - **Solución**: Modificado el early return para verificar tanto el flag como que los diccionarios tengan datos reales. Si el flag está en `True` pero los diccionarios están vacíos, resetea el flag y recarga la jerarquía.
  - **Beneficio**: Los filtros de jerarquía funcionan correctamente para todos los usuarios, independientemente del orden de inicio de sesión o permisos.

### Agregado
- **Logs de debug para filtros de jerarquía**
  - Agregados logs detallados en `on_tra_dept_selected`, `on_tra_group_selected` y `aplicar_filtro_tra` para facilitar el diagnóstico de problemas con filtros.
  - Los logs muestran el estado de los diccionarios, códigos seleccionados y flujo de filtrado.

## [1.5.6] - 2026-02-11

### 🔧 Cambiado
- **Optimización de carga de jerarquía y módulos**
  - **Archivo**: `app.py`
  - **Razón**: Mejora del rendimiento inicial y corrección de bloqueos en la UI.
  - **Beneficio**: Tiempos de carga reducidos (vistos 0.049s en caché) y filtros consistentes para todos los usuarios.

### 🐛 Corregido
- **Filtros vacíos para usuarios no-admin**
  - **Problema**: Los usuarios sin privilegios administrativos veían los filtros de jerarquía vacíos.
  - **Solución**: Se aseguró la actualización de la UI en `cargar_jerarquia_unificada` incluso si los datos ya están en memoria.
- **Sobreescritura de métodos paralelos**
  - **Problema**: Existían implementaciones duplicadas de `_inicializar_modulos_paralelo`.
  - **Solución**: Limpieza y consolidación del método para ejecución concurrente real.
- **Consistencia de estado en Login/Logout**
  - **Problema**: Comportamiento inconsistente entre diferentes sesiones de usuario.
  - **Solución**: Se añadió un reinicio de flags al cerrar sesión.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere al [Versionado Semántico](https://semver.org/lang/es/).

---


## [1.5.5] - 2026-02-11

### 🔧 Cambiado
- **Optimización de carga de jerarquía y módulos**
  - **Archivo**: `app.py`
  - **Razón**: Mejora del rendimiento inicial y corrección de bloqueos en la UI.
  - **Beneficio**: Tiempos de carga reducidos (vistos 0.049s en caché) y filtros consistentes para todos los usuarios.

### 🐛 Corregido
- **Filtros vacíos para usuarios no-admin**
  - **Problema**: Los usuarios sin privilegios administrativos veían los filtros de jerarquía vacíos.
  - **Solución**: Se aseguró la actualización de la UI en `cargar_jerarquia_unificada` incluso si los datos ya están en memoria.
- **Sobreescritura de métodos paralelos**
  - **Problema**: Existían implementaciones duplicadas de `_inicializar_modulos_paralelo`.
  - **Solución**: Limpieza y consolidación del método para ejecución concurrente real.
- **Consistencia de estado en Login/Logout**
  - **Problema**: Comportamiento inconsistente entre diferentes sesiones de usuario.
  - **Solución**: Se añadió un reinicio de flags al cerrar sesión.


## [1.5.4] - 10/02/2026

### 🆕 Añadido
- **Análisis de Ventas Perdidas en RI (TRA)**
  - Implementación de proyección de ventas perdidas para productos con stock cero.
  - Uso de `Update_date` (MA_PRODUCTOS) para inicio de disponibilidad.
  - Integración visual de mensajes en columnas existentes (Ventas, Días Fuera, UC, UV).
  - Resaltado en morado claro (`#E6E6FA`) para filas con quiebre de stock proyectado.

## [1.5.2] - 10/02/2026

### 🆕 Añadido

#### Actualizaciones Obligatorias durante el Login
- **Archivos modificados**: `app.py`
- **Funcionalidad**: Se implementó una comprobación forzada de actualizaciones al iniciar sesión.
- **Detalles**:
  - **Caché de 12 horas**: El sistema recuerda la última comprobación para evitar retrasos innecesarios en cada login.
  - **Bloqueo Mandatorio**: Si hay una actualización disponible, se detiene el inicio de sesión y se muestra un diálogo obligatorio.
  - **Notas de Versión**: El diálogo incluye el changelog detallado de la nueva versión.
  - **Botón de Actualización Forzada**: El usuario debe actualizar para poder entrar al sistema.
- **Razón**: Garantizar que todos los terminales utilicen la última versión crítica de la plataforma.

---

## [1.5.1] - 10/02/2026

### 🐛 Corregido

#### Disponibilidad del Gestor de Actualizaciones
- **Archivos modificados**: `app.py`
- **Problema**: El gestor de actualizaciones no estaba disponible inmediatamente después del login (esperaba 30 segundos), causando errores al verificar actualizaciones manualmente.
- **Solución**: 
  - Se modificó `_initialize_post_login_components` para instanciar el `UpdateManager` inmediatamente.
  - Se implementó un asistente `_ensure_update_manager` para inicialización a demanda (lazy loading).
  - Se difirió únicamente la verificación periódica (verificación de red) por 30 segundos para proteger el rendimiento del inicio.
- **Beneficio**: Los usuarios pueden verificar actualizaciones manualmente al instante después de iniciar sesión.

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
