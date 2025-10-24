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
    app.sede_combo = ttk.Combobox(fecha_frame, textvariable=app.sede_var, state='readonly', width=15)
    app.sede_combo['values'] = ["0301 - Cabudare", "0401 - Guanare", "0101 - Barinas"]
    app.sede_combo.current(0)  # Seleccionar primer elemento por defecto
    app.sede_combo.pack(side=tk.LEFT)

    # Botones de acción
    ttk.Button(top_controls, text="📈 Exportar Excel", 
               command=lambda: getattr(app, 'exportar_tra_excel', lambda: None)()).pack(side=tk.RIGHT, padx=5)
    ttk.Button(top_controls, text="Cargar", command=app.cargar_tra_base).pack(side=tk.RIGHT, padx=10)

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
    
    # Conectar eventos de búsqueda y filtros
    rango_combo.bind('<<ComboboxSelected>>', _on_tra_rango_selected)
    app.tra_search_var.trace_add('write', lambda *args: app.aplicar_filtro_tra())
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

    columns = ("Código", "Descripción", "Rotación", "Neto", "Representación %", "Stock Actual", "Stock Ideal", "Días Restantes")
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
        "Neto": {"width": 100, "anchor": "e"},
        "Representación %": {"width": 100, "anchor": "center"},
        "Stock Actual": {"width": 80, "anchor": "center"},
        "Stock Ideal": {"width": 80, "anchor": "center"},
        "Días Restantes": {"width": 100, "anchor": "center"}
    }
    
    for col in columns:
        app.tra_tree.heading(col, text=col)
        config = column_config.get(col, {"width": 120, "anchor": "center"})
        app.tra_tree.column(col, **config)
    
    # Configurar estilos de colores para rotación (fondos vivos + texto blanco + fuente grande)
    app.tra_tree.tag_configure('alta', background='#4CAF50', foreground='#FFFFFF', font=('', 11))  # Verde vibrante
    app.tra_tree.tag_configure('media', background='#FF9800', foreground='#FFFFFF', font=('', 11))  # Naranja vibrante
    app.tra_tree.tag_configure('baja', background='#F44336', foreground='#FFFFFF', font=('', 11))  # Rojo vibrante
    app.tra_tree.tag_configure('sin_movimiento', background='#9E9E9E', foreground='#FFFFFF', font=('', 11))  # Gris vibrante
    app.tra_tree.tag_configure('sin_clasificar', background='#9C27B0', foreground='#FFFFFF', font=('', 11))  # Púrpura vibrante
    
    # Efectos de hover y selección mejorados
    app.tra_tree.tag_configure('hover', background='#FFE082', foreground='#000000', font=('', 11, 'bold'))  # Amarillo brillante hover
    app.tra_tree.tag_configure('selected', background='#1976D2', foreground='#FFFFFF', font=('', 11, 'bold'))  # Azul intenso selección
    
    # Estilos por representación (mantener texto blanco y fuente grande)
    app.tra_tree.tag_configure('high_representation', foreground='#FFFFFF', font=('', 11))
    app.tra_tree.tag_configure('medium_representation', foreground='#FFFFFF', font=('', 11))
    app.tra_tree.tag_configure('low_representation', foreground='#FFFFFF', font=('', 11))
    
    # Estilos para mensajes de estado
    app.tra_tree.tag_configure('loading', background='#2196F3', foreground='#FFFFFF', font=('', 12, 'italic'))  # Azul vibrante
    app.tra_tree.tag_configure('no_data', background='#FF9800', foreground='#FFFFFF', font=('', 12, 'italic'))  # Naranja vibrante
    app.tra_tree.tag_configure('error', background='#F44336', foreground='#FFFFFF', font=('', 12, 'italic'))  # Rojo vibrante

    # Eventos de hover y selección mejorados
    def on_tra_hover(event):
        try:
            item = app.tra_tree.identify_row(event.y)
            if item:
                # Limpiar hover previo
                app.tra_tree.tk.call(app.tra_tree, 'tag', 'remove', 'hover', '')
                # Aplicar hover actual
                app.tra_tree.tk.call(app.tra_tree, 'tag', 'add', 'hover', item)
                # Cambiar cursor
                app.tra_tree.config(cursor='hand2')
        except Exception:
            pass
        return "break"  # Importante: devolver string para Tkinter
    
    def on_tra_leave(event):
        try:
            # Limpiar todos los hovers
            app.tra_tree.tk.call(app.tra_tree, 'tag', 'remove', 'hover', '')
            # Restaurar cursor
            app.tra_tree.config(cursor='')
        except Exception:
            pass
        return "break"  # Importante: devolver string para Tkinter
    
    def on_tra_select(event):
        try:
            selected = app.tra_tree.selection()
            if selected:
                # Limpiar selección previa
                app.tra_tree.tk.call(app.tra_tree, 'tag', 'remove', 'selected', '')
                # Aplicar selección actual
                app.tra_tree.tk.call(app.tra_tree, 'tag', 'add', 'selected', selected[0])
                # Efecto visual: breve parpadeo
                def parpadeo():
                    try:
                        app.tra_tree.tk.call(app.tra_tree, 'tag', 'remove', 'selected', selected[0])
                        app.root.after(150, lambda: app.tra_tree.tk.call(app.tra_tree, 'tag', 'add', 'selected', selected[0]))
                    except Exception:
                        pass
                app.root.after(100, parpadeo)
        except Exception:
            pass
        return "break"  # Importante: devolver string para Tkinter
    
    # Bindings de eventos
    app.tra_tree.bind('<Motion>', on_tra_hover)
    app.tra_tree.bind('<Leave>', on_tra_leave)
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
