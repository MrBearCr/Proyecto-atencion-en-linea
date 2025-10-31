# Plan de Mejoras Estructurales - Proyecto Atención en Línea

## 📋 Estado Actual

- **app.py**: 1890+ líneas (monolítico)
- **Clase**: `DatabaseApp` con múltiples responsabilidades
- **Arquitectura**: Todo mezclado (UI, BD, lógica, exportación)
- **Módulos internos**: `pal/` sin claridad en separación

---

## 🎯 Mejoras Propuestas

### **Fase 1: Separación de Responsabilidades**

#### 1.1 Crear estructura de directorios
```
proyecto-atencion-en-linea/
├── app.py                          # Punto de entrada (solo main())
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Configuración global
│   ├── constants.py                # Constantes (LOCATION_GROUPS, DB_MODULE_TO_FLAG, etc.)
│   └── db_config.ini               # Config BD (mover aquí)
├── core/
│   ├── __init__.py
│   ├── app_manager.py              # Orquestador principal
│   └── constants.py                # Constantes compartidas
├── ui/
│   ├── __init__.py
│   ├── main_window.py              # Ventana principal
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── settings_dialog.py      # Diálogo de configuración
│   │   └── export_dialog.py        # Diálogo de exportación
│   └── widgets/
│       ├── __init__.py
│       ├── stock_widget.py         # Widget de stock
│       ├── tra_widget.py           # Widget de TRA
│       └── mbrp_widget.py          # Widget de MBRP
├── services/
│   ├── __init__.py
│   ├── stock_service.py            # Lógica de stock (métodos actuales)
│   ├── tra_service.py              # Lógica de TRA (métodos actuales)
│   ├── mbrp_service.py             # Lógica de MBRP (métodos actuales)
│   └── notification_service.py     # Notificaciones
├── data/
│   ├── __init__.py
│   ├── models.py                   # Dataclasses/TypedDicts
│   └── cache.py                    # Caché unificado
└── utils/
    ├── __init__.py
    ├── logging.py                  # Sistema de logging
    └── helpers.py                  # Funciones auxiliares
```

---

### **Fase 2: Extracción de Servicios desde `app.py`**

#### 2.1 `services/stock_service.py`
**Mover desde app.py:**
- `actualizar_alertas_stock()`
- `recargar_stock()`
- `_recargar_stock_async()`
- `_background_load_alertas_stock()`
- `_update_stock_reload_progress()`
- `_hide_stock_reload_progress()`
- `load_stock_filters()`
- `aplicar_filtro_stock()`
- `_obtener_datos_filtrados()`
- Métodos helper: `_coincide_jerarquia()`, `_get_total_stock_count()`, etc.

**Responsabilidad:**
- Gestionar alertas de stock
- Cachés de stock
- Carga paralela
- Filtros jerárquicos

#### 2.2 `services/tra_service.py`
**Mover desde app.py:**
- `_background_load_ventas_tra()`
- `_background_load_ventas_tra_fast()`
- `_fetch_tra_chunk_optimized()`
- `_check_tra_cache()`, `_save_tra_cache()`
- `_update_tra_ui_after_chunk()`, `_update_tra_phase()`, etc.
- `aplicar_filtro_tra()`
- `exportar_tra_excel()`

**Responsabilidad:**
- Gestionar ventas TRA
- Carga adaptativa con chunks
- Cachés con TTL
- Clasificación de rotación

#### 2.3 `services/mbrp_service.py`
**Mover desde app.py:**
- Métodos equivalentes a TRA para MBRP
- `_background_load_ventas_mbrp()`
- `aplicar_filtro_mbrp()`
- `exportar_mbrp_excel()`

#### 2.4 `services/notification_service.py`
**Mover desde app.py:**
- `monitorear_favoritos()`
- `_detectar_y_notificar_criticos()`
- `_mostrar_alerta_compras()`
- `mostrar_notificacion()`
- `obtener_descripcion_producto()`
- `validar_stock_producto()`

---

### **Fase 3: Reorganizar UI**

#### 3.1 `ui/main_window.py`
**Mover desde app.py:**
- `setup_modern_ui()` → `build_ui()`
- `setup_bindings()`
- `setup_tooltips()`
- Métodos de compilación de widgets

#### 3.2 `ui/widgets/stock_widget.py`
**Nuevo archivo:**
```python
class StockWidget(ttk.Frame):
    def __init__(self, parent, app_manager):
        self.app_manager = app_manager
        # Construir UI de stock
    
    def populate_data(self, datos):
        # Llenar tabla con datos
    
    def get_filters(self):
        # Retornar filtros actuales
```

#### 3.3 `ui/dialogs/export_dialog.py`
**Mover desde app.py:**
- `_update_export_progress()`
- `_export_success()`
- `_export_error()`
- `_cleanup_export_progress()`

