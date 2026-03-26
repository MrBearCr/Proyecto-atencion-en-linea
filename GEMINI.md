# GEMINI.md - Contexto de Instrucción del Proyecto PAL

## Visión General del Proyecto
Este proyecto es una aplicación de escritorio desarrollada en **Python** para la **Gestión de Clientes y Logística (PAL)**. Su propósito principal es administrar eficientemente la información de clientes, el stock global y la cadena de suministro (abastecimiento), integrándose con una base de datos **SQL Server** y proporcionando capacidades de comunicación masiva a través de **WhatsApp**.

### Tecnologías Principales
*   **Lenguaje:** Python 3.x
*   **Interfaz Gráfica (GUI):** Tkinter (con temas modernos y componentes personalizados)
*   **Base de Datos:** SQL Server (mediante `pyodbc`)
*   **Seguridad y Cifrado:** `cryptography` (Fernet), `keyring` (para almacenamiento seguro de claves en el sistema), `bcrypt` (para hashes de contraseñas).
*   **Pruebas:** `pytest`, `pytest-cov`.
*   **Otras:** `requests` (comunicación API), `matplotlib` (gráficos de estadísticas), `Pillow` (manejo de imágenes).

### Arquitectura del Sistema
El proyecto sigue una estructura modular dentro del directorio `pal/`:
*   `pal/core/`: Lógica de negocio fundamental (autenticación, auditoría, gestión de credenciales seguras, licencias, sesiones y actualizaciones).
*   `pal/infrastructure/`: Capa de acceso a datos (`database.py`), manejo de drivers ODBC y esquemas de base de datos.
*   `pal/services/`: Servicios especializados (Abastecimiento, Rotación de inventario TRA/MBRP, Gestión de Stock, Notificaciones de WhatsApp, Exportaciones a Excel).
*   `pal/ui/`: Componentes de la interfaz de usuario (tabs, popups, temas y pantallas de inicio/login).
*   `app.py`: Punto de entrada principal que orquestra la inicialización de la aplicación y el bucle principal de la GUI.

---

## Instalación y Ejecución

### Requisitos Previos
*   Python 3.x instalado.
*   Servidor SQL Server accesible.
*   Driver ODBC de SQL Server instalado (la aplicación detecta automáticamente la mejor versión disponible).

### Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### Configuración de la Base de Datos
La aplicación utiliza un archivo `db_config.ini` en la raíz para almacenar la configuración del servidor, base de datos y usuario. **Importante:** Estos valores se almacenan **encriptados** por motivos de seguridad, utilizando una clave generada dinámicamente y guardada en el `keyring` del sistema operativo.

### Ejecución de la Aplicación
```bash
python app.py
```

---

## Convenciones de Desarrollo

### Seguridad y Credenciales
*   **Nunca** almacenes credenciales en texto plano. Utiliza siempre `SecureCredentialsManager` (`pal/core/credentials.py`) para cifrar/descifrar datos sensibles antes de guardarlos en archivos de configuración.
*   Las contraseñas de usuario en la base de datos se manejan con hashes `bcrypt`.

### Manejo de Base de Datos
*   El `DatabaseManager` (`pal/infrastructure/database.py`) se encarga de la creación automática de tablas y migraciones de esquema al iniciar la conexión.
*   Se utiliza un sistema de pools de conexión por hilo para garantizar que las operaciones en segundo plano (como la carga de datos masivos o alertas) no bloqueen la interfaz de usuario.

### Estilo de Código y Errores
*   Sigue las guías de estilo PEP 8.
*   Utiliza el sistema de códigos de error definido en `pal/core/errors.py` para proporcionar retroalimentación precisa al usuario y facilitar el soporte técnico.
*   Toda acción crítica debe ser registrada a través del `AuditLogger` para mantener un historial de eventos.

### Pruebas
*   Ejecuta las pruebas unitarias utilizando `pytest`.
*   Asegúrate de que las nuevas funcionalidades incluyan sus respectivos casos de prueba en el directorio `tests/`.

---

## Sistema de Jerarquía de Productos

El sistema implementa una jerarquía de **3 niveles** para clasificar productos, compartida por todos los módulos de inventario (Stock, TRA, MBRP):

### Niveles Jerárquicos
```
Departamento (Nivel 1)
└── Grupo (Nivel 2)
    └── Subgrupo (Nivel 3)
```

