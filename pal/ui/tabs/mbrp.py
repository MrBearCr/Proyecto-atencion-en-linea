"""
Pestaña MBRP (Movimiento de Baja Rotación de Producto)
Similar a TRA, enfocada en productos de rotación BAJA
"""
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import datetime, timedelta

def setup_mbrp_tab(app):
    # Frame raíz de la pestaña
    app.mbrp_tab_frame = ttk.Frame(app.mbrp_tab)
    app.mbrp_tab_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Controles superiores: fechas y sede
    top_controls = ttk.Frame(app.mbrp_tab_frame)
    top_controls.pack(fill=tk.X, pady=5)

    fecha_frame = ttk.Frame(top_controls)
    fecha_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Rango rápido
    ttk.Label(fecha_frame, text="Rango:").pack(side=tk.LEFT)
    app.mbrp_rango_var = tk.StringVar(value="30 días")
    rango_combo = ttk.Combobox(fecha_frame, textvariable=app.mbrp_rango_var, state='readonly', width=10)
    rango_combo['values'] = ["7 días", "15 días", "30 días", "60 días", "90 días", "Personalizado"]
    rango_combo.pack(side=tk.LEFT, padx=5)
    
    ttk.Label(fecha_frame, text="Desde:").pack(side=tk.LEFT, padx=(10,0))
    # Configurar fecha máxima: ayer (las ventas no se cargan hasta el cierre)
    ayer = datetime.now() - timedelta(days=1)
    # Ampliar rango para permitir análisis histórico hasta 365 días (1 año)
    hace_1_ano = ayer - timedelta(days=365)
    
    app.mbrp_fecha_inicio_entry = DateEntry(fecha_frame, width=12, date_pattern='yyyy-mm-dd',
                                           mindate=hace_1_ano, maxdate=ayer)
    app.mbrp_fecha_inicio_entry.set_date(ayer - timedelta(days=30))  # Default: últimos 30 días
    app.mbrp_fecha_inicio_entry.pack(side=tk.LEFT, padx=5)

    ttk.Label(fecha_frame, text="Hasta:").pack(side=tk.LEFT)
    app.mbrp_fecha_fin_entry = DateEntry(fecha_frame, width=12, date_pattern='yyyy-mm-dd',
                                        mindate=hace_1_ano, maxdate=ayer)
    app.mbrp_fecha_fin_entry.set_date(ayer)  # Default: hasta ayer
    app.mbrp_fecha_fin_entry.pack(side=tk.LEFT, padx=5)

    ttk.Label(fecha_frame, text="Sede:").pack(side=tk.LEFT, padx=10)
    app.mbrp_sede_var = tk.StringVar()
    app.mbrp_sede_combo = ttk.Combobox(fecha_frame, textvariable=app.mbrp_sede_var, state='readonly', width=15)
    app.mbrp_sede_combo['values'] = ["0301 - Cabudare", "0401 - Guanare", "0101 - Barinas"]
    app.mbrp_sede_combo.current(0)
    app.mbrp_sede_combo.pack(side=tk.LEFT)

    ttk.Button(top_controls, text="Cargar", command=app.cargar_mbrp_base).pack(side=tk.RIGHT, padx=10)
    ttk.Button(top_controls, text="📊 Reporte", command=app.generar_reporte_mbrp).pack(side=tk.RIGHT, padx=5)

    # Filtros jerárquicos
    filter_frame = ttk.Frame(app.mbrp_tab_frame)
    filter_frame.pack(fill=tk.X, pady=5)

    ttk.Label(filter_frame, text="Depto:").pack(side=tk.LEFT, padx=5)
    app.mbrp_dept_var = tk.StringVar(value='Todos')
    app.mbrp_dept_combo = ttk.Combobox(filter_frame, textvariable=app.mbrp_dept_var, state='readonly', width=20)
    app.mbrp_dept_combo['values'] = ['Todos']
    app.mbrp_dept_combo.pack(side=tk.LEFT, padx=5)

    ttk.Label(filter_frame, text="Grupo:").pack(side=tk.LEFT, padx=5)
    app.mbrp_group_var = tk.StringVar(value='Todos')
    app.mbrp_group_combo = ttk.Combobox(filter_frame, textvariable=app.mbrp_group_var, state='readonly', width=20)
    app.mbrp_group_combo['values'] = ['Todos']
    app.mbrp_group_combo.pack(side=tk.LEFT, padx=5)

    ttk.Label(filter_frame, text="Subgrupo:").pack(side=tk.LEFT, padx=5)
    app.mbrp_sub_var = tk.StringVar(value='Todos')
    app.mbrp_sub_combo = ttk.Combobox(filter_frame, textvariable=app.mbrp_sub_var, state='readonly', width=20)
    app.mbrp_sub_combo['values'] = ['Todos']
    app.mbrp_sub_combo.pack(side=tk.LEFT, padx=5)

    # Buscador
    search_frame = ttk.Frame(app.mbrp_tab_frame)
    search_frame.pack(fill=tk.X, pady=5)
    ttk.Label(search_frame, text="Buscar:").pack(side=tk.LEFT, padx=5)
    app.mbrp_search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=app.mbrp_search_var)
    search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    app.mbrp_search_var.trace_add('write', lambda *args: app.aplicar_filtro_mbrp())

    # Paginación
    pag_frame = ttk.Frame(app.mbrp_tab_frame)
    pag_frame.pack(fill=tk.X, pady=5)

    app.mbrp_btn_prev = ttk.Button(pag_frame, text="◄ Anterior", width=10, command=lambda: app.cambiar_pagina_mbrp(-1))
    app.mbrp_btn_prev.pack(side=tk.LEFT)

    app.mbrp_pagina_label = ttk.Label(pag_frame, text="Página 1/1", width=15)
    app.mbrp_pagina_label.pack(side=tk.LEFT, padx=5)

    app.mbrp_btn_next = ttk.Button(pag_frame, text="Siguiente ►", width=10, command=lambda: app.cambiar_pagina_mbrp(1))
    app.mbrp_btn_next.pack(side=tk.LEFT)

    # Tabla
    tree_frame = ttk.Frame(app.mbrp_tab_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)

    columns = ("Código", "Descripción", "Rotación", "Neto", "Stock Actual", "IM %", "Última Venta")
    app.mbrp_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=10)
    
    # Configurar tamaño de fuente y altura de filas más grandes
    style = ttk.Style()
    style.configure('LargeMBRP.Treeview', font=('', 11), rowheight=25)
    app.mbrp_tree.configure(style='LargeMBRP.Treeview')

    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=app.mbrp_tree.yview)
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=app.mbrp_tree.xview)
    app.mbrp_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    column_config = {
        "Código": {"width": 80, "anchor": "center"},
        "Descripción": {"width": 250, "anchor": "w"},
        "Rotación": {"width": 80, "anchor": "center"},
        "Neto": {"width": 100, "anchor": "e"},
        "Stock Actual": {"width": 90, "anchor": "center"},
        "IM %": {"width": 80, "anchor": "center"},
        "Última Venta": {"width": 110, "anchor": "center"},
    }

    for col in columns:
        app.mbrp_tree.heading(col, text=col)
        app.mbrp_tree.column(col, **column_config.get(col, {"width": 120, "anchor": "center"}))

    # Colores para MBRP - resaltar productos de BAJA movilidad (inverso a TRA)
    app.mbrp_tree.tag_configure('alta', background='#607D8B', foreground='#FFFFFF', font=('', 11))  # Gris azulado vibrante (menos importante en MBRP)
    app.mbrp_tree.tag_configure('media', background='#FF9800', foreground='#FFFFFF', font=('', 11))  # Naranja vibrante
    app.mbrp_tree.tag_configure('baja', background='#E91E63', foreground='#FFFFFF', font=('', 11, 'bold'))  # Rosa vibrante + negrita
    app.mbrp_tree.tag_configure('sin_movimiento', background='#D32F2F', foreground='#FFFFFF', font=('', 11, 'bold'))  # Rojo vibrante + texto blanco
    app.mbrp_tree.tag_configure('sin_clasificar', background='#9C27B0', foreground='#FFFFFF', font=('', 11))  # Púrpura vibrante
    app.mbrp_tree.tag_configure('loading', background='#2196F3', foreground='#FFFFFF', font=('', 12, 'italic'))  # Azul vibrante
    
    # Colores adicionales por Índice de Movilidad
    app.mbrp_tree.tag_configure('im_critico', background='#B71C1C', foreground='#FFFFFF', font=('', 11, 'bold'))  # IM < 5% - Rojo muy vibrante
    app.mbrp_tree.tag_configure('im_muy_bajo', background='#D32F2F', foreground='#FFFFFF', font=('', 11, 'bold'))  # IM 5-10% - Rojo vibrante
    app.mbrp_tree.tag_configure('im_bajo', background='#FF5722', foreground='#FFFFFF', font=('', 11))  # IM 10-20% - Naranja rojizo vibrante
    
    # Efectos de hover y selección mejorados
    app.mbrp_tree.tag_configure('hover', background='#FFC107', foreground='#000000', font=('', 11, 'bold'))  # Amarillo brillante hover
    app.mbrp_tree.tag_configure('selected', background='#1976D2', foreground='#FFFFFF', font=('', 11, 'bold'))  # Azul intenso selección

    # Eventos de hover y selección mejorados
    def on_mbrp_hover(event):
        try:
            item = app.mbrp_tree.identify_row(event.y)
            if item:
                app.mbrp_tree.tk.call(app.mbrp_tree, 'tag', 'remove', 'hover', '')
                app.mbrp_tree.tk.call(app.mbrp_tree, 'tag', 'add', 'hover', item)
                app.mbrp_tree.config(cursor='hand2')
        except Exception:
            pass
        return "break"
    
    def on_mbrp_leave(event):
        try:
            app.mbrp_tree.tk.call(app.mbrp_tree, 'tag', 'remove', 'hover', '')
            app.mbrp_tree.config(cursor='')
        except Exception:
            pass
        return "break"
    
    def on_mbrp_select(event):
        try:
            selected = app.mbrp_tree.selection()
            if selected:
                app.mbrp_tree.tk.call(app.mbrp_tree, 'tag', 'remove', 'selected', '')
                app.mbrp_tree.tk.call(app.mbrp_tree, 'tag', 'add', 'selected', selected[0])
                # Efecto de parpadeo
                def parpadeo():
                    try:
                        app.mbrp_tree.tk.call(app.mbrp_tree, 'tag', 'remove', 'selected', selected[0])
                        app.root.after(150, lambda: app.mbrp_tree.tk.call(app.mbrp_tree, 'tag', 'add', 'selected', selected[0]))
                    except Exception:
                        pass
                app.root.after(100, parpadeo)
        except Exception:
            pass
        return "break"
    
    # Bindings de eventos
    app.mbrp_tree.bind('<Motion>', on_mbrp_hover)
    app.mbrp_tree.bind('<Leave>', on_mbrp_leave)
    app.mbrp_tree.bind('<<TreeviewSelect>>', on_mbrp_select)
    
    # Layout
    app.mbrp_tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    # Inicializar diccionarios vacíos - se cargarán cuando se conecte a BD
    app.mbrp_dept_dict = {}
    app.mbrp_group_dict = {}
    app.mbrp_sub_dict = {}
    app.mbrp_dept_combo['values'] = ['Todos']
    app.mbrp_dept_var.set('Todos')

    # Si hay conexión y combos vacíos, disparar carga unificada (reutiliza misma jerarquía que TRA)
    try:
        if hasattr(app, 'db_manager') and getattr(app.db_manager, 'ensure_connection', lambda: False)():
            if not app.mbrp_dept_dict:
                app.cargar_jerarquia_unificada()
    except Exception:
        pass

    # Bindings de filtros (idénticos a TRA, pero con prefijo mbrp_)
    def _on_mbrp_dept_selected(event=None):
        desc = app.mbrp_dept_var.get()
        dept_cod = app.mbrp_dept_dict.get(desc)
        app.mbrp_group_dict = {}
        app.mbrp_sub_dict = {}
        # Solo consultar BD si hay conexión activa
        if dept_cod and hasattr(app.db_manager, 'conn') and app.db_manager.conn:
            try:
                grupos = app.db_manager.fetch_data(
                    "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_GRUPOS WHERE C_DEPARTAMENTO = ?",
                    (dept_cod,)
                )
                app.mbrp_group_dict = {desc: cod for cod, desc in grupos if cod and desc}
            except Exception:
                app.mbrp_group_dict = {}
        app.mbrp_group_combo['values'] = ['Todos'] + list(app.mbrp_group_dict.keys())
        app.mbrp_group_var.set('Todos')
        app.mbrp_sub_combo['values'] = ['Todos']
        app.mbrp_sub_var.set('Todos')
        if hasattr(app, 'aplicar_filtro_mbrp'):
            app.aplicar_filtro_mbrp()

    def _on_mbrp_group_selected(event=None):
        dept_desc = app.mbrp_dept_var.get()
        dept_cod = app.mbrp_dept_dict.get(dept_desc)
        group_desc = app.mbrp_group_var.get()
        group_cod = app.mbrp_group_dict.get(group_desc)
        app.mbrp_sub_dict = {}
        # Solo consultar BD si hay conexión activa
        if dept_cod and group_cod and hasattr(app.db_manager, 'conn') and app.db_manager.conn:
            try:
                subs = app.db_manager.fetch_data(
                    "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_SUBGRUPOS WHERE C_IN_DEPARTAMENTO = ? AND C_IN_GRUPO = ?",
                    (dept_cod, group_cod)
                )
                app.mbrp_sub_dict = {desc: cod for cod, desc in subs if cod and desc}
            except Exception:
                app.mbrp_sub_dict = {}
        app.mbrp_sub_combo['values'] = ['Todos'] + list(app.mbrp_sub_dict.keys())
        app.mbrp_sub_var.set('Todos')
        if hasattr(app, 'aplicar_filtro_mbrp'):
            app.aplicar_filtro_mbrp()

    def _on_mbrp_sub_selected(event=None):
        if hasattr(app, 'aplicar_filtro_mbrp'):
            app.aplicar_filtro_mbrp()

    # Funcionalidad del combobox de rango
    def _on_mbrp_rango_selected(event=None):
        rango = app.mbrp_rango_var.get()
        ayer = datetime.now() - timedelta(days=1)
        hace_1_ano = ayer - timedelta(days=365)
        
        if rango == "Personalizado":
            # Mostrar mensaje informativo sobre el rango permitido
            try:
                app.log(f"Rango personalizado seleccionado. Fechas permitidas: {hace_1_ano.strftime('%Y-%m-%d')} a {ayer.strftime('%Y-%m-%d')}", "INFO")
            except Exception:
                pass
            return
        
        # Extraer número de días
        dias = int(rango.split()[0])
        fecha_inicio = ayer - timedelta(days=dias-1)  # -1 porque incluimos el día actual
        
        # Asegurar que la fecha no exceda el límite mínimo
        if fecha_inicio < hace_1_ano:
            fecha_inicio = hace_1_ano
            try:
                app.log(f"Fecha inicio ajustada al límite mínimo: {hace_1_ano.strftime('%Y-%m-%d')}", "WARNING")
            except Exception:
                pass
        
        app.mbrp_fecha_inicio_entry.set_date(fecha_inicio)
        app.mbrp_fecha_fin_entry.set_date(ayer)
    
    rango_combo.bind('<<ComboboxSelected>>', _on_mbrp_rango_selected)
    app.mbrp_dept_combo.bind('<<ComboboxSelected>>', _on_mbrp_dept_selected)
    app.mbrp_group_combo.bind('<<ComboboxSelected>>', _on_mbrp_group_selected)
    app.mbrp_sub_combo.bind('<<ComboboxSelected>>', _on_mbrp_sub_selected)
