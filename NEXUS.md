

Este archivo proporciona orientación  al trabajar con código en este repositorio.

## Resumen del Proyecto

**NEXUS (Plataforma de Administracion Local)** es una aplicación de escritorio basada en Python para gestión de clientes, monitoreo de inventario e integración de mensajería por WhatsApp. Utiliza Tkinter para la interfaz gráfica y SQL Server como backend de base de datos.

**Propósito Principal:** Gestionar información de clientes con almacenamiento seguro de credenciales, monitorear niveles de stock con alertas inteligentes, analizar rotación de productos (módulo TRA), identificar productos de baja rotación (módulo MBRP) y enviar mensajes masivos por WhatsApp.

## Comandos Comunes

### Ejecutar la Aplicación
```powershell
# Iniciar la aplicación principal
python app.py

# Ejecutar en un entorno virtual (recomendado)
.venv\Scripts\activate
python app.py
```

### Pruebas
```powershell
# Probar funciones del pipeline MBRP de forma aislada
python test_mbrp_pipeline.py
```

### Gestión de Base de Datos
```powershell
# Verificar índices de base de datos
python check_indices.py
```

### Configuración del Entorno
```powershell
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# O instalar paquetes individuales:
pip install pyodbc cryptography keyring tkcalendar requests matplotlib win10toast Pillow bcrypt
```

## Descripción General de la Arquitectura

### Estructura por Capas

La aplicación sigue una **arquitectura por capas** con clara separación de responsabilidades:

```
┌─────────────────────────────────────────────┐
│  app.py (Punto de Entrada y Orquestación)  │
│  - Clase DatabaseApp                        │
│  - Inicialización de splash screen          │
│  - Sistema de módulos (flags dinámicos)     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  pal/ui/ (Capa de Presentación)            │
│  - header.py, sidebar.py, splash.py         │
│  - login.py, debug_console.py               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  pal/services/ (Lógica de Negocio)         │
│  - stock.py: Alertas y monitoreo inventario │
│  - tra.py: Análisis rotación productos (ABC)│
│  - mbrp.py: Detección baja rotación         │
│  - envios.py: Programador mensajes WhatsApp │
│  - filters.py: Filtros jerárquicos unif.    │
│  - exports.py: Exportación Excel/CSV        │
│  - cache.py: Capa de caché de descripciones │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  pal/core/ (Componentes Centrales)         │
│  - auth.py: AuthManager (basado en bcrypt)  │
│  - session.py: SessionManager               │
│  - permissions.py: Control acceso por roles │
│  - credentials.py: SecureCredentialsManager │
│  - audit.py: AuditLogger (archivo + BD)     │
│  - log.py: Sistema de logging centralizado  │
│  - chunks.py: AdaptiveChunkController       │
│  - errors.py: Enumeración ErrorCode         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  pal/infrastructure/ (Acceso a Datos)      │
│  - database.py: DatabaseManager             │
│    • Pool de conexiones para hilos          │
│    • Lógica de reintentos y resiliencia     │
│    • Integración SQL Server vía pyodbc      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Dependencias Externas                      │
│  - SQL Server (MA_PRODUCTOS, MA_DEPOPROD)   │
│  - WhatsApp Graph API                       │
│  - Windows Keyring (almacén credenciales)   │
└─────────────────────────────────────────────┘
```

### Patrones Arquitectónicos Clave

1. **Patrón de Capa de Servicio**: Lógica de negocio encapsulada en módulos `pal/services/`
2. **Patrón Repository**: `DatabaseManager` abstrae operaciones de base de datos
3. **Estrategia de Caché**: Múltiples capas de caché para descripciones, jerarquías y alertas
4. **Operaciones Thread-Safe**: Pool de conexiones con bloqueos para procesamiento paralelo
5. **Chunking Adaptativo**: Tamaño dinámico de chunks para consultas de grandes conjuntos de datos (módulos TRA/MBRP)