### Tablas de Base de Datos
- **`MA_DEPARTAMENTOS`**: Código (`C_CODIGO`) + Descripción (`C_DESCRIPCIO`)
- **`MA_GRUPOS`**: Código (`C_CODIGO`) + Descripción (`C_DESCRIPCIO`) + FK a departamento (`C_DEPARTAMENTO`)
- **`MA_SUBGRUPOS`**: Código (`C_CODIGO`) + Descripción (`C_DESCRIPCIO`) + FK a departamento (`C_IN_DEPARTAMENTO`) + FK a grupo (`C_IN_GRUPO`)

### Implementación en Código

#### 1. Diccionarios de Jerarquía (en `app.py`)
La aplicación mantiene diccionarios unificados para TRA y MBRP:

```python
# Estructura de diccionarios jerárquicos
self.tra_dept_dict = {desc: cod}           # {"Electrónica": "01", "Ropa": "02"}
self.tra_group_dict = {dept_cod: {desc: cod}}  # {"01": {"Celulares": "0101", "Laptops": "0102"}}
self.tra_sub_dict = {f"{dept}|{grp}": {desc: cod}}  # {"01|0101": {"Smartphones": "010101"}}
```

#### 2. Carga de Jerarquía Unificada (`cargar_jerarquia_unificada()`)
**Ubicación**: `app.py:5298-5470`

Carga jerarquías de TRA y MBRP con una sola consulta optimizada JOIN:
- Verifica caché local (`jerarquia_cache.json`) antes de consultar BD
- Usa consulta única LEFT JOIN entre departamentos, grupos y subgrupos
- Aplica a ambos módulos (TRA y MBRP comparten la misma jerarquía)

#### 3. Filtros Jerárquicos (`pal/services/filters.py`)
**Funciones principales**:
- `match_hierarchy_from_map()`: Coincide jerarquía usando un mapa de código→(dep,grp,sub)
- `match_hierarchy_from_record()`: Coincide jerarquía leyendo campos directamente del registro
- `filter_by_hierarchy()`: Aplica filtro jerárquico unificado sobre una colección

**Parámetro `missing_strategy`**:
- `"exclude"` (default): Productos sin jerarquía definida se excluyen cuando hay filtros activos
- `"include"`: Productos sin jerarquía se incluyen

#### 4. Caché de Jerarquía (`pal/services/stock.py`)
**Funciones**:
- `load_all_jerarquia()`: Carga mapeo completo desde BD o caché local
- `build_producto_jerarquia()`: Filtra jerarquía solo con códigos en alerta
- Archivo de caché: `productos_jerarquia_cache.json`
- TTL del caché: Variable (típicamente 24 horas)

#### 5. Asociación Producto→Jerarquía
En `MA_PRODUCTOS`, cada producto tiene:
- `C_DEPARTAMENTO`: Código del departamento
- `C_GRUPO`: Código del grupo
- `C_SUBGRUPO`: Código del subgrupo

Para obtener la jerarquía de un producto:
```python
# Desde el diccionario all_jerarquia (cargado en memoria)
jerarquia = self.all_jerarquia.get(codigo_producto)  # Retorna: (dep, grp, sub)
```

---

## Sistema de Descripciones de Productos

### Tipos de Descripción
El sistema maneja **dos tipos** de descripción para cada producto:

1. **Descripción Corta** (`cu_descripcion_corta`)
   - Usada para mostrar en listas, combos y notificaciones
   - Límite: ~100 caracteres típicamente
   - Columna en BD: `MA_PRODUCTOS.cu_descripcion_corta`

2. **Descripción Larga** (`C_DESCRI`)
   - Descripción completa del producto
   - Usada en reportes detallados y exportaciones
   - Columna en BD: `MA_PRODUCTOS.C_DESCRI`

### Obtener Descripciones

#### Método 1: Desde BD (Individual)
**Ubicación**: `app.py:562-573` y `app.py:10371-10381`

```python
def obtener_descripcion_producto(self, codigo: str) -> Optional[str]:
    """Obtiene la descripción corta de un producto desde la base de datos."""
    result = self.db_manager.fetch_data(
        "SELECT COALESCE(cu_descripcion_corta, 'SIN DESCRIPCIÓN') FROM MA_PRODUCTOS WHERE C_CODIGO = ?", 
        (codigo,)
    )
    return str(result[0][0]) if result and result[0][0] else None
```

#### Método 2: Batch (Múltiples Productos)
**Ejemplo**: `pal/services/abastecimiento.py:382-385`

