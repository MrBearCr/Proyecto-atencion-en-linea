# Arquitectura

## En una frase
Aplicación de escritorio en Python para la Gestión de Clientes y Logística (PAL) que administra inventario, abastecimiento y comunicación vía WhatsApp.

## Stack
- Lenguaje / runtime: Python 3.x
- Framework principal: Tkinter (interfaz gráfica)
- Base de datos: SQL Server (vía pyodbc)
- Servicios externos: WhatsApp Business API

## Mapa de carpetas
- `pal/core/` → Lógica de negocio (auth, auditoría, credenciales seguras, licencias, updater).
- `pal/infrastructure/` → Capa de acceso a datos (`database.py`), migraciones de esquema automático.
- `pal/services/` → Servicios especializados (Abastecimiento, TRA, MBRP, Stock, WhatsApp, Exportación Excel).
- `pal/ui/` → Componentes de la interfaz de usuario (tabs, popups, temas y pantallas de inicio/login).
- `app.py` → Punto de entrada principal y orquestador de la aplicación.
- `tests/` → Pruebas de la aplicación.

## Flujo de datos
El usuario interactúa con la GUI (`pal/ui/`), que invoca a los servicios (`pal/services/`) para aplicar reglas de negocio. Estos consultan la BD vía `pal/infrastructure/database.py`, procesan datos (ej. aplicando filtros jerárquicos) y retornan el resultado a la UI o exportan a Excel/WhatsApp.

## Lo que NO existe (y no hay que crear)
- No usamos ORM (se usa SQL crudo con placeholders dinámicos vía `pyodbc`).
- No hay API REST interna (la aplicación de escritorio se conecta directamente a la base de datos).
