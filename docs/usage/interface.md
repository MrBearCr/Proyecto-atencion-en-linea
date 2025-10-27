# Diseño de la Interfaz

## Componentes Principales
- Barra superior y estilos: `pal/ui/header.py`.
- Barra lateral: `pal/ui/sidebar.py`.
- Pestañas: `pal/ui/tabs/*.py` (records, messaging, stats, calendar, stock, tra, mbrp).

```python
# Inicialización (simplificada)
ui_setup_styles(app)   # estilos ttk
app.setup_modern_ui()  # crea header, sidebar, tabs y barra de estado
```

- Las pestañas de Stock/TRA usan filtros jerárquicos y paginación.
- La UI deshabilita acciones dependientes de BD hasta conectar.
