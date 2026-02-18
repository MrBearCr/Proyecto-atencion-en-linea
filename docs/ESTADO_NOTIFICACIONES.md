# Estado del Sistema de Notificaciones PAL

> Última actualización: 2026-02-17

---

## Resumen ejecutivo

El sistema de notificaciones PAL ha evolucionado de un conjunto de popups temporales
a una arquitectura de **notificaciones persistentes** con panel visual, botón "Tratar"
y navegación directa al módulo que requiere atención.

---

## Arquitectura actual (v2 — Persistente)

```
┌─────────────────────────────────────────────────────────────────┐
│  app.py                                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  self.notification_manager  (NotificationManager)        │   │
│  │  pal/services/notifications.py                           │   │
│  │  • Gestiona lista en memoria                             │   │
│  │  • Patrón Observer (add_observer / notify_observers)     │   │
│  │  • Métodos: add(), mark_as_read(), mark_as_treated(),    │   │
│  │             dismiss_notification(), mark_all_as_read()   │   │
│  │  • Carga/guarda via NotificationDBBackend (opcional)     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PyodbcNotificationBackend                               │   │
│  │  pal/infrastructure/notification_db_backend.py           │   │
│  │  • save(notification)                                    │   │
│  │  • update_status(notification)                           │   │
│  │  • load_active(usuario)                                  │   │
│  │  • purge_expired()                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SQL Server — tabla pal_notificaciones                   │   │
│  │  Migración: docs/migrations/010_crear_tabla_notif...sql  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  pal/ui/header.py — NotificationBell                            │
│  • Widget 🔔 con badge numérico rojo                            │
│  • Panel desplegable (Toplevel) con scroll                      │
│  • Tarjetas por notificación:                                   │
│    - Franja de color por prioridad (urgent/warning/info/success)│
│    - Icono + título + módulo + timestamp relativo               │
│    - Mensaje truncado                                           │
│    - Botón "→ Tratar" → mark_as_treated() + navigate_to_module()│
│    - Botón "× Descartar" → dismiss_notification()              │
│  • Botón "✓ Todo leído" → mark_all_as_read()                   │
│  • Observador del NotificationManager (auto-refresco)          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  app.py — navigate_to_module(modulo_ruta)                       │
│  Mapeo de rutas a pestañas del main_notebook:                   │
│  'stock'        → stock_tab                                     │
│  'tra'          → tra_tab                                       │
│  'mbrp'         → mbrp_tab                                      │
│  'clientes'     → clientes_tab                                  │
│  'admin'        → admin_tab                                     │
│  'mensajes'     → messaging_tab                                 │
│  'estadisticas' → stats_tab                                     │
│  'calendario'   → calendar_tab                                  │
│  'registros'    → records_tab                                   │
│  'inicio'       → dashboard_tab                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Archivos involucrados

| Archivo | Rol |
|---|---|
| `pal/services/notifications.py` | Modelo `Notification`, `NotificationManager`, `NotificationDBBackend` (ABC) |
| `pal/infrastructure/notification_db_backend.py` | Implementación pyodbc para SQL Server |
| `pal/ui/header.py` | `NotificationBell` widget + `create_header()` + `setup_styles()` |
| `app.py` | Importa backend, instancia manager, expone `navigate_to_module()` |
| `docs/migrations/010_crear_tabla_notificaciones.sql` | DDL de la tabla `pal_notificaciones` |

---

## Migración de base de datos

**Archivo:** `docs/migrations/010_crear_tabla_notificaciones.sql`

Ejecutar una sola vez en la base de datos de producción:

```sql
-- Ejecutar como DBA o usuario con permisos DDL
-- Idempotente: usa IF NOT EXISTS
:r docs/migrations/010_crear_tabla_notificaciones.sql
```

Columnas principales de `pal_notificaciones`:

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NVARCHAR(36) PK | UUID de la notificación |
| `titulo` | NVARCHAR(200) | Título corto |
| `mensaje` | NVARCHAR(MAX) | Cuerpo del mensaje |
| `prioridad` | NVARCHAR(20) | `urgent`, `warning`, `info`, `success` |
| `modulo` | NVARCHAR(100) | Nombre del módulo origen |
| `modulo_ruta` | NVARCHAR(100) | Ruta para `navigate_to_module()` |
| `accion_etiqueta` | NVARCHAR(100) | Texto del botón "Tratar" |
| `datos_json` | NVARCHAR(MAX) | Datos extra en JSON |
| `leida` | BIT | 0 = no leída |
| `descartada` | BIT | 0 = activa |
| `tratada` | BIT | 0 = pendiente de tratar |
| `c_usuario` | NVARCHAR(100) | Usuario destino (NULL = global) |
| `c_usuario_trato` | NVARCHAR(100) | Usuario que la trató |
| `f_creacion` | DATETIME | Fecha de creación |
| `f_leida` | DATETIME | Fecha de lectura |
| `f_tratada` | DATETIME | Fecha de tratamiento |
| `f_expiracion` | DATETIME | Expiración (NULL = sin expiración) |

---

## Cómo crear una notificación desde código

```python
# Ejemplo: notificación de quiebre de stock
self.notification_manager.add(
    title="Quiebre de Stock",
    message="El producto 016208 tiene 0 unidades en Cabudare.",
    priority="urgent",          # urgent | warning | info | success
    module="Stock",             # Nombre visible del módulo
    modulo_ruta="stock",        # Ruta para navigate_to_module()
    accion_etiqueta="Ver Stock",# Texto del botón "Tratar"
    usuario="admin",            # None = global
    datos={"codigo": "016208"}, # Datos extra opcionales
)
```

---

## Flujo del botón "Tratar"

```
Usuario hace clic en "→ Tratar"
        │
        ▼
