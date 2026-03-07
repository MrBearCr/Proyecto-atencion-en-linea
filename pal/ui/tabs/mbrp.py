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
    rango_combo['values'] = ["7 días", "15 días", "30 días", "60 días", "90 días", "120 días", "365 días", "Personalizado"]
    rango_combo.pack(side=tk.LEFT, padx=5)
    
    ttk.Label(fecha_frame, text="Desde:").pack(side=tk.LEFT, padx=(10,0))
    # Configurar fecha máxima: ayer (las ventas no se cargan hasta el cierre)
    ayer = datetime.now() - timedelta(days=1)
    # Ampliar rango para permitir análisis histórico prolongado (10 años de respaldo)
    hace_10_anos = ayer - timedelta(days=3650)
    
    app.mbrp_fecha_inicio_entry = DateEntry(fecha_frame, width=12, date_pattern='yyyy-mm-dd',
                                           mindate=hace_10_anos, maxdate=ayer)
    app.mbrp_fecha_inicio_entry.set_date(ayer - timedelta(days=30))  # Default: últimos 30 días
    app.mbrp_fecha_inicio_entry.pack(side=tk.LEFT, padx=5)

    ttk.Label(fecha_frame, text="Hasta:").pack(side=tk.LEFT)
    app.mbrp_fecha_fin_entry = DateEntry(fecha_frame, width=12, date_pattern='yyyy-mm-dd',
                                        mindate=hace_10_anos, maxdate=ayer)
    app.mbrp_fecha_fin_entry.set_date(ayer)  # Default: hasta ayer
    app.mbrp_fecha_fin_entry.pack(side=tk.LEFT, padx=5)

    ttk.Label(fecha_frame, text="Sede:").pack(side=tk.LEFT, padx=10)
    app.mbrp_sede_var = tk.StringVar()
    app.mbrp_sede_combo = ttk.Combobox(fecha_frame, textvariable=app.mbrp_sede_var, state='readonly', width=18)
    app.mbrp_sede_combo['values'] = ["00 - ICH", "0301 - Cabudare", "0401 - Guanare", "0101 - Barinas"]
    app.mbrp_sede_combo.current(0)
    app.mbrp_sede_combo.pack(side=tk.LEFT)

    # Aviso al seleccionar ICH (consulta global)
    def _on_mbrp_sede_selected(event=None):
        try:
            sel = (app.mbrp_sede_var.get() or '')
            if sel.startswith('00'):
                import tkinter as _tk
                banner = _tk.Toplevel(app.root)
                banner.overrideredirect(True)
                banner.attributes("-topmost", True)
                banner.configure(bg="#FFB81C")
                app.root.update_idletasks()
                rx, ry, rw = app.root.winfo_x(), app.root.winfo_y(), app.root.winfo_width()
                bw = 420
                banner.geometry(f"{bw}x60+{rx + (rw - bw)//2}+{ry + 10}")
                _tk.Label(
                    banner,
                    text="⚠️  Filtro ICH (MBRP) — Consulta global seleccionada.\nPuede tardar más en procesar.",
                    bg="#FFB81C", fg="black",
                    font=("Segoe UI", 9, "bold"),
                    justify="center", pady=8
                ).pack(expand=True, fill=_tk.BOTH)
                banner.after(4500, banner.destroy)
        except Exception:
            pass
    app.mbrp_sede_combo.bind('<<ComboboxSelected>>', _on_mbrp_sede_selected)

    # Botones de acción
    ttk.Button(top_controls, text="Cargar", command=app.cargar_mbrp_base).pack(side=tk.RIGHT, padx=10)
    ttk.Button(top_controls, text="🔄 Actualizar Ventas", 
               command=lambda: getattr(app, 'actualizar_ultimas_ventas_mbrp', lambda: None)()).pack(side=tk.RIGHT, padx=5)
    
    # Permisos para exportar y ver ventas en dólares
    can_export_mbrp = False
    can_view_dollars_mbrp = False
    try:
        if hasattr(app, 'permissions') and app.current_user:
            can_export_mbrp = app.permissions.tiene_permiso(app.current_user['id'], 'MBRP', 'exportar')
            can_view_dollars_mbrp = app.permissions.tiene_permiso(app.current_user['id'], 'MBRP', 'ver_ventas_dolares')
        if app.current_user and app.current_user.get('username','').lower() == 'admin':
            can_export_mbrp = True
            can_view_dollars_mbrp = True
    except Exception:
        can_export_mbrp = False
        can_view_dollars_mbrp = False
    btn_export_mbrp = ttk.Button(top_controls, text="📈 Exportar Excel", 
               command=lambda: getattr(app, 'exportar_mbrp_excel', lambda: None)())
    btn_export_mbrp.pack(side=tk.RIGHT, padx=5)
    if not can_export_mbrp:
        try:
            btn_export_mbrp.state(["disabled"])  # ttk style
        except Exception:
            btn_export_mbrp.config(state='disabled')

    ttk.Button(top_controls, text="📊 Reporte 0", command=app.generar_reporte_mbrp).pack(side=tk.RIGHT, padx=5)
    
    # Checkbox para cambiar entre unidades y dólares en ventas (protegido por permiso)
    app.mbrp_mostrar_dolares_var = tk.BooleanVar(value=False)
    mbrp_dolares_check = ttk.Checkbutton(
        top_controls, 
        text="Ventas en $", 
        variable=app.mbrp_mostrar_dolares_var,
        command=lambda: app.actualizar_display_ventas_mbrp()
    )
    mbrp_dolares_check.pack(side=tk.RIGHT, padx=5)
    if not can_view_dollars_mbrp:
        try:
            mbrp_dolares_check.state(["disabled"])
        except Exception:
            mbrp_dolares_check.config(state='disabled')

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

    # Filtro por Proveedores
    ttk.Label(filter_frame, text="Proveedores:").pack(side=tk.LEFT, padx=(15, 5))
    ttk.Button(
        filter_frame,
        text="🔍",
        width=3,
        command=lambda: getattr(app, 'abrir_selector_proveedor_mbrp', lambda: None)(),
    ).pack(side=tk.LEFT, padx=5)

    # Etiqueta para mostrar proveedor seleccionado (feedback visual)
    app.mbrp_proveedor_label_var = tk.StringVar(value="")
    app.mbrp_proveedor_label = ttk.Label(
        filter_frame,
        textvariable=app.mbrp_proveedor_label_var,
        foreground="#555555",
    )
    # No la mostramos hasta que haya proveedor seleccionado (para no ver un recuadro vacío)

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

    columns = ("Código", "Descripción", "Rotación", "Ventas", "Stock Actual", "Días de Stock", "IM %", "Última Venta")
    app.mbrp_tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=10)
    
    # Configurar columna ID (árbol) para expandir proveedores
    app.mbrp_tree.column("#0", width=30, stretch=tk.NO)
    
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
        "Ventas": {"width": 100, "anchor": "center"},
        "Stock Actual": {"width": 90, "anchor": "center"},
        "Días de Stock": {"width": 90, "anchor": "center"},
        "IM %": {"width": 80, "anchor": "center"},
        "Última Venta": {"width": 110, "anchor": "center"},
    }

    for col in columns:
        # Usar encabezado dinámico para la columna Ventas
        header_text = col
        if col == "Ventas" and hasattr(app, 'mbrp_mostrar_dolares_var') and app.mbrp_mostrar_dolares_var.get():
            header_text = "Ventas ($)"
        app.mbrp_tree.heading(col, text=header_text)
        app.mbrp_tree.column(col, **column_config.get(col, {"width": 120, "anchor": "center"}))

    # Colores para MBRP - resaltar productos de BAJA movilidad con filas alternadas
    app.mbrp_tree.tag_configure('baja', background='#607D8B', foreground='#FFFFFF', font=('', 11))  # Gris azulado (Anteriormente ALTA)
    app.mbrp_tree.tag_configure('baja-moderada', background='#FF9800', foreground='#FFFFFF', font=('', 11))  # Naranja (Anteriormente MEDIA)
    app.mbrp_tree.tag_configure('critico', background='#D32F2F', foreground='#FFFFFF', font=('', 11, 'bold'))  # Rojo (Anteriormente BAJA/SIN_MOVIMIENTO)
    app.mbrp_tree.tag_configure('sin_clasificar', background='#9C27B0', foreground='#FFFFFF', font=('', 11))  # Púrpura vibrante
    app.mbrp_tree.tag_configure('loading', background='#2196F3', foreground='#FFFFFF', font=('', 12, 'italic'))  # Azul vibrante
    
    # Estilos alternados para mejor distinción de filas
    app.mbrp_tree.tag_configure('baja_alt', background='#546E7A', foreground='#FFFFFF', font=('', 11))
    app.mbrp_tree.tag_configure('baja-moderada_alt', background='#F57C00', foreground='#FFFFFF', font=('', 11))
    app.mbrp_tree.tag_configure('critico_alt', background='#B71C1C', foreground='#FFFFFF', font=('', 11, 'bold'))
    app.mbrp_tree.tag_configure('sin_clasificar_alt', background='#7B1FA2', foreground='#FFFFFF', font=('', 11))  # Púrpura más oscuro
    
    # Colores adicionales por Índice de Movilidad
    app.mbrp_tree.tag_configure('im_critico', background='#B71C1C', foreground='#FFFFFF', font=('', 11, 'bold'))  # IM < 5% - Rojo muy vibrante
    app.mbrp_tree.tag_configure('im_muy_bajo', background='#D32F2F', foreground='#FFFFFF', font=('', 11, 'bold'))  # IM 5-10% - Rojo vibrante
    app.mbrp_tree.tag_configure('im_bajo', background='#FF5722', foreground='#FFFFFF', font=('', 11))  # IM 10-20% - Naranja rojizo vibrante
    
    # Colores alternados para IM
    app.mbrp_tree.tag_configure('im_critico_alt', background='#9A0007', foreground='#FFFFFF', font=('', 11, 'bold'))  # IM crítico más oscuro
    app.mbrp_tree.tag_configure('im_muy_bajo_alt', background='#B71C1C', foreground='#FFFFFF', font=('', 11, 'bold'))  # IM muy bajo más oscuro
    app.mbrp_tree.tag_configure('im_bajo_alt', background='#E64A19', foreground='#FFFFFF', font=('', 11))  # IM bajo más oscuro
    
    # Configurar colores de selección en el style para que funcione correctamente
    style.map('LargeMBRP.Treeview',
        background=[('selected', '#0D47A1')],  # Azul oscuro para selección
        foreground=[('selected', '#FFFFFF')]   # Texto blanco para contraste
    )
    
    # Variable para rastrear el ítem actualmente seleccionado
    app.mbrp_current_selected_item = None

    # Eventos de selección mejorados
    def on_mbrp_click(event):
        """Maneja el click en una fila del treeview"""
        try:
            region = app.mbrp_tree.identify_region(event.x, event.y)
            if region == 'cell' or region == 'tree':
                item = app.mbrp_tree.identify_row(event.y)
                if item:
                    # Seleccionar el item
                    app.mbrp_tree.selection_set(item)
                    app.mbrp_tree.focus(item)
                    app.mbrp_current_selected_item = item
                    # Asegurar que sea visible
                    app.mbrp_tree.see(item)
                    # Actualizar info ICH (última venta / stock por sede) si está disponible
                    if hasattr(app, '_update_mbrp_ich_info'):
                        app._update_mbrp_ich_info()
        except Exception:
            pass
    
    def on_mbrp_select(event):
        """Maneja el evento de selección del treeview"""
        try:
            selected = app.mbrp_tree.selection()
            if selected:
                app.mbrp_current_selected_item = selected[0]
                # Actualizar info ICH al cambiar selección
                if hasattr(app, '_update_mbrp_ich_info'):
                    app._update_mbrp_ich_info()
        except Exception:
            pass
    
    # Bindings de eventos
    app.mbrp_tree.bind('<Button-1>', on_mbrp_click)
    app.mbrp_tree.bind('<Button-3>', lambda e: getattr(app, 'mostrar_context_menu_mbrp', lambda ev: None)(e))
    app.mbrp_tree.bind('<<TreeviewSelect>>', on_mbrp_select)
    
    # Layout
    app.mbrp_tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    # Información adicional para modo ICH (global): última venta y stock por sede
    app.mbrp_ich_info_var = tk.StringVar(value="")
    app.mbrp_ich_info_label = ttk.Label(
        app.mbrp_tab_frame,
        textvariable=app.mbrp_ich_info_var,
        foreground="#555555",
        wraplength=900,
        justify='left',
    )
    app.mbrp_ich_info_label.pack(fill=tk.X, pady=(4, 0))

    # Inicializar diccionarios vacíos SOLO si no existen aún
    # NOTA: La jerarquía se carga en create_main_workspace() ANTES de crear esta pestaña
    # No volver a cargar aquí para evitar duplicados y conflictos de hilo
    if not hasattr(app, 'mbrp_dept_dict') or not app.mbrp_dept_dict:
        app.mbrp_dept_dict = {}
    if not hasattr(app, 'mbrp_group_dict') or not app.mbrp_group_dict:
        app.mbrp_group_dict = {}
    if not hasattr(app, 'mbrp_sub_dict') or not app.mbrp_sub_dict:
        app.mbrp_sub_dict = {}
    
    # Actualizar combo con datos existentes o inicializar con 'Todos'
    if app.mbrp_dept_dict:
        app.mbrp_dept_combo['values'] = ['Todos'] + list(app.mbrp_dept_dict.keys())
    else:
        app.mbrp_dept_combo['values'] = ['Todos']
    app.mbrp_dept_var.set('Todos')

    # Bindings de filtros (idénticos a TRA, pero con prefijo mbrp_)
    def _on_mbrp_dept_selected(event=None):
        desc = app.mbrp_dept_var.get()
        dept_cod = app.mbrp_dept_dict.get(desc)
        
        # Resetear combos de grupo y subgrupo
        app.mbrp_group_combo['values'] = ['Todos']
        app.mbrp_group_var.set('Todos')
        app.mbrp_sub_combo['values'] = ['Todos']
        app.mbrp_sub_var.set('Todos')
        
        # Si no hay departamento seleccionado o es 'Todos', no cargar grupos
        if not dept_cod or desc == 'Todos':
            if hasattr(app, 'aplicar_filtro_mbrp'):
                app.aplicar_filtro_mbrp()
            return
        
        # Cargar grupos del departamento seleccionado
        if hasattr(app.db_manager, 'conn') and app.db_manager.conn:
            try:
                grupos = app.db_manager.fetch_data(
                    "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_GRUPOS WHERE C_DEPARTAMENTO = ?",
                    (dept_cod,)
                )
                # Usar estructura anidada como TRA: mbrp_group_dict[dept_cod][desc] = cod
                if dept_cod not in app.mbrp_group_dict:
                    app.mbrp_group_dict[dept_cod] = {}
                app.mbrp_group_dict[dept_cod] = {desc: cod for cod, desc in grupos if cod and desc}
                app.mbrp_group_combo['values'] = ['Todos'] + list(app.mbrp_group_dict[dept_cod].keys())
            except Exception as e:
                app.log(f"Error cargando grupos MBRP: {e}", "ERROR")
                if dept_cod not in app.mbrp_group_dict:
                    app.mbrp_group_dict[dept_cod] = {}
        
        if hasattr(app, 'aplicar_filtro_mbrp'):
            app.aplicar_filtro_mbrp()

    def _on_mbrp_group_selected(event=None):
        dept_desc = app.mbrp_dept_var.get()
        dept_cod = app.mbrp_dept_dict.get(dept_desc)
        group_desc = app.mbrp_group_var.get()
        
        # Resetear combo de subgrupos
        app.mbrp_sub_combo['values'] = ['Todos']
        app.mbrp_sub_var.set('Todos')
        
        # Si no hay dept o group, o es 'Todos', no cargar subgrupos
        if not dept_cod or not group_desc or group_desc == 'Todos':
            if hasattr(app, 'aplicar_filtro_mbrp'):
                app.aplicar_filtro_mbrp()
            return
        
        # Obtener código de grupo desde estructura anidada
        group_cod = app.mbrp_group_dict.get(dept_cod, {}).get(group_desc)
        
        if not group_cod:
            if hasattr(app, 'aplicar_filtro_mbrp'):
                app.aplicar_filtro_mbrp()
            return
        
        # Cargar subgrupos
        if hasattr(app.db_manager, 'conn') and app.db_manager.conn:
            try:
                subs = app.db_manager.fetch_data(
                    "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_SUBGRUPOS WHERE C_IN_DEPARTAMENTO = ? AND C_IN_GRUPO = ?",
                    (dept_cod, group_cod)
                )
                # Usar key compuesta como TRA: "dept|group"
                key = f"{dept_cod}|{group_cod}"
                app.mbrp_sub_dict[key] = {desc: cod for cod, desc in subs if cod and desc}
                app.mbrp_sub_combo['values'] = ['Todos'] + list(app.mbrp_sub_dict[key].keys())
            except Exception as e:
                app.log(f"Error cargando subgrupos MBRP: {e}", "ERROR")
        
        if hasattr(app, 'aplicar_filtro_mbrp'):
            app.aplicar_filtro_mbrp()

    def _on_mbrp_sub_selected(event=None):
        if hasattr(app, 'aplicar_filtro_mbrp'):
            app.aplicar_filtro_mbrp()

    # Funcionalidad del combobox de rango
    def _on_mbrp_rango_selected(event=None):
        rango = app.mbrp_rango_var.get()
        ayer = datetime.now() - timedelta(days=1)
        hace_10_anos = ayer - timedelta(days=3650)
        
        if rango == "Personalizado":
            # Mostrar mensaje informativo sobre el rango permitido
            try:
                app.log(f"Rango personalizado seleccionado. Fechas permitidas: {hace_10_anos.strftime('%Y-%m-%d')} a {ayer.strftime('%Y-%m-%d')}", "INFO")
            except Exception:
                pass
            return
        
        # Extraer número de días
        try:
            dias = int(rango.split()[0])
            fecha_inicio = ayer - timedelta(days=dias-1)  # -1 porque incluimos el día actual
        except (ValueError, IndexError):
            return
        
        # Asegurar que la fecha no exceda el límite mínimo
        if fecha_inicio < hace_10_anos:
            fecha_inicio = hace_10_anos
            try:
                app.log(f"Fecha inicio ajustada al límite histórico: {hace_10_anos.strftime('%Y-%m-%d')}", "WARNING")
            except Exception:
                pass
        
        app.mbrp_fecha_inicio_entry.set_date(fecha_inicio)
        app.mbrp_fecha_fin_entry.set_date(ayer)
        _check_mbrp_wide_range()

    def _show_mbrp_wide_range_warning():
        """Muestra banner de advertencia para rangos muy amplios"""
        try:
            import tkinter as _tk
            banner = _tk.Toplevel(app.root)
            banner.overrideredirect(True)
            banner.attributes("-topmost", True)
            banner.configure(bg="#F44336") # Rojo para mayor visibilidad en rangos históricos
            app.root.update_idletasks()
            rx, ry, rw = app.root.winfo_x(), app.root.winfo_y(), app.root.winfo_width()
            bw = 500
            banner.geometry(f"{bw}x60+{rx + (rw - bw)//2}+{ry + 10}")
            _tk.Label(
                banner,
                text="⚠️  Rango amplio detectado (+1 año) — La consulta y el cálculo\npueden tardar considerablemente en terminar.",
                bg="#F44336", fg="white",
                font=("Segoe UI", 9, "bold"),
                justify="center", pady=8
            ).pack(expand=True, fill=_tk.BOTH)
            banner.after(5500, banner.destroy)
        except Exception:
            pass

    def _check_mbrp_wide_range(event=None):
        """Verifica si el rango es > 365 días y muestra aviso"""
        try:
            f1 = app.mbrp_fecha_inicio_entry.get_date()
            f2 = app.mbrp_fecha_fin_entry.get_date()
            if (f2 - f1).days > 365:
                # Evitar mostrar múltiples banners si ya hay uno
                _show_mbrp_wide_range_warning()
        except Exception:
            pass

    # Vincular cambios de fecha manuales al aviso de rango
    app.mbrp_fecha_inicio_entry.bind('<<DateEntrySelected>>', _check_mbrp_wide_range)
    app.mbrp_fecha_fin_entry.bind('<<DateEntrySelected>>', _check_mbrp_wide_range)
    
    # Función para verificar y recargar filtros MBRP si están vacíos
    # Esta se ejecuta al hacer clic en el dropdown para intentar rellenarlo
    def _verificar_y_recargar_filtros_mbrp(event=None):
        """Verifica si los filtros MBRP están vacíos y los recarga automáticamente"""
        # SOLO rellenar la jerar quía, NO cargar datos
        if len(app.mbrp_dept_combo['values']) <= 1:  # Solo tiene 'Todos'
            try:
                # Intentar actualizar solo los combos de jerar quía desde datos ya cargados
                if hasattr(app, '_update_hierarchy_combos'):
                    app._update_hierarchy_combos()
                
                # Si TODAVIA están vacíos, logear advertencia pero NO cargar datos
                if len(app.mbrp_dept_combo['values']) <= 1:
                    app.log("[MBRP] Filtros vacíos. Presione 'Cargar' para obtener datos.", "WARNING")
            except Exception as e:
                app.log(f"Error actualizando filtros MBRP: {e}", "ERROR")
    
    # Eventos con verificación automática
    app.mbrp_dept_combo.bind('<Button-1>', _verificar_y_recargar_filtros_mbrp)  # Antes de abrir
    rango_combo.bind('<<ComboboxSelected>>', _on_mbrp_rango_selected)
    app.mbrp_dept_combo.bind('<<ComboboxSelected>>', _on_mbrp_dept_selected)
    app.mbrp_group_combo.bind('<<ComboboxSelected>>', _on_mbrp_group_selected)
    app.mbrp_sub_combo.bind('<<ComboboxSelected>>', _on_mbrp_sub_selected)