```python
descripciones = {}  # {codigo: {corta: 'desc', larga: 'desc'}}
for r_cod, r_dep, r_qty, r_desc_corta, r_desc_larga in res_stock_sedes:
    descripciones[r_cod] = {
        "corta": str(r_desc_corta or r_desc_larga or "SIN DESCRIPCIÓN"),
        "larga": str(r_desc_larga or "SIN DESCRIPCIÓN")
    }
```

#### Método 3: Caché Local (`pal/services/cache.py`)
```python
from pal.services.cache import CacheDescripciones

cache = CacheDescripciones(ttl=3600)  # 1 hora de TTL
cache.guardar(codigo, descripcion)
desc = cache.obtener(codigo)  # Retorna None si expiró
```

### Fallback de Descripciones
El sistema aplica esta prioridad cuando una descripción no está disponible:
1. Descripción corta (`cu_descripcion_corta`)
2. Descripción larga (`C_DESCRI`)
3. Texto fallback: `"SIN DESCRIPCIÓN"`

---

## Módulos del Sistema (Detalle)

### 1. Módulo Core (`pal/core/`)

#### `auth.py` - Autenticación
- `AuthManager`: Gestión de inicio de sesión, verificación de credenciales
- Uso de `bcrypt` para hashes de contraseñas
- Integración con sistema de permisos

#### `credentials.py` - Credenciales Seguras
- `SecureCredentialsManager`: Cifrado/descifrado usando Fernet
- Almacenamiento de claves en `keyring` del sistema operativo
- **Nunca** almacenar contraseñas en texto plano

#### `errors.py` - Sistema de Errores
- `ErrorCode` (Enum): Códigos de error corporativos organizados por categoría:
  - 1000-1999: Errores de base de datos
  - 2000-2999: Errores de validación
  - 3000-3999: Errores de cifrado
  - 4000-4999: Errores de API
  - 5000-5999: Autenticación y sesión
  - 6000-6999: Configuración
- `PalError`: Excepción base con contexto, excepción original y traceback

#### `audit.py` / `audit_db.py` - Auditoría
- `AuditLogger`: Registro de eventos críticos del sistema
- Logs con timestamps, nivel de severidad y mensajes
- `AuditDBLogger`: Registro de auditoría en base de datos

#### `license.py` - Licenciamiento
- Validación de licencias de usuario
- Soporte para licencias online/offline
- Gestión de períodos de gracia

#### `session.py` - Gestión de Sesiones
- Manejo de sesiones de usuario con timeout por inactividad
- Almacenamiento seguro de datos de sesión

#### `updater.py` - Actualizaciones
- Sistema de actualización automática de la aplicación
- Descarga de nuevas versiones desde repositorio
- Verificación de integridad de actualizaciones

#### `permissions.py` - Permisos
- Sistema RBAC (Role-Based Access Control)
- Verificación de permisos por módulo y acción

#### `config_manager.py` - Configuración
- Gestión centralizada de configuración de la aplicación
- Validación de parámetros de configuración

#### `user_management.py` - Gestión de Usuarios
- CRUD de usuarios del sistema
- Asignación de roles y permisos

### 2. Infrastructure (`pal/infrastructure/`)

#### `database.py` - DatabaseManager
**Funciones principales**:
- `fetch_data(query, params)`: Ejecuta SELECT y retorna filas
- `execute_query(query, params)`: Ejecuta INSERT/UPDATE/DELETE
- `ensure_connection()`: Verifica y restablece conexión si es necesario
- Creación automática de tablas PAL al inicializar
- Pool de conexiones por hilo

**Tablas Automáticas**:
- `pal_sugerencias_transferencia`: Sugerencias de abastecimiento
- `pal_productos_no_trasladables`: Lista roja de productos
- `pal_historial_ejecuciones`: Historial de procesos
- `pal_audit_log`: Logs de auditoría
- `pal_permisos`: Permisos de usuarios
- `pal_usuarios`: Usuarios del sistema
- `pal_modulos`: Módulos habilitados
- `pal_configuracion_abastecimiento`: Configuración por sede
- `pal_whatsapp_config`: Configuración de WhatsApp
- `pal_whatsapp_templates`: Plantillas de mensajes
- `pal_whatsapp_envios`: Registro de envíos

#### `notification_db_backend.py`
- Backend de base de datos para notificaciones
- Almacenamiento persistente de notificaciones

### 3. Services (`pal/services/`)

#### `abastecimiento.py` - Servicio de Abastecimiento
**Clase**: `AbastecimientoService`