NotificationBell._on_tratar(notif)
        │
        ├─► NotificationManager.mark_as_treated(id, usuario)
        │       │
        │       └─► PyodbcNotificationBackend.update_status()
        │               └─► UPDATE pal_notificaciones SET tratada=1 ...
        │
        ├─► NotificationBell._close_panel()
        │
        └─► app.navigate_to_module(notif.modulo_ruta)
                └─► main_notebook.select(tab_correspondiente)
```

---

## Estado de implementación

| Componente | Estado |
|---|---|
| `Notification` dataclass | ✅ Implementado |
| `NotificationManager` (in-memory + observer) | ✅ Implementado |
| `NotificationDBBackend` (ABC) | ✅ Implementado |
| `PyodbcNotificationBackend` | ✅ Implementado |
| Migración SQL `010_crear_tabla_notificaciones.sql` | ✅ Creada |
| `NotificationBell` widget con panel | ✅ Implementado |
| Botón "Tratar" con navegación | ✅ Implementado |
| `navigate_to_module()` en app.py | ✅ Implementado |
| Integración post-login (cargar desde BD) | ✅ Implementado |

---

## Integración post-login (paso pendiente)

Para activar la persistencia completa, agregar en `_post_login_setup()` dentro de `app.py`:

```python
# Después de que db_manager esté conectado y current_user esté disponible:
from pal.infrastructure.notification_db_backend import PyodbcNotificationBackend
from pal.services.notifications import NotificationManager as CentralNotificationManager

# Reemplazar el manager temporal por uno con backend persistente
backend = PyodbcNotificationBackend(self.db_manager)
self.notification_manager = CentralNotificationManager(db_backend=backend)

# Cargar notificaciones activas del usuario
usuario = self.current_user.get('username') if self.current_user else None
self.notification_manager.load_from_db(usuario=usuario)

# Actualizar la campana si ya existe
if hasattr(self, 'notification_bell') and self.notification_bell:
    self.notification_bell._mgr = self.notification_manager
    self.notification_bell.set_usuario(usuario)
    self.notification_bell._mgr.add_observer(self.notification_bell._on_notifications_changed)
    self.notification_bell._refresh_badge()
```

---

## Notas de diseño

- **Backward compatible**: La clase interna `NotificationManager` de `app.py` se mantiene
  para no romper llamadas existentes (`show_error`, `show_banner`, etc.).
- **Observer pattern**: Cualquier cambio en el manager notifica automáticamente a la campana.
- **Thread-safe UI**: Los callbacks del observer usan `frame.after(0, ...)` para ejecutar
  en el hilo principal de Tkinter.
- **Sin bloqueo**: El panel se cierra con `FocusOut` con un delay de 150ms para evitar
  cierres accidentales al hacer clic en botones internos.
- **Prioridades visuales**: Cada prioridad tiene color de fondo, franja lateral y badge
  diferenciados (rojo urgente, naranja warning, azul info, verde success).
