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

    ttk.Label(fecha_frame, text="Desde:").pack(side=tk.LEFT)
    app.fecha_inicio_entry = DateEntry(fecha_frame, width=12, date_pattern='yyyy-mm-dd')
    app.fecha_inicio_entry.set_date(datetime(datetime.now().year, 1, 1))
    app.fecha_inicio_entry.pack(side=tk.LEFT, padx=5)

    ttk.Label(fecha_frame, text="Hasta:").pack(side=tk.LEFT)
    app.fecha_fin_entry = DateEntry(fecha_frame, width=12, date_pattern='yyyy-mm-dd')
    app.fecha_fin_entry.set_date(datetime.now())
    app.fecha_fin_entry.pack(side=tk.LEFT, padx=5)

    ttk.Label(fecha_frame, text="Sede:").pack(side=tk.LEFT, padx=10)
    app.sede_var = tk.StringVar()
    app.sede_combo = ttk.Combobox(fecha_frame, textvariable=app.sede_var, state='readonly', width=15)
    app.sede_combo['values'] = ["0301 - Cabudare", "0401 - Guanare", "0101 - Barinas"]
    app.sede_combo.current(0)  # Seleccionar primer elemento por defecto
    app.sede_combo.pack(side=tk.LEFT)

    # Botón de cargar (función básica por ahora)
    def cargar_tra_basico():
        messagebox.showinfo("TRA", "Funcionalidad TRA cargada (versión básica)")
    
    ttk.Button(top_controls, text="Cargar", command=cargar_tra_basico).pack(side=tk.RIGHT, padx=10)

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

    # Buscador de texto
    search_frame = ttk.Frame(app.tra_tab_frame)
    search_frame.pack(fill=tk.X, pady=5)

    ttk.Label(search_frame, text="Buscar:").pack(side=tk.LEFT, padx=5)
    app.tra_search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=app.tra_search_var)
    search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    # Controles de paginación
    pag_frame = ttk.Frame(app.tra_tab_frame)
    pag_frame.pack(fill=tk.X, pady=5)

    app.tra_btn_prev = ttk.Button(
        pag_frame, 
        text="◄ Anterior", 
        width=10, 
        state='disabled'
    )
    app.tra_btn_prev.pack(side=tk.LEFT)

    app.tra_pagina_label = ttk.Label(pag_frame, text="Página 1/1", width=15)
    app.tra_pagina_label.pack(side=tk.LEFT, padx=5)

    app.tra_btn_next = ttk.Button(
        pag_frame, 
        text="Siguiente ►", 
        width=10
    )
    app.tra_btn_next.pack(side=tk.LEFT)

    # Frame para tabla con scrollbars
    tree_frame = ttk.Frame(app.tra_tab_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)

    columns = ("Código", "Descripción", "Rotación", "Neto", "Stock Ideal")
    app.tra_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)

    # Configurar scrollbars
    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=app.tra_tree.yview)
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=app.tra_tree.xview)
    app.tra_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # Configurar columnas
    for col in columns:
        app.tra_tree.heading(col, text=col)
        app.tra_tree.column(col, width=120, anchor='center')

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