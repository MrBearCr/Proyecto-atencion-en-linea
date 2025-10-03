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

    ttk.Button(action_frame, text="📥 Exportar CSV", 
               command=lambda: getattr(app, 'exportar_csv', lambda: None)()).pack(side=tk.LEFT, padx=5)

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

    app.stock_tree = ttk.Treeview(tree_frame, columns=list(columns_config.keys()), show="headings", height=15)
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

    # Estilos de filas
    app.stock_tree.tag_configure('leve', background='#abebc6')
    app.stock_tree.tag_configure('media', background='#DAF7A6')
    app.stock_tree.tag_configure('critica', background='#ff856b')
    app.stock_tree.tag_configure('favorito', background='#FFFFE0')
    app.stock_tree.tag_configure('hover', background='#f0f0f0')
    app.stock_tree.tag_configure('selected', background='#d0d0d0')

    app.stock_tree.bind('<Button-1>', lambda e: getattr(app, 'on_favorito_click', lambda x: None)(e))
    app.stock_tree.bind('<Enter>', lambda e: getattr(app, 'hover_row', lambda x: None)(e))
    app.stock_tree.bind('<Leave>', lambda e: getattr(app, 'leave_row', lambda x: None)(e))
    app.stock_tree.bind('<<TreeviewSelect>>', lambda e: getattr(app, 'select_row', lambda x: None)(e))

    # Carga inicial solo si hay conexión
    app.current_page = 1
    app.page_size = 250
    if hasattr(app, 'db_manager') and hasattr(app.db_manager, 'conn') and app.db_manager.conn:
        if hasattr(app, 'load_stock_filters'):
            app.load_stock_filters()
        if hasattr(app, 'aplicar_filtro_stock'):
            app.aplicar_filtro_stock()
    else:
        print("No hay conexión activa a la base de datos para cargar alertas iniciales")