---

### **Fase 4: Centralizar Configuración**

#### 4.1 `config/settings.py`
```python
# Mapeos de módulos
DB_MODULE_TO_FLAG = {...}

# Grupos de ubicación
LOCATION_GROUPS = {...}

# Configuración de paginas/chunks
PAGE_SIZE_STOCK = 250
PAGE_SIZE_TRA = 500
CHUNK_SIZE_TRA = 500

# Cache TTL
STOCK_CACHE_TTL = timedelta(hours=15)
TRA_CACHE_TTL = timedelta(hours=2)

# Debugging
DEBUG_FLAGS = {
    'tra': False,
    'stock': False,
    'mbrp': False,
    'db': False,
}
```

#### 4.2 `config/constants.py`
```python
CONFIG_FILE = 'db_config.ini'
JERARQUIA_CACHE_FILE = "productos_jerarquia_cache.json"
FAVORITOS_CACHE_FILE = 'favoritos_cache.json'
```

---

### **Fase 5: Modelos de Datos**

#### 5.1 `data/models.py`
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class StockAlerta:
    codigo: str
    descripcion: str
    stock: int
    nivel: str  # 'Crítica', 'Media', 'Leve'

@dataclass
class VentaTRA:
    codigo: str
    rotacion: str  # 'ALTA', 'MEDIA', 'BAJA'
    neto: float
    # ... más campos

@dataclass
class Usuario:
    id: str
    username: str
    permissions: dict
```

---

### **Fase 6: Sistema de Logging Centralizado**

#### 6.1 `utils/logging.py`
```python
class AppLogger:
    def __init__(self):
        self.setup_logging()
    
    def log(self, message, level="INFO"):
        # Logging centralizado
    
    def debug_log(self, module, message):
        # Debug por módulo
```

---

## 📊 Beneficios Esperados

| Aspecto | Actual | Mejorado |
|---------|--------|----------|
| **Líneas por archivo** | 1890+ en app.py | 200-300 por módulo |
| **Testabilidad** | Nula | Alta (servicios aislados) |
| **Mantenibilidad** | Difícil | Fácil (responsabilidades claras) |
| **Reutilización** | Baja | Alta (módulos independientes) |
| **Debugging** | Complejo | Simple (logging modular) |
| **Escalabilidad** | Limitada | Ampliable (arquitectura modular) |

---

## 🔄 Orden de Implementación

1. **Fase 1**: Crear estructura de directorios
2. **Fase 2**: Crear servicios vacíos y migrar lógica
3. **Fase 3**: Extraer UI a módulos
4. **Fase 4**: Centralizar configuración
5. **Fase 5**: Definir modelos de datos
6. **Fase 6**: Crear logger centralizado
7. **Refactoring**: `app_manager.py` orquesta todo
8. **Testing**: Crear tests unitarios por módulo

---

## 🚀 Punto de Entrada Mejorado

### Antes (app.py actual)
```python
class DatabaseApp:
    def __init__(self, root):
        # 50+ líneas de inicialización
        # Múltiples responsabilidades
```

### Después (app.py refactorizado)
```python
# app.py
from core.app_manager import AppManager
from ui.main_window import MainWindow

def main():
    root = tk.Tk()
    app_manager = AppManager()
    window = MainWindow(root, app_manager)
    root.mainloop()

if __name__ == '__main__':
    main()
```

### core/app_manager.py
```python
class AppManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.stock_service = StockService(self.db)
        self.tra_service = TraService(self.db)
        self.mbrp_service = MbrpService(self.db)
        self.notification_service = NotificationService(self.db)
    
    def initialize(self):
        """Inicializar todos los servicios"""
        self.db.connect()
        self.load_config()
        self.start_background_tasks()
```

---

## 📝 Checklist de Implementación

- [ ] Crear estructura de directorios
- [ ] Mover `services/stock_service.py`
- [ ] Mover `services/tra_service.py`
- [ ] Mover `services/mbrp_service.py`
- [ ] Mover `services/notification_service.py`
- [ ] Crear `config/settings.py`
- [ ] Crear `data/models.py`
- [ ] Crear `ui/main_window.py`
- [ ] Crear `core/app_manager.py`
- [ ] Refactorizar `app.py` a punto de entrada
- [ ] Crear tests unitarios
- [ ] Documentar APIs

---

## 🎓 Notas Adicionales

### Próximos Pasos
- Agregar type hints completos
- Documentar con docstrings
- Crear tests unitarios
- Implementar dependency injection
- Considerar async/await para operaciones BD

### Consideraciones
- Mantener backward compatibility durante migración
- Usar feature flags para rollback si es necesario
- Validar que caché/persistencia funcione igual
- Verificar logging en todos los módulos