**Funcionalidades**:
- **Lista Roja**: Productos que no deben trasladarse a ciertas sedes
  - `get_red_list()`: Obtener productos en lista roja
  - `add_to_red_list()`: Agregar producto a lista roja
  - `remove_from_red_list()`: Remover de lista roja

- **Sugerencias de Transferencia**:
  - Análisis de stock vs ventas por sede
  - Algoritmo de cálculo de promedio diario con cascada
  - Distribución proporcional basada en peso de ventas
  - Consideración de compromisos pendientes

- **Algoritmo de Cálculo**:
  1. Ventanas de tiempo crecientes (cascada): días/3, días/2, días
  2. Resurrección: Si no hay ventas en ventanas, buscar en 365 días
  3. Productos rojos sin stock: Asignar promedio mínimo (0.05)
  4. Productos muertos: Excluir del análisis

**Estructura de Sugerencia**:
```python
{
    "producto_codigo": str,
    "producto_descripcion": str,        # corta
    "producto_descripcion_larga": str, # larga
    "sucursal_destino": str,
    "sucursal_origen_sugerida": str,
    "cantidad_sugerida": int,
    "stock_actual": float,
    "promedio_diario": float,
    "dias_para_quiebre": float,
    "motivo": str,
    "es_rojo": bool
}
```

#### `tra.py` - Transferencias (Rotación de Inventario)
**Funciones principales**:
- Análisis de rotación de inventario (TRA)
- Cálculo de días de inventario disponible
- Identificación de productos con exceso o quiebre
- Integración con sistema de filtros jerárquicos

#### `mbrp.py` - Máximo y Mínimo por Punto de Reorden
- Cálculo de niveles de reorder point (ROP)
- Determinación de stock máximo y mínimo por producto/sede
- Análisis de cobertura de inventario

#### `stock.py` - Gestión de Stock
**Funciones**:
- `load_all_jerarquia()`: Carga jerarquía completa con caché
- `build_producto_jerarquia()`: Filtra jerarquía por códigos en alerta
- Procesamiento de alertas de stock (quiebres, excesos)
- Mapeo de alertas por ubicación y severidad

#### `exports.py` - Exportaciones
**Funciones de exportación a Excel**:
- `export_stock_excel()`: Exporta alertas de stock con formato profesional
- `export_tra_excel()`: Exporta análisis TRA
- `export_mbrp_excel()`: Exporta análisis MBRP
- `export_clientes_excel()`: Exporta datos de clientes
- `export_sugerencias_excel()`: Exporta sugerencias de abastecimiento

**Características de Exportación**:
- Formato condicional (colores según severidad)
- Múltiples hojas de análisis
- Tablas con estilos profesionales
- Fórmulas Excel
- Compatibilidad con Excel 2010+
- Limpieza automática de caracteres de control (`clean_for_excel()`)

**Funciones auxiliares**:
- `get_ofertas_por_productos_bulk()`: Detecta ofertas activas por producto en un rango de fechas

#### `notifications.py` - Notificaciones WhatsApp
**Integración WhatsApp Business API**:
- Envío de mensajes individuales y masivos
- Soporte para plantillas de mensajes
- Validación de números de teléfono
- Registro de envíos en base de datos

**Funciones**:
- `enviar_mensaje_whatsapp()`: Envío individual
- `enviar_mensaje_bulk()`: Envío masivo con control de rate limiting
- Manejo de errores de API
- Reintentos automáticos

#### `filters.py` - Filtros Unificados
Utilidades compartidas de filtrado para módulos PAL:
- Filtrado jerárquico (departamento/grupo/subgrupo)
- Normalización de valores
- Estrategias de manejo de datos faltantes

#### `cache.py` - Caché
- `CacheDescripciones`: Caché TTL para descripciones de productos
- Reduce consultas repetidas a la base de datos

#### `envios.py` - Envíos
- Gestión de logística de envíos
- Integración con servicios de mensajería

### 4. UI (`pal/ui/`)

#### `login.py` - Pantalla de Login
- Formulario de inicio de sesión
- Validación de credenciales
- Manejo de errores de autenticación

#### `splash.py` - Pantalla de Inicio
- Splash screen con carga de recursos
- Indicadores de progreso de inicialización
- Verificación de conexión a BD

#### `header.py` - Encabezado Principal
- Barra de navegación superior
- Información de usuario y sesión
- Botones de acceso rápido

#### `themes.py` - Temas
- Configuración de temas visuales (claro/oscuro)
- Paletas de colores corporativas
- Fuentes y estilos consistentes

#### `debug_console.py` - Consola de Debug
- Visualización de logs en tiempo real
- Filtros por nivel de severidad
- Utilidad para soporte técnico

