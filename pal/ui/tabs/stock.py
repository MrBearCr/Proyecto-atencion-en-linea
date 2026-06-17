"""
Módulo de configuración de pestaña de Stock
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import math

def setup_stock_tab(app):
    """Configura la pestaña de Quiebre de Stock en la aplicación"""
    if not app.modules_enabled.get("stock", False):
        return
    main_frame = ttk.Frame(app.stock_tab)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # ① --- Frame superior de Información ---
    top_controls = ttk.Frame(main_frame)
    top_controls.pack(fill=tk.X, pady=5)

    info_label = ttk.Label(top_controls, 
                           text="🚨 Monitor Automático de Quiebres (Basado en los últimos 30 días)",
                           font=('', 10, 'bold'), foreground="#D32F2F")
    info_label.pack(side=tk.LEFT, pady=5)

    # ② --- Frame de Filtros Jerárquicos y Búsqueda ---
    filter_frame = ttk.Frame(main_frame)
    filter_frame.pack(fill=tk.X, pady=5)

    # Departamentos
    ttk.Label(filter_frame, text="Depto:").pack(side=tk.LEFT, padx=5)
    app.stock_dept_var = tk.StringVar(value='Todos')
    app.stock_dept_combo = ttk.Combobox(filter_frame, textvariable=app.stock_dept_var, state='readonly', width=18)
    app.stock_dept_combo['values'] = ['Todos']
    app.stock_dept_combo.pack(side=tk.LEFT, padx=5)
    app.stock_dept_combo.bind('<<ComboboxSelected>>', lambda e: getattr(app, 'on_stock_dept_selected', lambda x: None)(e))

    # Grupos
    ttk.Label(filter_frame, text="Grupo:").pack(side=tk.LEFT, padx=5)
    app.stock_group_var = tk.StringVar(value='Todos')
    app.stock_group_combo = ttk.Combobox(filter_frame, textvariable=app.stock_group_var, state='readonly', width=18)
    app.stock_group_combo['values'] = ['Todos']
    app.stock_group_combo.pack(side=tk.LEFT, padx=5)
    app.stock_group_combo.bind('<<ComboboxSelected>>', lambda e: getattr(app, 'on_stock_group_selected', lambda x: None)(e))

    # Subgrupos
    ttk.Label(filter_frame, text="Subgrupo:").pack(side=tk.LEFT, padx=5)
    app.stock_subgroup_var = tk.StringVar(value='Todos')
    app.stock_subgroup_combo = ttk.Combobox(filter_frame, textvariable=app.stock_subgroup_var, state='readonly', width=18)
    app.stock_subgroup_combo['values'] = ['Todos']
    app.stock_subgroup_combo.pack(side=tk.LEFT, padx=5)
    app.stock_subgroup_combo.bind('<<ComboboxSelected>>', lambda e: app.aplicar_filtro_stock())

    # Búsqueda por texto
    ttk.Label(filter_frame, text="🔍 Buscar:").pack(side=tk.LEFT, padx=(15, 5))
    app.stock_search_var = tk.StringVar()
    app.stock_search_entry = ttk.Entry(filter_frame, textvariable=app.stock_search_var, width=25)
    app.stock_search_entry.pack(side=tk.LEFT, padx=5)
    app.stock_search_entry.bind('<KeyRelease>', lambda e: app.aplicar_filtro_stock())

    # ③ --- Acciones y Paginación ---
    action_frame = ttk.Frame(main_frame)
    action_frame.pack(fill=tk.X, pady=5)
    
    # Exportar
    can_export_stock = False
    try:
        if hasattr(app, 'permissions') and app.current_user:
            can_export_stock = app.permissions.tiene_permiso(app.current_user['id'], 'STOCK', 'exportar')
        if app.current_user and app.current_user.get('username','').lower() == 'admin':
            can_export_stock = True
    except Exception:
        can_export_stock = False
        
    btn_export_stock = ttk.Button(action_frame, text="📈 Exportar Excel", 
               command=lambda: getattr(app, 'exportar_stock_excel', lambda: None)())
    btn_export_stock.pack(side=tk.LEFT, padx=5)
    if not can_export_stock:
        btn_export_stock.state(["disabled"])

    # Checkbox para solo alta rotación
    app.stock_solo_alta_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(action_frame, text="Solo Alta/Media Rotación", 
                    variable=app.stock_solo_alta_var,
                    command=lambda: app.actualizar_alertas_stock(force_refresh=True)).pack(side=tk.LEFT, padx=15)

    # Botón Recargar (Ahora unificado)
    ttk.Button(action_frame, text="🔄 Recargar Módulo", 
               command=app.recargar_stock).pack(side=tk.LEFT, padx=5)

    pagination_frame = ttk.Frame(action_frame)
    pagination_frame.pack(side=tk.RIGHT)
    app.btn_prev_stock = ttk.Button(pagination_frame, text="◄ Anterior", 
                              command=lambda: app.cambiar_pagina_stock(-1), width=10)
    app.btn_prev_stock.pack(side=tk.LEFT)
    app.stock_pagination_label = ttk.Label(pagination_frame, text="Página 1/1", width=15)
    app.stock_pagination_label.pack(side=tk.LEFT, padx=5)
    app.btn_next_stock = ttk.Button(pagination_frame, text="Siguiente ►", 
                              command=lambda: app.cambiar_pagina_stock(1), width=10)
    app.btn_next_stock.pack(side=tk.LEFT)

    # ④ --- Tabla de Datos ---
    columns_config = {
        "Favorito": {"width": 50, "anchor": "center", "stretch": False},
        "Código": {"width": 100, "anchor": "center"},
        "Descripción": {"width": 280, "anchor": "w"},
        "Sede": {"width": 100, "anchor": "center"},
        "Unid. Perdidas": {"width": 110, "anchor": "center"},
        "Días Quiebre": {"width": 100, "anchor": "center"},
        "Últ. Liquidación": {"width": 100, "anchor": "center"},
        "Últ. Venta": {"width": 100, "anchor": "center"},
    }

    tree_frame = ttk.Frame(main_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    app.stock_tree = ttk.Treeview(tree_frame, columns=list(columns_config.keys()), show="headings", height=10)
    
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

    for col, config in columns_config.items():
        app.stock_tree.heading(col, text=col)
        app.stock_tree.column(col, **config)

    # Colores amigables: Azul suave para quiebres, Amarillo suave para favoritos, Verde suave para nuevos
    app.stock_tree.tag_configure('quiebre', background='#E3F2FD', foreground='#000000', font=('', 11))
    app.stock_tree.tag_configure('favorito', background='#FFF9C4', foreground='#000000', font=('', 11, 'bold'))
    app.stock_tree.tag_configure('nuevo_quiebre', background='#E8F5E9', foreground='#000000', font=('', 11, 'bold'))

    style.map('LargeStock.Treeview',
        background=[('selected', '#0D47A1')],
        foreground=[('selected', '#FFFFFF')]
    )
    
    app.current_selected_stock_item = None
    
    def on_tree_click(event):
        try:
            col = app.stock_tree.identify_column(event.x)
            if col == '#1': 
                getattr(app, 'on_favorito_click', lambda x: None)(event)
            else:
                item = app.stock_tree.identify_row(event.y)
                if item:
                    app.stock_tree.selection_set(item)
                    app.stock_tree.focus(item)
                    app.current_selected_stock_item = item
        except Exception:
            pass
    
    app.stock_tree.bind('<Button-1>', on_tree_click)

    # Carga inicial
    app.stock_current_page = 1
    app.stock_page_size = 250
    if hasattr(app, 'db_manager') and hasattr(app.db_manager, 'conn') and app.db_manager.conn:
        if hasattr(app, 'load_stock_filters'):
            app.load_stock_filters()
        # No disparamos carga automática inmediata para no saturar al inicio, 
        # esperar a que el usuario haga clic o la app esté lista.