## Sistema de Módulos

La aplicación utiliza un **sistema de módulos dinámico** controlado centralmente desde la base de datos (tabla `pal_global_settings` para configuración global y `pal_usuarios_modulos` para permisos por usuario).

- **Módulos configurables**: `stock`, `tra`, `mbrp`, `envio_mensajes`, `estadisticas`, `calendario`, `admin`, `clientes`.

La configuración se gestiona vía interfaz: **Settings → Gestión de Usuarios** (para habilitar/deshabilitar módulos a usuarios específicos).

## Lógica de Negocio Crítica

### Módulo TRA (Análisis de Rotación de Productos)

**Propósito**: Clasificar productos usando el principio ABC/Pareto (regla 80/20) para optimizar compras e inventario.

**Persistencia de Rotación (Nodo Maestro)**:
Para evitar el recalculo constante de rotación (operación pesada en SQL), se implementó un sistema de persistencia compartida:
- **Tabla**: `pal_productos_rotacion` (almacena neto, promedio diario, clasificación y fecha).
- **Lógica de Nodo**: El primer usuario que carga el módulo TRA tras 24 horas actúa como **Nodo Maestro**, calcula la rotación y la persiste en la BD.
- **Carga Instantánea**: Los demás usuarios cargan directamente desde la tabla de persistencia, reduciendo el tiempo de carga de minutos a segundos.
- **Uso en Quiebres**: El módulo de Quiebre de Stock utiliza esta tabla para filtrar automáticamente y notificar solo productos de **Alta/Media Rotación**.

**Lógica de Clasificación**:
- **ALTA (Alta)**: Top 20% de productos que representan el 80% de las ventas
- **MEDIA (Media)**: Siguiente 20% que representa el 15% de las ventas  
- **BAJA (Baja)**: Restante 60% que representa el 5% de las ventas

**Funciones Clave** (`pal/services/tra.py`):
- `clasificar_rotacion_tra()`: Aplica clasificación ABC vía porcentaje acumulado
- `filter_ventas_tra()`: Filtra por departamento/grupo/subgrupo/texto de búsqueda
- `detectar_alertas_rotacion_alta()`: Cruza datos TRA con alertas de stock

**Flujo de Datos**:
1. Cargar datos de ventas vía `obtener_ventas_completas_tra()` con chunking adaptativo
2. Clasificar usando umbrales de porcentaje acumulado (80%, 95%)
3. Cachear resultados con TTL (2 horas)
4. Aplicar filtros jerárquicos para visualización

### Módulo MBRP (Productos de Baja Rotación)

**Propósito**: Identificar productos con ventas bajas/nulas para liberar capital y optimizar espacio de almacén.

**Métrica Clave**: **Índice de Movilidad (IM)** - escala normalizada 0-100% basada en actividad de ventas.

**Lógica de Clasificación**:
- **SIN_MOVIMIENTO** (IM = 0%): Sin ventas → Liquidación inmediata
- **BAJA** (0% < IM ≤ 10%): Muy baja actividad → Promoción agresiva
- **MEDIA** (10% < IM ≤ 30%): Moderadamente baja → Monitoreo requerido
- **ALTA** (IM > 30%): Rotación aceptable → Excluido del análisis MBRP

**Fórmula**:
```
IM = ((Ventas_Producto - Ventas_Mínimas) / (Ventas_Máximas - Ventas_Mínimas)) × 100
```

**Funciones Clave** (`pal/services/mbrp.py`):
- `calcular_indice_movilidad()`: Calcula IM usando normalización min-max
- `filtrar_productos_baja_rotacion()`: Filtra productos bajo umbral IM (por defecto 30%)
- `clasificar_rotacion_mbrp()`: Asigna categoría de rotación basada en IM

### Módulo Stock (Alertas de Inventario)


