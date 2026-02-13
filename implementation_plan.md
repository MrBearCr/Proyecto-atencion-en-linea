# Implementation Plan - Stock Module Migration ("Quiebre de Stock")

# Goal Description
Transform the legacy `stock` module into a "Quiebre de Stock" (Stock Break) module with dynamic configuration. The core logic shifts from simple low stock to "High Rotation (TRA) + Zero Stock" (Lost Sales). Crucially, the system must separate **Sales Scope** (Global/ICH) from **Stock Scope** (Treatable Warehouses per Branch).

## User Review Required
> [!IMPORTANT]
> **Configuration Overhaul**: We will implement a new "Sedes Configuration" UI in Global Settings. This replaces the hardcoded `LOCATION_GROUPS`.
> **Stock vs Sales**:
> - **Sales**: Global context (all warehouses) to determine Rotation/Importance.
> - **Stock**: Local context (configured "Treatable" warehouses) to determine Breaks.
> **Database**: Validating usage of `pal_global_settings` to store the new `sedes_config`.

## Proposed Changes

### Configuration Layer (`pal/core/` & `pal/ui/`)

#### [NEW] [config_manager.py](file:///c:/Users/rafae/OneDrive/Desktop/Proyecto-atencion-en-linea-1/pal/core/config_manager.py)
- **Class**: `ConfigManager`
- **Purpose**: Centralize reading/writing to `pal_global_settings`.
- **Methods**:
    - `get_sedes_config()`: Returns dict of `{ "SedeName": ["dep1", "dep2"] }`.
    - `save_sedes_config(config_dict)`: Saves JSON to DB.
    - `get_sales_warehouses()`: Returns global list of sales warehouses (ICH).

# Plan de Migración y Transformación: Módulo "Quiebre de Stock"

## Objetivo
Transformar el antiguo módulo de Stock en un sistema de **Quiebre de Stock** proactivo, eficiente y bien integrado en la administración.

## Cambios Propuestos

### 1. Renombrado y Estética (UI)
- **Módulo**: Cambiar "Stock" / "Alertas Stock" por "⚠️ Quiebre de Stock" en toda la UI (Sidebar, Pestañas, Logs).
- **Archivos**: `app.py`, `pal/ui/sidebar.py`, `pal/ui/tabs/stock.py`.

### 2. Lógica Optimizada de Quiebres (Backend)
- **Direct SQL**: Implementar `obtener_quiebres_directos` en `DatabaseManager` que identifique productos con stock 0 y ventas registradas después de su Última Compra (`Update_date`).
- **Desacoplamiento**: Eliminar la dependencia del módulo TRA (RI) para la detección de quiebres, utilizando consultas SQL más simples y rápidas.

### 3. Consolidación de "Configuraciones Globales"
- **Nuevo Dashboard de Configuración**: Crear `pal/ui/admin_menu.py` siguiendo el patrón de tarjetas de "Clientes".
- **Sub-módulos**:
    - **Sedes (Servidores)**: Restaurar la gestión de `pal_sedes_configuracion` (IP, BD, etc.).
    - **Depósitos (Stock)**: Configuración de almacenes tratables para Quiebre de Stock.
    - **Exclusiones**: Gestión de departamentos excluidos de reportes.
    - **Usuarios & Permisos**: Centralizar la gestión de acceso.
- **Navegación**: Implementar `show_admin_sub_view` en `app.py` para alternar entre estas configuraciones.

### [Backend] [pal/infrastructure/database.py](file:///c:/Users/rafae/OneDrive/Desktop/Proyecto-atencion-en-linea-1/pal/infrastructure/database.py)
#### [NEW]
- Implementar `obtener_quiebres_directos(depositos)` para la detección optimizada de ventas perdidas.

### [UI] [NEW] [pal/ui/admin_menu.py](file:///c:/Users/rafae/OneDrive/Desktop/Proyecto-atencion-en-linea-1/pal/ui/admin_menu.py)
- Implementar el menú de tarjetas para la sección de Administración.

### [UI] [NEW] [pal/ui/tabs/sedes_servidores.py](file:///c:/Users/rafae/OneDrive/Desktop/Proyecto-atencion-en-linea-1/pal/ui/tabs/sedes_servidores.py)
- Re-implementar la UI para la tabla `pal_sedes_configuracion`.

## Verification Plan

### Manual Verification
1. **Configuration**:
    - Go to Settings.
    - Create Sede "TestBranch".
    - Assign Deposit X.
    - Save and reload app -> Verify config persists.
2. **Break Logic**:
    - Pick a High Rotation product.
    - Ensure it has 0 stock in Deposit X but >0 elsewhere.
    - Verify popup alerts "Break in TestBranch".
    - Verify NO alert for other branches where stock > 0.
