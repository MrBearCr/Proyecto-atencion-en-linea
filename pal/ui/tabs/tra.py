"""
Módulo de configuración de pestaña TRA (Tiempo de Rotación y Abastecimiento)
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime

def setup_tra_tab(app):
    """Configura la pestaña TRA en la aplicación"""
    
    app.tra_tab_frame = ttk.Frame(app.tra_tab)
    app.tra_tab_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Frame principal para controles superiores
    top_controls = ttk.Frame(app.tra_tab_frame)
    top_controls.pack(fill=tk.X, pady=5)

    # Frame para fechas y sede
    fecha_frame = ttk.Frame(top_controls)
    fecha_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Rango rápido
    ttk.Label(fecha_frame, text="Rango:").pack(side=tk.LEFT)
    app.tra_rango_var = tk.StringVar(value="30 días")
    rango_combo = ttk.Combobox(fecha_frame, textvariable=app.tra_rango_var, state='readonly', width=10)
    rango_combo['values'] = ["7 días", "15 días", "30 días", "60 días", "90 días", "180 días", "365 días", "Personalizado"]
    rango_combo.pack(side=tk.LEFT, padx=5)
    
    ttk.Label(fecha_frame, text="Desde:").pack(side=tk.LEFT, padx=(10,0))
    # Configurar fecha máxima: ayer (las ventas no se cargan hasta el cierre)
    from datetime import timedelta
    ayer = datetime.now() - timedelta(days=1)
    # Ampliar rango para permitir análisis histórico hasta 2 años
    hace_2_anos = ayer - timedelta(days=730)
    
    app.fecha_inicio_entry = DateEntry(fecha_frame, width=12, date_pattern='yyyy-mm-dd',
                                      mindate=hace_2_anos, maxdate=ayer)
    app.fecha_inicio_entry.set_date(ayer - timedelta(days=30))  # Default: últimos 30 días
    app.fecha_inicio_entry.pack(side=tk.LEFT, padx=5)

    ttk.Label(fecha_frame, text="Hasta:").pack(side=tk.LEFT)
    app.fecha_fin_entry = DateEntry(fecha_frame, width=12, date_pattern='yyyy-mm-dd',
                                   mindate=hace_2_anos, maxdate=ayer)
    app.fecha_fin_entry.set_date(ayer)  # Default: hasta ayer
    app.fecha_fin_entry.pack(side=tk.LEFT, padx=5)

    ttk.Label(fecha_frame, text="Sede:").pack(side=tk.LEFT, padx=10)
    app.sede_var = tk.StringVar()
    app.sede_combo = ttk.Combobox(fecha_frame, textvariable=app.sede_var, state='readonly', width=18)
    app.sede_combo['values'] = ["00 - ICH", "0301 - Cabudare", "0401 - Guanare", "0101 - Barinas"]
    app.sede_combo.current(0)  # Por defecto 00 - ICH
    app.sede_combo.pack(side=tk.LEFT)

    # Aviso al seleccionar ICH (consulta global)
    def _on_sede_selected(event=None):
        try:
            sel = (app.sede_var.get() or '')
            if sel.startswith('00'):
                if hasattr(app, 'notification_manager'):
                    app.notification_manager.show_banner(
                        "Filtro ICH seleccionado: consulta global de todas las sedes; puede tardar más en procesar.",
                        bg="#FFB81C",
                        fg="black",
                        duration=5500,
                    )
        except Exception:
            pass
    app.sede_combo.bind('<<ComboboxSelected>>', _on_sede_selected)

    # Botones de acción
    # Exportar (respetar permisos)
    can_export = False
    try:
        if hasattr(app, 'permissions') and app.current_user:
            can_export = app.permissions.tiene_permiso(app.current_user['id'], 'TRA', 'exportar')
        if app.current_user and app.current_user.get('username','').lower() == 'admin':
            can_export = True
    except Exception:
        can_export = False
    btn_export = ttk.Button(top_controls, text="📈 Exportar Excel", 
               command=lambda: getattr(app, 'exportar_tra_excel', lambda: None)())
    btn_export.pack(side=tk.RIGHT, padx=5)
    if not can_export:
        try:
            btn_export.state(["disabled"])  # ttk style
        except Exception:
            btn_export.config(state='disabled')

    ttk.Button(top_controls, text="Cargar", command=app.cargar_tra_base).pack(side=tk.RIGHT, padx=10)
    
    # Checkbox para cambiar entre unidades y dólares en ventas (protegido por permiso)
    app.tra_mostrar_dolares_var = tk.BooleanVar(value=False)
    can_view_dollars_tra = False
    try:
        if hasattr(app, 'permissions') and app.current_user:
            can_view_dollars_tra = app.permissions.tiene_permiso(app.current_user['id'], 'TRA', 'ver_ventas_dolares')
        if app.current_user and app.current_user.get('username','').lower() == 'admin':
            can_view_dollars_tra = True
    except Exception:
        can_view_dollars_tra = False
    
    # Checkbox para Reporte Masivo (incluir ventas 0)
    app.tra_masivo_var = tk.BooleanVar(value=False)
    
    can_view_massive = False
    try:
        if hasattr(app, 'permissions') and app.current_user:
            can_view_massive = app.permissions.tiene_permiso(app.current_user['id'], 'TRA', 'masivo')
    except Exception:
        can_view_massive = False

    if can_view_massive:
        tra_masivo_check = ttk.Checkbutton(
            top_controls,
            text="Reporte Masivo",
            variable=app.tra_masivo_var
        )
        tra_masivo_check.pack(side=tk.RIGHT, padx=5)
    
    tra_dolares_check = ttk.Checkbutton(
        top_controls, 
        text="Ventas en $", 
        variable=app.tra_mostrar_dolares_var,
        command=lambda: app.actualizar_display_ventas_tra()
    )
    tra_dolares_check.pack(side=tk.RIGHT, padx=5)
    if not can_view_dollars_tra:
        try:
            tra_dolares_check.state(["disabled"])
        except Exception:
            tra_dolares_check.config(state='disabled')

    # Frame para filtros jerárquicos
    filter_frame = ttk.Frame(app.tra_tab_frame)
    filter_frame.pack(fill=tk.X, pady=5)

    # Departamentos
    ttk.Label(filter_frame, text="Depto:").pack(side=tk.LEFT, padx=5)
    app.tra_dept_var = tk.StringVar(value='Todos')
    app.tra_dept_combo = ttk.Combobox(filter_frame, textvariable=app.tra_dept_var, state='readonly', width=20)
    app.tra_dept_combo['values'] = ['Todos']
    app.tra_dept_combo.pack(side=tk.LEFT, padx=5)

    # Grupos
    ttk.Label(filter_frame, text="Grupo:").pack(side=tk.LEFT, padx=5)
    app.tra_group_var = tk.StringVar(value='Todos')
    app.tra_group_combo = ttk.Combobox(filter_frame, textvariable=app.tra_group_var, state='readonly', width=20)
    app.tra_group_combo['values'] = ['Todos']
    app.tra_group_combo.pack(side=tk.LEFT, padx=5)

    # Subgrupos
    ttk.Label(filter_frame, text="Subgrupo:").pack(side=tk.LEFT, padx=5)
    app.tra_sub_var = tk.StringVar(value='Todos')
    app.tra_sub_combo = ttk.Combobox(filter_frame, textvariable=app.tra_sub_var, state='readonly', width=20)
    app.tra_sub_combo['values'] = ['Todos']
    app.tra_sub_combo.pack(side=tk.LEFT, padx=5)

    # Filtro por Proveedores
    ttk.Label(filter_frame, text="Proveedores:").pack(side=tk.LEFT, padx=(15, 5))
    ttk.Button(
        filter_frame,
        text="🔍",
        width=3,
        command=lambda: getattr(app, 'abrir_selector_proveedor_tra', lambda: None)(),
    ).pack(side=tk.LEFT, padx=5)

    # Etiqueta para mostrar proveedor seleccionado (feedback visual)
    app.tra_proveedor_label_var = tk.StringVar(value="")
    app.tra_proveedor_label = ttk.Label(
        filter_frame,
        textvariable=app.tra_proveedor_label_var,
        foreground="#555555",
    )
    # No la mostramos hasta que haya proveedor seleccionado (para no ver un recuadro vacío)

    # Buscador de texto
    search_frame = ttk.Frame(app.tra_tab_frame)
    search_frame.pack(fill=tk.X, pady=5)

    ttk.Label(search_frame, text="Buscar:").pack(side=tk.LEFT, padx=5)
    app.tra_search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=app.tra_search_var)
    search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    # Funcionalidad del combobox de rango
    def _on_tra_rango_selected(event=None):
        rango = app.tra_rango_var.get()
        ayer = datetime.now() - timedelta(days=1)
        hace_2_anos = ayer - timedelta(days=730)
        
        if rango == "Personalizado":
            # Mostrar mensaje informativo sobre el rango permitido
            try:
                app.log(f"Rango personalizado seleccionado. Fechas permitidas: {hace_2_anos.strftime('%Y-%m-%d')} a {ayer.strftime('%Y-%m-%d')}", "INFO")
            except Exception:
                pass
            return
        
        # Extraer número de días
        dias = int(rango.split()[0])
        fecha_inicio = ayer - timedelta(days=dias-1)  # -1 porque incluimos el día actual
        
        # Asegurar que la fecha no exceda el límite mínimo
        if fecha_inicio < hace_2_anos:
            fecha_inicio = hace_2_anos
            try:
                app.log(f"Fecha inicio ajustada al límite mínimo: {hace_2_anos.strftime('%Y-%m-%d')}", "WARNING")
            except Exception:
                pass
        
        app.fecha_inicio_entry.set_date(fecha_inicio)
        app.fecha_fin_entry.set_date(ayer)
    
    # Función para verificar y recargar filtros si están vacíos
    def _verificar_y_recargar_filtros_tra(event=None):
        """Verifica si los filtros están vacíos y los recarga automáticamente"""
        if len(app.tra_dept_combo['values']) <= 1:  # Solo tiene 'Todos'
            try:
                app.log("Filtros TRA vacíos detectados, recargando...", "WARNING")
                # Intentar cargar desde cache o BD
                if hasattr(app, 'cargar_jerarquia_unificada'):
                    app.cargar_jerarquia_unificada()
                elif hasattr(app, 'cargar_jerarquia_tra'):
                    app.cargar_jerarquia_tra()
            except Exception as e:
                app.log(f"Error recargando filtros TRA: {e}", "ERROR")
    
    # Conectar eventos de búsqueda y filtros
    rango_combo.bind('<<ComboboxSelected>>', _on_tra_rango_selected)
    app.tra_search_var.trace_add('write', lambda *args: app.aplicar_filtro_tra())
    
    # Eventos con verificación automática
    app.tra_dept_combo.bind('<Button-1>', _verificar_y_recargar_filtros_tra)  # Antes de abrir
    app.tra_dept_combo.bind('<<ComboboxSelected>>', app.on_tra_dept_selected)
    app.tra_group_combo.bind('<<ComboboxSelected>>', app.on_tra_group_selected)
    app.tra_sub_combo.bind('<<ComboboxSelected>>', lambda e: app.aplicar_filtro_tra())

    # Controles de paginación
    pag_frame = ttk.Frame(app.tra_tab_frame)
    pag_frame.pack(fill=tk.X, pady=5)

    app.tra_btn_prev = ttk.Button(
        pag_frame, 
        text="◄ Anterior", 
        width=10, 
        command=lambda: app.cambiar_pagina_tra(-1),
        state='disabled'
    )
    app.tra_btn_prev.pack(side=tk.LEFT)

    app.tra_pagina_label = ttk.Label(pag_frame, text="Página 1/1", width=15)
    app.tra_pagina_label.pack(side=tk.LEFT, padx=5)

    app.tra_btn_next = ttk.Button(
        pag_frame, 
        text="Siguiente ►", 
        width=10, 
        command=lambda: app.cambiar_pagina_tra(1)
    )
    app.tra_btn_next.pack(side=tk.LEFT)

    # Frame para tabla con scrollbars
    tree_frame = ttk.Frame(app.tra_tab_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)

    columns = ("Código", "Descripción", "Rotación", "Ventas", "Representación %", "Stock Actual", "Stock Ideal", "Días Restantes", "Estado Stock")
    app.tra_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=10)
    
    # Configurar tamaño de fuente y altura de filas más grandes
    style = ttk.Style()
    style.configure('Large.Treeview', font=('', 11), rowheight=25)
    app.tra_tree.configure(style='Large.Treeview')

    # Configurar scrollbars
    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=app.tra_tree.yview)
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=app.tra_tree.xview)
    app.tra_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # Configurar columnas con anchos específicos
    column_config = {
        "Código": {"width": 80, "anchor": "center"},
        "Descripción": {"width": 250, "anchor": "w"},
        "Rotación": {"width": 80, "anchor": "center"},
        "Ventas": {"width": 100, "anchor": "center"},
        "Representación %": {"width": 100, "anchor": "center"},
        "Stock Actual": {"width": 80, "anchor": "center"},
        "Stock Ideal": {"width": 80, "anchor": "center"},
        "Días Restantes": {"width": 100, "anchor": "center"},
        "Estado Stock": {"width": 120, "anchor": "center"}
    }
    
    for col in columns:
        # Usar encabezado dinámico para la columna Ventas
        header_text = col
        if col == "Ventas" and hasattr(app, 'tra_mostrar_dolares_var') and app.tra_mostrar_dolares_var.get():
            header_text = "Ventas ($)"
        app.tra_tree.heading(col, text=header_text)
        config = column_config.get(col, {"width": 120, "anchor": "center"})
        app.tra_tree.column(col, **config)
    
    # Configurar estilos de colores para rotación con filas alternadas
    app.tra_tree.tag_configure('alta', background='#4CAF50', foreground='#FFFFFF', font=('', 11))  # Verde vibrante
    app.tra_tree.tag_configure('media', background='#FF9800', foreground='#FFFFFF', font=('', 11))  # Naranja vibrante
    app.tra_tree.tag_configure('baja', background='#F44336', foreground='#FFFFFF', font=('', 11))  # Rojo vibrante
    app.tra_tree.tag_configure('sin_movimiento', background='#9E9E9E', foreground='#FFFFFF', font=('', 11))  # Gris vibrante
    app.tra_tree.tag_configure('sin_clasificar', background='#9C27B0', foreground='#FFFFFF', font=('', 11))  # Púrpura vibrante
    
    # Estilos alternados para mejor distinción de filas
    app.tra_tree.tag_configure('alta_alt', background='#388E3C', foreground='#FFFFFF', font=('', 11))  # Verde más oscuro
    app.tra_tree.tag_configure('media_alt', background='#F57C00', foreground='#FFFFFF', font=('', 11))  # Naranja más oscuro
    app.tra_tree.tag_configure('baja_alt', background='#D32F2F', foreground='#FFFFFF', font=('', 11))  # Rojo más oscuro
    app.tra_tree.tag_configure('sin_movimiento_alt', background='#757575', foreground='#FFFFFF', font=('', 11))  # Gris más oscuro
    app.tra_tree.tag_configure('sin_clasificar_alt', background='#7B1FA2', foreground='#FFFFFF', font=('', 11))  # Púrpura más oscuro
    
    # Estilos para productos con ALERTA de stock (indicador visual adicional)
    # Estos estilos se aplican cuando hay alta/media rotación + stock bajo
    app.tra_tree.tag_configure('stock_alert', background='#FFE082', foreground='#E65100', font=('', 11, 'bold'))  # Amarillo con naranja oscuro
    
    # Configurar colores de selección en el style para que funcione correctamente
    style.map('Large.Treeview',
        background=[('selected', '#0D47A1')],  # Azul oscuro para selección
        foreground=[('selected', '#FFFFFF')]   # Texto blanco para contraste
    )
    
    # Variable para rastrear el ítem actualmente seleccionado
    app.tra_current_selected_item = None
    
    # Estilos para mensajes de estado
    app.tra_tree.tag_configure('loading', background='#2196F3', foreground='#FFFFFF', font=('', 12, 'italic'))  # Azul vibrante
    app.tra_tree.tag_configure('no_data', background='#FF9800', foreground='#FFFFFF', font=('', 12, 'italic'))  # Naranja vibrante
    app.tra_tree.tag_configure('error', background='#F44336', foreground='#FFFFFF', font=('', 12, 'italic'))  # Rojo vibrante

    # Eventos de selección mejorados
    def on_tra_click(event):
        """Maneja el click en una fila del treeview"""
        try:
            region = app.tra_tree.identify_region(event.x, event.y)
            if region == 'cell' or region == 'tree':
                item = app.tra_tree.identify_row(event.y)
                if item:
                    # Seleccionar el item
                    app.tra_tree.selection_set(item)
                    app.tra_tree.focus(item)
                    app.tra_current_selected_item = item
                    # Asegurar que sea visible
                    app.tra_tree.see(item)
        except Exception:
            pass
    
    def on_tra_select(event):
        """Maneja el evento de selección del treeview"""
        try:
            selected = app.tra_tree.selection()
            if selected:
                app.tra_current_selected_item = selected[0]
        except Exception:
            pass
    
    # Bindings de eventos
    app.tra_tree.bind('<Button-1>', on_tra_click)
    app.tra_tree.bind('<<TreeviewSelect>>', on_tra_select)
    
    # Layout
    app.tra_tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    # Inicializar diccionarios para filtros jerárquicos si no existen
    if not hasattr(app, 'tra_dept_dict'):
        app.tra_dept_dict = {}
    if not hasattr(app, 'tra_group_dict'):
        app.tra_group_dict = {}
    if not hasattr(app, 'tra_sub_dict'):
        app.tra_sub_dict = {}

    # Si hay conexión y los combos están vacíos, disparar carga unificada de jerarquías
    try:
        if hasattr(app, 'db_manager') and getattr(app.db_manager, 'ensure_connection', lambda: False)():
            if not app.tra_dept_dict:
                app.cargar_jerarquia_unificada()
    except Exception:
        pass
