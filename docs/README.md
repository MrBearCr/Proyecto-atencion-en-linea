# Proyecto Atención en Línea — Documentación Unificada

## Resumen
Aplicación de escritorio en Python (Tkinter) para gestionar clientes, monitorear inventario (Stock/TRA/MBRP) y enviar notificaciones por WhatsApp (Graph API), con SQL Server como backend. La app centraliza UI, lógica de negocio y acceso a datos en módulos `pal/*` y un archivo de orquestación `app.py`.

## Requisitos
- Windows 10/11, Python 3.8+.
- Microsoft ODBC Driver for SQL Server, acceso a SQL Server 2016+.
- pip: `pyodbc tkinter cryptography keyring matplotlib tkcalendar requests win10toast pillow`.
- Hardware: 4GB RAM (8GB recomendado), 1GB libre, 1366x768+.

## Instalación rápida
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt  # si existe
# o manual
pip install pyodbc tkinter cryptography keyring matplotlib tkcalendar requests win10toast pillow
python app.py
```
En primer arranque, configure Conexión (servidor/BD/usuario) y, si aplica, el token de WhatsApp en Settings.

## Configuración
- Base de datos: pyodbc con consultas parametrizadas y commit/rollback.
- Credenciales y token: almacenados en Windows Credential Manager (keyring) y cifrados con Fernet.
- Tablas internas creadas por la app: `pal_clientes`, `pal_envios_programados`, `pal_temp_envio`.
- Tablas externas esperadas: `MA_PRODUCTOS`, `MA_DEPOPROD`, `TR_INVENTARIO` (solo lectura).

Esquema interno (resumen):
```sql
CREATE TABLE clientes (...);
CREATE INDEX idx_clientes_numero ON clientes (numero_cliente);
CREATE INDEX idx_clientes_codigo ON clientes (C_CODIGO);
CREATE TABLE favoritos_productos (...);
CREATE TABLE envios_programados (...);
CREATE INDEX idx_envios_fecha_estado ON envios_programados (fecha_programada, estado);
CREATE INDEX idx_envios_numero ON envios_programados (numero_cliente);
CREATE TABLE TEMP_ENVIO (...);
```

## Arquitectura
- Orquestación: `app.py` (splash, sesión, UI, programador de envíos).
- Core: `pal/core/session.py`, `pal/core/credentials.py`, `pal/core/errors.py`, `pal/core/audit.py`, `pal/core/log.py`.
- Servicios: `pal/services/stock.py`, `pal/services/tra.py`, `pal/services/mbrp.py`, `pal/services/filters.py`, `pal/services/envios.py`, `pal/services/cache.py`.
- Infraestructura: `pal/infrastructure/database.py` (pyodbc).
- UI: `pal/ui/header.py`, `pal/ui/sidebar.py`, `pal/ui/splash.py`, `pal/ui/tabs/*.py`.
- Integraciones: WhatsApp Graph API, Windows Keyring.

Notas:
- Filtros jerárquicos unificados en `pal/services/filters.py` con estrategias `include|exclude`.
- Envío masivo con espaciado (~7s) y plantillas WhatsApp aprobadas.
- Auditoría en `audit.log` (rotación 5MB x3). Sesión expira a los 15 min y purga secretos temporales.

## Uso de la aplicación
- Interfaz: barra superior, lateral y pestañas (Records, Messaging, Stats, Calendar, Stock, TRA, MBRP).
- Registros: CRUD de `clientes` (número 1–11 dígitos, código de producto). Validación de entrada y consultas parametrizadas.
- Stock: alertas por nivel (Crítica/Media/Leve), filtros jerárquicos, búsqueda y paginación.
- TRA: filtrado jerárquico, cálculo de representación y paginación.
- Mensajería: envío individual o masivo vía plantillas; token almacenado cifrado.

## Seguridad
- Keyring: servicio "DBClientApp"; Fernet para cifrado de credenciales y token.
- No se registran secretos en logs.
- Variables de entorno opcionales para despliegues automatizados.

## Códigos de error (ErrorCode)
Ejemplo de uso:
```python
from pal.core.errors import ErrorCode
audit.log_event("DATABASE_OPERATION", user="admin", status="FAILED", error_code=ErrorCode.DB_QUERY_EXECUTION)
```
Categorías destacadas: BD (1001–1005), Validación (2001–2003), Cifrado (3001–3003), API (4001–4002), Sesión (5001–5002), Config (6001–6002).

## Problemas comunes
- Falta ODBC Driver: instalar desde Microsoft.
- Token WhatsApp inválido: renovar en Meta y volver a guardar en Settings.
- Sin datos ERP: verificar permisos a `MA_PRODUCTOS`/`MA_DEPOPROD`/`TR_INVENTARIO`.

## Referencias rápidas
- Filtros unificados: `pal/services/filters.py` (match_hierarchy_* y filter_by_hierarchy).
- Envío WhatsApp: endpoint Graph API v21.0, autenticación Bearer, plantilla `alerta_stock` por defecto.
- Sesión: `pal/core/session.py` (binds de actividad y timeout configurable).

## Contacto
Sugerencias y issues: abrir PR/issue en el repositorio.