**Características Clave**:
- Carga paginada (300 registros iniciales, carga en segundo plano para conjunto completo)
- Filtrado jerárquico por departamento/grupo/subgrupo
- Sistema de favoritos con notificaciones toast de Windows
- Exclusiones departamentales (configurable)
- Visibilidad de stock entre ubicaciones (BARINAS, GUANARE, CDT)

**Flujo de Datos**:
1. Carga rápida inicial: 300 registros de `obtener_alertas_stock()`
2. Hilo en segundo plano: `_background_load_alertas_stock()` carga conjunto completo
3. Filtrado en tiempo real vía `aplicar_filtro_stock()`
4. Notificaciones toast para productos favoritos con stock crítico

## Arquitectura de Base de Datos

### Gestión de Conexiones

- **Conexión Primaria**: Hilo principal (`self.conn`)
- **Pool de Conexiones**: Pool thread-safe para operaciones paralelas (`_connection_pool`)
- **Bloqueos**: `_connect_lock` para conexiones serializadas, `_pool_lock` para acceso al pool
- **Auto-Reconexión**: `ensure_connection()` con lógica de reintentos
- **MARS Habilitado**: Múltiples Conjuntos de Resultados Activos para consultas concurrentes

### Prefijos de Esquema

Todas las tablas de la aplicación usan prefijo `pal_`:
- `pal_clientes`: Registros de clientes
- `pal_usuarios`: Cuentas de usuario (contraseñas hasheadas con bcrypt)
- `pal_roles`, `pal_permisos`: Sistema RBAC
- `pal_sesiones`: Sesiones de usuario activas con autenticación basada en tokens
- `pal_envios_programados`: Mensajes de WhatsApp programados
- `pal_auditoria_accesos`: Log de auditoría (login/logout/permisos)

**Tablas ERP Externas** (solo lectura):
- `MA_PRODUCTOS`: Datos maestros de productos (descripciones, jerarquías)
- `MA_DEPOPROD`: Niveles de stock por almacén/producto
- `VT_FACTURASDETALLE`: Detalles de transacciones de ventas

### Configuración

Conexión de base de datos almacenada en `db_config.ini`:
```ini
[Database]
server = NOMBRE_SERVIDOR
database = NOMBRE_BD
user = USUARIO  ; vacío para autenticación Windows

[Debug]
stock = True
tra = True
mbrp = True
db = True

; La configuración de módulos ahora reside en la base de datos.
tra = False
stock = False
mbrp = False
db = False
```

Credenciales almacenadas de forma segura vía **Windows Keyring** (no en texto plano).

## Modelo de Seguridad

### Autenticación (`pal/core/auth.py`)

- **Hashing de Contraseñas**: bcrypt con 12 rondas
- **Tokens de Sesión**: Tokens URL-safe de 48 bytes
- **Duración de Sesión**: 8 horas (480 minutos)
- **Política de Bloqueo**: 5 intentos fallidos → bloqueo de 15 minutos
- **Pista de Auditoría**: Todos los intentos de login registrados en `pal_auditoria_accesos`

### Autorización (`pal/core/permissions.py`)

Control de acceso basado en roles con permisos a nivel de módulo:
- **Formato de Permisos**: `MODULO.ACCION` (ej. `STOCK.exportar`, `TRA.visualizar`)
- **Anulación de Admin**: El nombre de usuario `admin` bypasea todas las verificaciones de permisos
- **Verificaciones de Permisos**: Antes de operaciones sensibles (exportar, eliminar, modificar)

### Almacenamiento de Credenciales (`pal/core/credentials.py`)

- **Cifrado Fernet**: Cifrado simétrico AES-128
- **Integración con Keyring**: Windows Credential Manager para claves
- **Campos Cifrados**: Token API de WhatsApp, contraseña de base de datos (si se almacena)
- **Rotación de Claves**: Soporte para re-cifrado con nuevas claves

## Optimizaciones de Rendimiento