#### `admin_menu.py` - Menú de Administración
- Gestión de usuarios
- Configuración de permisos
- Panel de control administrativo

#### `clientes_menu.py` - Menú de Clientes
- Búsqueda y gestión de clientes
- Visualización de información de contacto

#### `tabs/` - Pestañas Funcionales
Contiene los diferentes módulos de la aplicación organizados en pestañas:
- Tab de Stock/Alertas
- Tab de TRA (Transferencias)
- Tab de MBRP (Máximos/Mínimos)
- Tab de Abastecimiento
- Tab de Clientes
- Tab de Exportaciones
- Tab de Notificaciones WhatsApp

#### `popups/` - Ventanas Emergentes
- Diálogos de confirmación
- Formularios de edición
- Notificaciones toast
- Modales de configuración

---

## Patrones de Diseño Replicados

### 1. Gestión de Conexión a Base de Datos
```python
# Verificar conexión antes de operar
if not self.db_manager or not self.db_manager.ensure_connection():
    self.log("No hay conexión válida", "WARNING")
    return
```

### 2. Normalización de Códigos
```python
def _normalize_code(value):
    """Normaliza códigos de producto para comparación consistente."""
    try:
        s = str(value).strip().lstrip('0')
        return s if s else "0"
    except Exception:
        return ""
```

### 3. Manejo de Resultados de BD Nulos
```python
result = self.db_manager.fetch_data(query, params)
if not result:
    return []  # o valor por defecto seguro
```

### 4. Logging con Contexto
```python
from pal.core.log import get_logger

logger = get_logger(__name__)
logger.info("Mensaje informativo")
logger.error(f"Error en operación: {e}")
logger.success("Operación completada")
```

### 5. Placeholders SQL Dinámicos
```python
# Para IN clauses con listas variables
placeholders = ','.join(['?'] * len(lista_codigos))
query = f"SELECT * FROM tabla WHERE codigo IN ({placeholders})"
result = db_manager.fetch_data(query, tuple(lista_codigos))
```

### 6. Batch Processing (Chunks)
```python
chunk_size = 500
for i in range(0, len(codigos), chunk_size):
    chunk = codigos[i:i+chunk_size]
    # Procesar chunk...
```

### 7. Manejo de Fechas SQL Server
```python
# Formato ISO para evitar errores de conversión
fecha_str = fecha.strftime('%Y-%m-%d 23:59:59.997')
```

### 8. Fallback en Descripciones
```python
descripcion_corta = str(r_desc_corta or r_desc_larga or "SIN DESCRIPCIÓN")
descripcion_larga = str(r_desc_larga or "SIN DESCRIPCIÓN")
```

### 9. Estrategia de Caché con TTL
```python
# Verificar caché existente
if os.path.exists(cache_file):
    mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
    if datetime.now() - mtime < ttl:
        with open(cache_file, 'r') as f:
            return json.load(f)
# Si no hay caché válido, cargar de BD y guardar caché
```

### 10. Patrón de Callbacks para Progreso
```python
def export_data(datos, progress_cb=None):
    total = len(datos)
    for i, item in enumerate(datos):
        # Procesar item...
        if progress_cb:
            progress_cb(i + 1, total)  # (actual, total)
```

---

## Módulos de Negocio Clave
*   **Abastecimiento (`abastecimiento.py`):** Sugerencias de transferencia entre sedes basadas en rotación y stock mínimo.
*   **Rotación de Inventario (TRA/MBRP):** Análisis profundo de ventas y rotación de productos para optimizar el inventario.
*   **Mensajería WhatsApp:** Integración para envío de notificaciones y mensajes programados a clientes.
*   **Exportaciones (`exports.py`):** Generación de reportes complejos en formato Excel con alto rendimiento.

---

## Flujo de Datos Típico

1. **Inicialización**: `app.py` → carga configuración → conecta BD → carga jerarquías → inicia GUI
2. **Consulta de Stock**: Usuario aplica filtros → sistema consulta `MA_DEPOPROD` → aplica jerarquía → muestra resultados
3. **Análisis de Abastecimiento**: Calcula promedios de ventas → detecta quiebres → genera sugerencias → guarda en `pal_sugerencias_transferencia`
4. **Exportación**: Recupera sugerencias → enriquece con descripciones → genera Excel con formato
5. **Notificación**: Selecciona clientes → carga plantilla → envía vía API WhatsApp → registra en `pal_whatsapp_envios`
