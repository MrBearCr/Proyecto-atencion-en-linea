# ARCHIVO ARCHIVADO
Este documento ha sido unificado en `docs/README.md`.

Contenido original:

# Arquitectura del Sistema

## Introducción
Aplicación de escritorio en Python (Tkinter) para gestión de clientes, monitoreo de inventario y mensajería por WhatsApp, con SQL Server como backend de datos.

## Visión General
- app.py inicializa splash, sesión, UI y servicios.
- Módulos organizados en `pal/core`, `pal/services`, `pal/infrastructure`, `pal/ui`.
- Acceso a datos mediante `pyodbc`; seguridad con `keyring` + `cryptography.fernet`.

## Principios de Diseño
1. Separación por capas y módulos.
2. Resiliencia: reintentos y validaciones de conexión.
3. Seguridad por defecto: secretos fuera de archivos planos.
4. Reutilización: filtros jerárquicos unificados y caché.

## Flujo de Datos
1. UI (Tkinter) dispara acciones en `DatabaseApp`.
2. `DatabaseApp` delega en servicios (`pal/services/*`).
3. `DatabaseManager` ejecuta consultas parametrizadas en SQL Server.
4. `SecureCredentialsManager` provee credenciales/token cuando se requieren.
5. `AuditLogger` registra eventos y errores.

## Patrones y Utilidades
- Service layer, Strategy (filtros), Caching, Logging centralizado, Threading para tareas en segundo plano.

## Documentación Relacionada
- Ver `docs/README.md`.