### Chunking Adaptativo (`pal/core/chunks.py`)

Tamaño dinámico de chunks para consultas de grandes conjuntos de datos:
- **Tamaño Inicial**: 500 registros
- **Latencia Objetivo**: 2 segundos por chunk
- **Auto-Ajuste**: Crece/disminuye basado en rendimiento de consultas
- **Suavizado EMA**: Promedio móvil exponencial para prevenir oscilación
- **Cooldown**: Previene cambios rápidos de tamaño

**Uso en módulos TRA/MBRP**: Carga 180+ días de datos de ventas sin bloquear la interfaz.

### Estrategias de Caché

1. **Caché de Descripciones** (`pal/services/cache.py`): Descripciones de productos con evicción LRU
2. **Caché de Jerarquía**: Datos de departamento/grupo/subgrupo con TTL de 15 horas
3. **Caché de Favoritos**: Archivo JSON local para acceso instantáneo
4. **Caché TRA/MBRP**: Resultados de consultas cacheados por 2 horas con claves basadas en parámetros

### Arquitectura de Hilos

- **Hilo Principal**: Solo operaciones de interfaz (requisito de Tkinter)
- **Hilos en Segundo Plano**:
  - Carga de alertas de stock (`_background_load_alertas_stock`)
  - Carga de datos TRA (`_background_load_ventas_tra`)
  - Carga de datos MBRP (similar a TRA)
  - Monitoreo de favoritos (`monitorear_favoritos`)
  - Programador de mensajes WhatsApp
- **Actualizaciones Thread-Safe**: `root.after(0, callback)` para actualizaciones de interfaz desde hilos

## Sistema de Exportación (`pal/services/exports.py`)

Todas las funciones de exportación soportan:
- **Excel Multi-Hoja**: Datos, Resumen, Elementos críticos
- **Callbacks de Progreso**: Actualizaciones de progreso thread-safe
- **Ejecución Asíncrona**: Hilos en segundo plano para prevenir bloqueo de interfaz
- **Formato**: Formato condicional, auto-filtros, auto-ajuste de columnas
- **Verificaciones de Permisos**: Validación RBAC antes de exportar

**Funciones de Exportación**:
- `export_stock_excel()`: Alertas de stock con grupos de ubicación
- `export_tra_excel()`: Clasificación TRA con gráficos ABC (pastel/barras)
- `export_mbrp_excel()`: Análisis MBRP con métricas de rentabilidad

## Depuración

### Consola de Depuración (`pal/ui/debug_console.py`)

Consola de depuración flotante accesible vía **Ctrl+D** (cuando está habilitada):
- Streaming de logs en tiempo real
- Filtrable por nivel de log
- Historial de logs buscable
- Alternar visibilidad sin reiniciar

### Flags de Depuración a Nivel de Componente

Configurar en `db_config.ini` bajo `[Debug]`:
```ini
[Debug]
tra = True      # Habilitar logging verbose del módulo TRA
stock = True    # Habilitar logging verbose del módulo Stock
mbrp = True     # Habilitar logging verbose del módulo MBRP
db = True       # Habilitar logging de consultas de base de datos
```

**Acceso vía código**:
```python
self.tra_debug = self.debug_flags.get('tra', False)
if self.tra_debug:
    self.tra_debug_log("Mensaje de traza detallado", level="DEBUG")
```

### Sistema de Logging (`pal/core/log.py`)

Logging centralizado con filtrado basado en componentes:
- **Logger Global**: Log principal de la aplicación
- **Loggers de Componentes**: TRA, STOCK, MBRP, DB
- **Niveles de Log**: DEBUG, INFO, WARNING, ERROR, SUCCESS
- **Throttling**: Prevenir spam de logs con parámetro `throttle_key`
- **Rotación**: Rotación automática de archivos de log (límite 10MB)

## Patrones Comunes de Desarrollo

