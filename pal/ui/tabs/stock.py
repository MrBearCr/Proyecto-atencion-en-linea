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

    
    ttk.Button(action_frame, text="📈 Exportar Excel", 
               command=lambda: getattr(app, 'exportar_excel', lambda: None)()).pack(side=tk.LEFT, padx=5)
    
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

    # Estilos de filas
    app.stock_tree.tag_configure('leve', background='#4CAF50', foreground='#FFFFFF', font=('', 11))  # Verde vibrante
    app.stock_tree.tag_configure('media', background='#FF9800', foreground='#FFFFFF', font=('', 11))  # Naranja vibrante
    app.stock_tree.tag_configure('critica', background='#F44336', foreground='#FFFFFF', font=('', 11))  # Rojo vibrante
    app.stock_tree.tag_configure('favorito', background='#FFC107', foreground='#000000', font=('', 11))  # Amarillo vibrante
    app.stock_tree.tag_configure('hover', background='#FFE082', foreground='#000000', font=('', 11, 'bold'))  # Amarillo brillante hover
    app.stock_tree.tag_configure('selected', background='#1976D2', foreground='#FFFFFF', font=('', 11, 'bold'))  # Azul intenso seleccionado

    # Eventos mejorados con efectos visuales
    def on_stock_hover(event):
        try:
            item = app.stock_tree.identify_row(event.y)
            if item:
                app.stock_tree.tk.call(app.stock_tree, 'tag', 'remove', 'hover', '')
                app.stock_tree.tk.call(app.stock_tree, 'tag', 'add', 'hover', item)
                app.stock_tree.config(cursor='hand2')
        except Exception:
            pass
        return "break"
    
    def on_stock_leave(event):
        try:
            app.stock_tree.tk.call(app.stock_tree, 'tag', 'remove', 'hover', '')
            app.stock_tree.config(cursor='')
        except Exception:
            pass
        return "break"
    
    def on_stock_select(event):
        try:
            selected = app.stock_tree.selection()
            if selected:
                app.stock_tree.tk.call(app.stock_tree, 'tag', 'remove', 'selected', '')
                app.stock_tree.tk.call(app.stock_tree, 'tag', 'add', 'selected', selected[0])
                # Efecto de parpadeo
                def parpadeo():
                    try:
                        app.stock_tree.tk.call(app.stock_tree, 'tag', 'remove', 'selected', selected[0])
                        app.root.after(150, lambda: app.stock_tree.tk.call(app.stock_tree, 'tag', 'add', 'selected', selected[0]))
                    except Exception:
                        pass
                app.root.after(100, parpadeo)
        except Exception:
            pass
        
        # Llamar a la función de selección existente también
        try:
            getattr(app, 'select_row', lambda x: None)(event)
        except Exception:
            pass
        return "break"
    
    app.stock_tree.bind('<Button-1>', lambda e: getattr(app, 'on_favorito_click', lambda x: None)(e))
    app.stock_tree.bind('<Motion>', on_stock_hover)
    app.stock_tree.bind('<Leave>', on_stock_leave)
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
