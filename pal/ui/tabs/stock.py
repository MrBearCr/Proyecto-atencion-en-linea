"""
Módulo de configuración de pestaña de Stock
"""
import tkinter as tk
from tkinter import ttk
import math

def setup_stock_tab(app):
    """Configura la pestaña de Stock en la aplicación"""
    if not app.modules_enabled.get("stock", False):
        return
    main_frame = ttk.Frame(app.stock_tab)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # ① --- Filtros jerárquicos ---
    hier_frame = ttk.Frame(main_frame)
    hier_frame.pack(fill=tk.X, pady=5)

    # Departamento
    ttk.Label(hier_frame, text="Departamento:").pack(side=tk.LEFT)
    app.dept_var = tk.StringVar(value='Todos')
    app.dept_combo = ttk.Combobox(hier_frame, textvariable=app.dept_var, state='readonly')
    app.dept_combo['values'] = ['Todos']
    app.dept_combo.pack(side=tk.LEFT, padx=5)
    app.dept_combo.bind('<<ComboboxSelected>>', lambda e: getattr(app, 'on_dept_selected', lambda: None)())

    # Grupo
    ttk.Label(hier_frame, text="Grupo:").pack(side=tk.LEFT)
    app.group_var = tk.StringVar(value='Todos')
    app.group_combo = ttk.Combobox(hier_frame, textvariable=app.group_var, state='readonly')
    app.group_combo['values'] = ['Todos']
    app.group_combo.pack(side=tk.LEFT, padx=5)
    app.group_combo.bind('<<ComboboxSelected>>', lambda e: getattr(app, 'on_group_selected', lambda: None)())

    # Subgrupo
    ttk.Label(hier_frame, text="Subgrupo:").pack(side=tk.LEFT)
    app.sub_var = tk.StringVar(value='Todos')
    app.sub_combo = ttk.Combobox(hier_frame, textvariable=app.sub_var, state='readonly')
    app.sub_combo['values'] = ['Todos']
    app.sub_combo.pack(side=tk.LEFT, padx=5)
    app.sub_combo.bind('<<ComboboxSelected>>', lambda e: getattr(app, 'aplicar_filtro_stock', lambda: None)())
    # --------------------------------

    # Filtro de texto
    search_frame = ttk.Frame(main_frame)
    search_frame.pack(fill=tk.X, pady=5)
    ttk.Label(search_frame, text="Buscar Descripción:").pack(side=tk.LEFT)
    app.search_var = tk.StringVar()
    entry_search = ttk.Entry(search_frame, textvariable=app.search_var)
    entry_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    app.search_var.trace_add('write', lambda *args: getattr(app, 'aplicar_filtro_stock', lambda: None)())

    # Controles superiores en dos filas
    top_controls = ttk.Frame(main_frame)
    top_controls.pack(fill=tk.X, pady=5)

    # Fila 1: Filtros de nivel
    filter_frame = ttk.Frame(top_controls)
    filter_frame.pack(fill=tk.X, pady=5)
    ttk.Label(filter_frame, text="Filtrar:").pack(side=tk.LEFT)
    app.filter_var = tk.StringVar(value='TODAS')
    app.current_filter = 'TODAS'

    filters = [
        ('Todas', 'TODAS'),
        ('Críticas (<8)', 'CRÍTICA'),
        ('Medias (8-14)', 'MEDIA'),
        ('Leves (15-20)', 'LEVE')
    ]

    for text, val in filters:
        ttk.Radiobutton(
            filter_frame,
            text=text,
            variable=app.filter_var,
            value=val,
            command=lambda v=val: (
                setattr(app, 'current_page', 1),
                setattr(app, 'current_filter', v),
                getattr(app, 'aplicar_filtro_stock', lambda: None)()
            )
        ).pack(side=tk.LEFT, padx=5)

    # Fila 2: Acciones y paginación
    action_frame = ttk.Frame(top_controls)
    action_frame.pack(fill=tk.X, pady=5)

    
    # Exportar (respetar permisos)
    can_export_stock = False
    try:
        if hasattr(app, 'permissions') and app.current_user:
            can_export_stock = app.permissions.tiene_permiso(app.current_user['id'], 'STOCK', 'exportar')
        if app.current_user and app.current_user.get('username','').lower() == 'admin':
            can_export_stock = True
    except Exception:
        can_export_stock = False
    btn_export_stock = ttk.Button(action_frame, text="📈 Exportar Excel", 
               command=lambda: getattr(app, 'exportar_excel', lambda: None)())
    btn_export_stock.pack(side=tk.LEFT, padx=5)
    if not can_export_stock:
        try:
            btn_export_stock.state(["disabled"])  # ttk style
        except Exception:
            btn_export_stock.config(state='disabled')
    
    ttk.Button(action_frame, text="🔄 Recargar", 
               command=lambda: getattr(app, 'recargar_stock', lambda: None)()).pack(side=tk.LEFT, padx=5)

    pagination_frame = ttk.Frame(action_frame)
    pagination_frame.pack(side=tk.RIGHT)
    app.btn_prev = ttk.Button(pagination_frame, text="◄ Anterior", 
                              command=lambda: getattr(app, 'cambiar_pagina', lambda x: None)(-1), width=10)
    app.btn_prev.pack(side=tk.LEFT)
    app.pagination_label = ttk.Label(pagination_frame, text="Página 1/1", width=15)
    app.pagination_label.pack(side=tk.LEFT, padx=5)
    app.btn_next = ttk.Button(pagination_frame, text="Siguiente ►", 
                              command=lambda: getattr(app, 'cambiar_pagina', lambda x: None)(1), width=10)
    app.btn_next.pack(side=tk.LEFT)

    # Árbol de datos
    tree_frame = ttk.Frame(main_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)

    columns_config = {
        "Favorito": {"width": 50, "anchor": "center", "stretch": False},
        "Código": {"width": 100, "anchor": "center"},
        "Descripción": {"width": 350, "anchor": "w"},
        "Stock": {"width": 80, "anchor": "center"},
        "Nivel": {"width": 100, "anchor": "center"}
    }

    app.stock_tree = ttk.Treeview(tree_frame, columns=list(columns_config.keys()), show="headings", height=10)
    
    # Configurar tamaño de fuente y altura de filas más grandes
    style = ttk.Style()
    style.configure('LargeStock.Treeview', font=('', 11), rowheight=25)
    app.stock_tree.configure(style='LargeStock.Treeview')
    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=app.stock_tree.yview)
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=app.stock_tree.xview)
    app.stock_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    app.stock_tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    # Configurar columnas y encabezados
    for col, config in columns_config.items():
        app.stock_tree.heading(col, text=col)
        app.stock_tree.column(col, **config)

    # Estilos de filas con bordes visuales (colores más oscuros para resaltar líneas)
    app.stock_tree.tag_configure('leve', background='#4CAF50', foreground='#FFFFFF', font=('', 11))  # Verde vibrante
    app.stock_tree.tag_configure('media', background='#FF9800', foreground='#FFFFFF', font=('', 11))  # Naranja vibrante
    app.stock_tree.tag_configure('critica', background='#F44336', foreground='#FFFFFF', font=('', 11))  # Rojo vibrante
    
    # Estilos alternados para mejor distinción de filas
    app.stock_tree.tag_configure('leve_alt', background='#388E3C', foreground='#FFFFFF', font=('', 11))  # Verde más oscuro
    app.stock_tree.tag_configure('media_alt', background='#F57C00', foreground='#FFFFFF', font=('', 11))  # Naranja más oscuro
    app.stock_tree.tag_configure('critica_alt', background='#D32F2F', foreground='#FFFFFF', font=('', 11))  # Rojo más oscuro
    
    app.stock_tree.tag_configure('favorito', background='#FFC107', foreground='#000000', font=('', 11, 'bold'))  # Amarillo vibrante

    # Configurar colores de selección en el style para que funcione correctamente
    style.map('LargeStock.Treeview',
        background=[('selected', '#0D47A1')],  # Azul oscuro para selección
        foreground=[('selected', '#FFFFFF')]   # Texto blanco para contraste
    )
    
    # Variable para rastrear el ítem actualmente seleccionado
    app.current_selected_item = None
    
    # Eventos mejorados con efectos visuales
    def on_stock_click(event):
        """Maneja el click en una fila del treeview"""
        try:
            region = app.stock_tree.identify_region(event.x, event.y)
            if region == 'cell' or region == 'tree':
                item = app.stock_tree.identify_row(event.y)
                if item:
                    # Seleccionar el item
                    app.stock_tree.selection_set(item)
                    app.stock_tree.focus(item)
                    app.current_selected_item = item
                    # Asegurar que sea visible
                    app.stock_tree.see(item)
        except Exception:
            pass
    
    def on_stock_select(event):
        """Maneja el evento de selección del treeview"""
        try:
            selected = app.stock_tree.selection()
            if selected:
                app.current_selected_item = selected[0]
        except Exception:
            pass
    
    # Bind para favoritos (solo en columna de favoritos)
    def on_tree_click(event):
        """Maneja clicks distinguiendo entre favorito y selección de fila"""
        try:
            col = app.stock_tree.identify_column(event.x)
            if col == '#1':  # Primera columna (Favorito)
                getattr(app, 'on_favorito_click', lambda x: None)(event)
            else:
                on_stock_click(event)
        except Exception:
            pass
    
    app.stock_tree.bind('<Button-1>', on_tree_click)
    app.stock_tree.bind('<<TreeviewSelect>>', on_stock_select)

    # Carga inicial solo si hay conexión
    app.current_page = 1
    app.page_size = 250
    if hasattr(app, 'db_manager') and hasattr(app.db_manager, 'conn') and app.db_manager.conn:
        if hasattr(app, 'load_stock_filters'):
            app.load_stock_filters()
        if hasattr(app, 'aplicar_filtro_stock'):
            app.aplicar_filtro_stock()
    else:
        (getattr(app, 'log', print))("No hay conexión activa a la base de datos para cargar alertas iniciales", "DEBUG")