### Agregar un Nuevo Módulo de Servicio

1. Crear archivo de servicio en `pal/services/tu_modulo.py`
2. Implementar funciones centrales con inyección de dependencia de `DatabaseManager`
3. Agregar flag de módulo a `load_modules_config()` en `app.py`
4. Crear pestaña de interfaz en método `setup_modern_ui()`
5. Agregar verificaciones de permisos si es necesario
6. Actualizar `WARP.md` con documentación del nuevo módulo

### Implementar Consultas de Base de Datos

Siempre usar consultas parametrizadas vía `DatabaseManager`:
```python
# Correcto - seguro contra inyección SQL
results = self.db_manager.fetch_data(
    "SELECT * FROM pal_clientes WHERE numero_cliente = ?",
    (numero_cliente,)
)

# Incorrecto - nunca concatenar entrada de usuario
query = f"SELECT * FROM pal_clientes WHERE numero_cliente = '{numero_cliente}'"
```

### Actualizaciones Thread-Safe de Interfaz

Usar `root.after()` para actualizaciones de interfaz desde hilos en segundo plano:
```python
def tarea_segundo_plano():
    # Procesamiento pesado
    resultado = procesar_datos()
    
    # Actualizar interfaz de forma segura
    self.root.after(0, lambda: actualizar_ui(resultado))

threading.Thread(target=tarea_segundo_plano, daemon=True).start()
```

### Patrón de Filtrado Jerárquico

Reutilizar funciones de filtrado unificadas (`pal/services/filters.py`):
```python
from pal.services.filters import aplicar_filtro_jerarquico

datos_filtrados = aplicar_filtro_jerarquico(
    datos=todos_registros,
    dept_code=codigo_dept,
    group_code=codigo_group,
    sub_code=codigo_sub,
    producto_jerarquia=self.producto_jerarquia
)
```

## Notas Técnicas Importantes

### Consideraciones Específicas de Windows

- **Keyring**: Usa librería `keyring` con backend de Windows Credential Manager
- **Notificaciones Toast**: `win10toast` para notificaciones de bandeja del sistema (módulo Stock) ---OBSOLETO
- **Rutas**: Usar `os.path.join()` para compatibilidad multiplataforma (aunque esta es una app solo Windows)

### Integración con SQL Server

- **Driver**: Requiere Microsoft ODBC Driver for SQL Server
- **Autenticación**: Soporta tanto autenticación Windows (Trusted_Connection) como SQL
- **Cadena de Conexión**: Incluye `MARS_Connection=yes` para consultas concurrentes
- **Timeout**: Timeout de conexión de 30 segundos, configurable

### Gestión de Configuración

- **db_config.ini**: Conexión de base de datos, flags de módulos, configuración de depuración
- **Cachés JSON**: Favoritos, datos de jerarquía, resultados de consultas TRA/MBRP
- **Keyring**: Credenciales cifradas (token WhatsApp, contraseña BD)
- **Sin archivo .env**: La configuración usa formato INI en su lugar

### Integridad de Datos

- **Logging de Auditoría**: Todas las acciones de usuario registradas en `pal_auditoria_accesos`
- **Seguimiento de Sesiones**: Sesiones basadas en tokens con expiración
- **Códigos de Error**: Códigos de error estandarizados vía enum `ErrorCode`
- **Seguridad Transaccional**: `execute_query()` hace commit automáticamente, usar transacciones explícitas para operaciones multi-paso

## Dependencias Externas

### API de WhatsApp Business --- EN DESARROLLO / CHEQUEO CON META

- **Endpoint**: Facebook Graph API v18+
- **Almacenamiento de Token**: Cifrado en Windows Keyring
- **Características**: Mensajería masiva, envíos programados, soporte de plantillas
- **Configuración**: Settings → API WhatsApp

### Tablas de SQL Server

