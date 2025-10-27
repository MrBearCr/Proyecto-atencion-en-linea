# ARCHIVO ARCHIVADO
Este documento ha sido unificado en `docs/README.md`.

Contenido original (última versión previa a la unificación):

# Componentes del Sistema (actual)

## Capa de Presentación (Tkinter)
- Aplicación de escritorio con pestañas: Registros, Mensajería, Estadísticas, Calendario, Stock, TRA, MBRP.
- Módulos UI: `pal/ui/header.py`, `pal/ui/sidebar.py`, `pal/ui/tabs/*.py`, `pal/ui/splash.py`.
- Estilos y widgets modernos con ttk; actualización de UI segura desde hilos.

## Capa de Negocio
- Clase orquestadora: `DatabaseApp` en `app.py` (inicialización, UI, tareas en segundo plano).
- Servicios:
  - `pal/services/stock.py`: filtrado/paginación de alertas, existencias por depósito.
  - `pal/services/tra.py`: filtrado/paginación TRA y cálculos de representación.
  - `pal/services/mbrp.py`: métricas de baja rotación y últimas ventas.
  - `pal/services/filters.py`: filtros jerárquicos unificados.
  - `pal/services/envios.py`: programador y envíos programados.
  - `pal/services/cache.py`: caché de descripciones.

## Capa de Infraestructura y Datos
- `pal/infrastructure/database.py`: `DatabaseManager` con pyodbc, commits/rollback y validación de conexión.
- Tablas propias: `clientes`, `favoritos_productos`, `envios_programados`, `TEMP_ENVIO`.
- Tablas externas (solo lectura): `MA_PRODUCTOS`, `MA_DEPOPROD`, `TR_INVENTARIO`.

## Capa de Seguridad y Utilidades
- `pal/core/credentials.py`: `SecureCredentialsManager` con keyring + Fernet.
- `pal/core/errors.py`: `ErrorCode` centralizado.
- `pal/core/audit.py`: `AuditLogger` con RotatingFileHandler.
- `pal/core/session.py`: `SessionManager` (timeout 15 min, limpieza de secretos).

## Integraciones Externas
- WhatsApp Business (Graph API) vía `requests` y token almacenado en keyring.

Para detalles de configuración y seguridad, ver `docs/README.md`.