**La aplicación debe tener acceso de LECTURA a**:
- `MA_PRODUCTOS`: Maestro de productos (código, descripción, jerarquía)
- `MA_DEPOPROD`: Stock por almacén (código artículo, depósito, cantidad)
- `VT_FACTURASDETALLE`: Transacciones de ventas (para análisis TRA/MBRP)

**La aplicación crea y gestiona**:
- Todas las tablas con prefijo `pal_*` (ver sección Arquitectura de Base de Datos)

## Solución de Problemas Comunes

### "Driver ODBC no encontrado"
Instalar Microsoft ODBC Driver for SQL Server desde Microsoft Downloads.

### "Token expirado" (WhatsApp)
Regenerar token en Meta Business Suite y actualizar vía Settings → API WhatsApp.

### "Permiso denegado" para exportaciones
Verificar rol y permisos de usuario en tabla `pal_permisos`. El usuario admin bypasea todas las verificaciones.

### Consultas TRA/MBRP lentas
- Verificar que SQL Server tenga índices en columnas de fecha en `VT_FACTURASDETALLE`
- Reducir rango de fechas (probar 90 días en vez de 180)
- Verificar configuración `[Debug]` - deshabilitar logging verbose en producción

### Interfaz se congela durante operaciones grandes
Asegurar que las operaciones corran en hilos en segundo plano, no en el hilo principal. Verificar llamadas bloqueantes en manejadores de eventos de interfaz.

## Directrices de Desarrollo

### 1. Documentación de Cambios (CHANGELOG.md)

**IMPORTANTE**: Todos los cambios mayores deben documentarse en `CHANGELOG.md`.

**Estructura de entrada de cambio**:
```markdown
## [Versión] - YYYY-MM-DD

### 🆕 Añadido (Added)
- Descripción de nueva funcionalidad
- **Razón**: Por qué se agregó
- **Beneficio**: Qué mejora aporta

### 🔧 Cambiado (Changed)
- Descripción de modificación a funcionalidad existente
- **Razón**: Por qué se modificó
- **Impacto**: Qué afecta

### 🐛 Corregido (Fixed)
- Descripción del bug corregido
- **Problema**: Qué fallaba
- **Solución**: Cómo se corrigió
```

**Qué se considera un "cambio mayor"**:
- ✅ Nuevas funcionalidades o módulos
- ✅ Cambios en la arquitectura o flujo de datos
- ✅ Modificaciones a la base de datos (esquema, índices)
- ✅ Correcciones de bugs críticos
- ✅ Mejoras de rendimiento significativas
- ✅ Cambios en APIs externas (WhatsApp, SQL Server)
- ✅ Actualizaciones de dependencias importantes

**Qué NO documentar**:
- ❌ Cambios cosméticos menores (espaciado, formato)
- ❌ Correcciones de typos en comentarios
- ❌ Refactorizaciones internas sin cambio de funcionalidad

**Ejemplo práctico**:
```markdown
## [1.5.0] - 2025-01-12

### 🆕 Añadido
- **Jerarquía drill-down interactiva en exportación TRA/RI**
  - **Archivo**: `pal/services/exports.py`
  - **Razón**: Los usuarios necesitaban explorar datos jerárquicos (Depto → Grupo → Subgrupo) de forma interactiva en Excel
  - **Beneficio**: Navegación intuitiva con botones [+]/[-] para expandir/colapsar niveles, similar a la app
  - **Detalles técnicos**: Implementado usando `ws_h.row_dimensions.group()` con niveles de outline 1-2

### 🔧 Cambiado
- **Gráficos en reportes TRA ahora son adaptativos**
  - **Archivo**: `pal/services/exports.py`, función `_write_summary()`
  - **Razón**: Gráficos de pastel eran ilegibles con >8 categorías
  - **Impacto**: Automáticamente usa gráfico de barras si hay >8 elementos
  - **Beneficio**: Mejor legibilidad y experiencia de usuario

### 🐛 Corregido
- **Referencias de celda incorrectas en gráficos TRA**
  - **Problema**: Gráficos mostraban datos vacíos o incorrectos
  - **Causa**: Referencias incluían filas de encabezado de forma incorrecta
  - **Solución**: Corregidas referencias usando `Reference(min_row=header_row, max_row=last_row)`
```

### 2. Control de Versiones

**Estrategia de Branching**:
- `main`: Código estable en producción
- `develop`: Rama de desarrollo activo
- `feature/nombre-feature`: Nuevas funcionalidades
- `fix/nombre-bug`: Correcciones de bugs

**Commits**:
- Usar mensajes descriptivos 
- Formato: `[Módulo] Acción realizada`
- Ejemplo: `[TRA] Agregar jerarquía drill-down en exportación Excel`

**Tags de Versión**:
- Seguir Versionado Semántico: `MAJOR.MINOR.PATCH`
- `MAJOR`: Cambios incompatibles con versiones anteriores
- `MINOR`: Nueva funcionalidad compatible hacia atrás
- `PATCH`: Correcciones de bugs

### 3. Testing

**Antes de Commit**:
1. Verificar que la aplicación inicia sin errores: `python app.py`
2. Probar la funcionalidad modificada manualmente
3. Si hay tests automatizados, ejecutarlos: `python test_mbrp_pipeline.py`
4. Verificar que no se rompieron otras funcionalidades

**Testing de Módulos Específicos**:
- **TRA/MBRP**: Probar con diferentes rangos de fechas y filtros
- **Stock**: Verificar alertas y notificaciones
- **Exportaciones**: Abrir archivos Excel/CSV generados
- **Permisos**: Probar con diferentes roles de usuario

### 4. Documentación

**Cuándo actualizar documentación**:
- Al agregar nuevos módulos: Actualizar `WARP.md`
- Al cambiar comandos: Actualizar sección "Comandos Comunes"
- Al modificar arquitectura: Actualizar diagramas en `docs/arquitectura/`
- Al cambiar configuración: Actualizar `docs/configuracion/`

**Documentación en Código**:
- Usar docstrings en funciones públicas
- Comentar lógica de negocio compleja
- Documentar parámetros y valores de retorno
- Incluir ejemplos de uso cuando sea pertinente

### 5. Revisión de Código

**Checklist antes de merge**:
- [ ] Código sigue patrones establecidos en el proyecto
- [ ] No hay credenciales o secretos hardcodeados
- [ ] Consultas SQL usan parámetros (protección contra SQL injection)
- [ ] Operaciones pesadas corren en hilos secundarios
- [ ] Actualizaciones de UI usan `root.after(0, callback)`
- [ ] Logs apropiados para debugging (usar niveles correctos)
- [ ] CHANGELOG.md actualizado con cambios mayores
- [ ] Documentación relevante actualizada

### 6. Comunicación de Cambios

**Al completar una funcionalidad**:
1. Actualizar `CHANGELOG.md` con entrada detallada
2. Si afecta a usuarios: Preparar nota de release
3. Si cambia configuración: Documentar pasos de migración
4. Si hay breaking changes: Notificar con antelación

**Formato de Release Notes** (para usuarios finales):
```markdown
# Versión 1.5.0 - Enero 2025

## ✨ Novedades
- **Reportes RI interactivos**: Ahora puede expandir/colapsar departamentos y grupos en Excel

## 🛠️ Mejoras
- Nueva columna 'Marca' en reportes RI y MBRP (Excel)
- Ajuste de anchos de columna en exportaciones (Proveedor a 350px)
- Gráficos adaptativos según cantidad de categorías
- Mejor rendimiento en carga de datos TRA (180+ días) mediante índices

## 🐛 Correcciones
- Corregidos gráficos que no se generaban en algunos reportes

## 📝 Acción Requerida
- Ninguna. Esta actualización es completamente compatible.
```


