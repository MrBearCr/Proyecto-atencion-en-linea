"""
Módulo de configuración de pestaña de Estadísticas
"""
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# -------------------------
# Utilidades internas Stats
# -------------------------

def _stats_build_inverse_maps(app):
    """Construye mapas inversos (cod->desc) para deptos/grupos/subgrupos."""
    inv = {
        'dept': {},
        'group': {},
        'sub': {}
    }
    try:
        # Deptos: {desc->cod} -> {cod->desc}
        for desc, cod in (getattr(app, 'tra_dept_dict', {}) or {}).items():
            if cod: inv['dept'][str(cod)] = str(desc)
        # Grupos: {dept_cod->{desc->cod}} -> {(dept_cod, cod)->desc}
        for dept_cod, groups in (getattr(app, 'tra_group_dict', {}) or {}).items():
            for gdesc, gcod in (groups or {}).items():
                if dept_cod and gcod:
                    inv['group'][(str(dept_cod), str(gcod))] = str(gdesc)
        # Subgrupos: {"dept|group"->{desc->cod}} -> {(dept_cod, group_cod, cod)->desc}
        for key, subs in (getattr(app, 'tra_sub_dict', {}) or {}).items():
            try:
                dept_cod, group_cod = key.split('|', 1)
            except Exception:
                continue
            for sdesc, scod in (subs or {}).items():
                if scod:
                    inv['sub'][(str(dept_cod), str(group_cod), str(scod))] = str(sdesc)
    except Exception:
        pass
    return inv

def _stats_get_current_selection(app):
    """Obtiene la selección jerárquica actual de la pestaña TRA (códigos)."""
    dept_cod = None
    group_cod = None
    sub_cod = None
    try:
        if hasattr(app, 'tra_dept_var') and getattr(app, 'tra_dept_dict', None):
            sel = app.tra_dept_var.get()
            dept_cod = app.tra_dept_dict.get(sel)
        if dept_cod and hasattr(app, 'tra_group_var') and getattr(app, 'tra_group_dict', None):
            gsel = app.tra_group_var.get()
            group_cod = (app.tra_group_dict.get(dept_cod, {}) or {}).get(gsel)
        if dept_cod and group_cod and hasattr(app, 'tra_sub_var') and getattr(app, 'tra_sub_dict', None):
            ssel = app.tra_sub_var.get()
            key = f"{dept_cod}|{group_cod}"
            sub_cod = (app.tra_sub_dict.get(key, {}) or {}).get(ssel)
    except Exception:
        pass
    return (str(dept_cod) if dept_cod else None,
            str(group_cod) if group_cod else None,
            str(sub_cod) if sub_cod else None)

def _stats_filter_records(records, *, dept=None, group=None, sub=None):
    """Filtra registros TRA por jerarquía leyendo índices (2,3,4)."""
    if not records:
        return []
    out = []
    for r in records:
        try:
            dep = str(r[2]) if len(r) > 2 and r[2] is not None else ''
            grp = str(r[3]) if len(r) > 3 and r[3] is not None else ''
            sgb = str(r[4]) if len(r) > 4 and r[4] is not None else ''
            if dept and dep != dept:
                continue
            if group and grp != group:
                continue
            if sub and sgb != sub:
                continue
            out.append(r)
        except Exception:
            continue
    return out

def _stats_aggregate(records, level, *, dept=None, group=None):
    """Agrupa ventas netas por nivel (dept/group/sub)."""
    acc = {}
    if not records:
        return acc
    for r in records:
        try:
            neto = float(r[5] or 0)
        except Exception:
            neto = 0.0
        if level == 'dept':
            key = str(r[2]) if len(r) > 2 and r[2] is not None else None
        elif level == 'group':
            # Solo grupos del dept seleccionado
            if dept is None:
                continue
            if len(r) > 2 and str(r[2]) != str(dept):
                continue
            key = str(r[3]) if len(r) > 3 and r[3] is not None else None
        elif level == 'sub':
            # Solo subgrupos del dept y group seleccionados
            if dept is None or group is None:
                continue
            if not (len(r) > 2 and str(r[2]) == str(dept) and len(r) > 3 and str(r[3]) == str(group)):
                continue
            key = str(r[4]) if len(r) > 4 and r[4] is not None else None
        else:
            key = None
        if not key:
            continue
        acc[key] = acc.get(key, 0.0) + (neto if neto > 0 else 0.0)
    # Remover claves con 0
    return {k: v for k, v in acc.items() if v > 0}

def _stats_format_labels(values_map, *, inv_maps, level, dept=None, group=None):
    """Convierte códigos en etiquetas legibles y arma lista (labels, sizes, meta_codes, legend_rows)."""
    labels = []
    sizes = []
    meta = []  # guardar el código clave para drill-down
    legend_rows = []  # (name, pct_float, value_float)
    total = sum(values_map.values()) or 1.0
    for code, val in sorted(values_map.items(), key=lambda kv: kv[1], reverse=True):
        pct = (val / total) * 100.0
        if level == 'dept':
            name = inv_maps['dept'].get(str(code), str(code))
            label = f"{name}\n{pct:.1f}%"
        elif level == 'group':
            name = inv_maps['group'].get((str(dept), str(code)), str(code))
            label = f"{name}\n{pct:.1f}%"
        else:  # sub
            name = inv_maps['sub'].get((str(dept), str(group), str(code)), str(code))
            label = f"{name}\n{pct:.1f}%"
        labels.append(label)
        sizes.append(val)
        meta.append(str(code))
        legend_rows.append((name, pct, float(val)))
    return labels, sizes, meta, legend_rows

def _stats_clear_container(app):
    for w in app.graph_container.winfo_children():
        try:
            w.destroy()
        except Exception:
            pass

def _stats_update_breadcrumb(app):
    state = getattr(app, 'stats_pie_state', {"level": "dept", "dept": None, "group": None})
    inv = getattr(app, '_stats_inv_maps', _stats_build_inverse_maps(app))
    app._stats_inv_maps = inv
    parts = ["Departamentos"]
    if state.get('dept'):
        dname = inv['dept'].get(str(state['dept']), str(state['dept']))
        parts.append(dname)
    if state.get('group'):
        gname = inv['group'].get((str(state['dept']), str(state['group'])), str(state['group']))
        parts.append(gname)
    app.stats_breadcrumb_var.set(" / ".join(parts))
    # Habilitar/Deshabilitar botón volver
    lvl = state.get('level', 'dept')
    if lvl == 'dept':
        app.stats_btn_back.state(["disabled"]) if hasattr(app, 'stats_btn_back') else None
    else:
        try:
            app.stats_btn_back.state(["!disabled"])  # habilitar
        except Exception:
            pass

def _stats_go_back(app):
    state = getattr(app, 'stats_pie_state', {"level": "dept", "dept": None, "group": None})
    lvl = state.get('level', 'dept')
    if lvl == 'sub':
        state['level'] = 'group'
        state['group'] = None
    elif lvl == 'group':
        state['level'] = 'dept'
        state['dept'] = None
        state['group'] = None
    app.stats_pie_state = state
    app.mostrar_estadisticas()

def _stats_render_pie(app, labels, sizes, title, *, on_pick_codes, legend_rows, colors=None):
    _stats_clear_container(app)

    # Contenedor con dos columnas: gráfico (izquierda) y detalle (derecha)
    container = ttk.Frame(app.graph_container)
    container.pack(fill=tk.BOTH, expand=True)
    left = ttk.Frame(container)
    right = ttk.Frame(container, padding=(8, 0))
    left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    right.pack(side=tk.RIGHT, fill=tk.Y)

    fig, ax = plt.subplots(figsize=(7, 5), dpi=100)
    wedges, texts = ax.pie(
        sizes,
        labels=labels,
        startangle=90,
        autopct=None,
        pctdistance=0.8,
        wedgeprops={"linewidth": 0.8, "edgecolor": "#FFFFFF"},
    )
    ax.axis('equal')
    # Título en esquina superior izquierda con tamaño menor
    ax.text(-1.4, 1.3, title, fontsize=10, ha='left', va='top', weight='bold')

    # Hacer pickeables los wedges con el código asociado
    for w, code in zip(wedges, on_pick_codes):
        try:
            w.set_picker(True)
            w._stats_code = code  # atributo custom
        except Exception:
            pass

    # Canvas en la izquierda
    canvas = FigureCanvasTkAgg(fig, master=left)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Tabla de detalle a la derecha (nombre, %, neto)
    ttk.Label(right, text="Detalle de representación").pack(anchor='w', pady=(0, 4))
    cols = ("Elemento", "%", "Neto")
    tree = ttk.Treeview(right, columns=cols, show='headings', height=12)
    for c in cols:
        tree.heading(c, text=c)
    tree.column("Elemento", width=200, anchor='w')
    tree.column("%", width=60, anchor='e')
    tree.column("Neto", width=90, anchor='e')

    # Rellenar filas en el mismo orden que el gráfico (descendente)
    for idx, (name, pct, val) in enumerate(legend_rows):
        pct_txt = f"{pct:.1f}%"
        try:
            val_disp = int(round(val))
        except Exception:
            val_disp = val
        tree.insert("", tk.END, iid=str(idx), values=(name, pct_txt, val_disp))
    tree.pack(fill=tk.Y, expand=False)

    # Permitir drill-down desde el detalle (doble clic)
    code_by_index = {str(i): on_pick_codes[i] for i in range(len(on_pick_codes))}

    def _on_detail_dblclick(event):
        try:
            sel = tree.selection()
            if not sel:
                return
            idx = sel[0]
            code = code_by_index.get(idx)
            if not code:
                return
            state = getattr(app, 'stats_pie_state', {"level": "dept", "dept": None, "group": None})
            if state.get('level') == 'dept':
                state['level'] = 'group'
                state['dept'] = str(code)
                state['group'] = None
            elif state.get('level') == 'group':
                state['level'] = 'sub'
                state['group'] = str(code)
            app.stats_pie_state = state
            app.mostrar_estadisticas()
        except Exception:
            pass

    tree.bind('<Double-1>', _on_detail_dblclick)

    def _on_pick(event):
        try:
            artist = event.artist
            code = getattr(artist, '_stats_code', None)
            if not code:
                return
            # Actualizar estado y volver a renderizar
            state = getattr(app, 'stats_pie_state', {"level": "dept", "dept": None, "group": None})
            if state.get('level') == 'dept':
                state['level'] = 'group'
                state['dept'] = str(code)
                state['group'] = None
            elif state.get('level') == 'group':
                state['level'] = 'sub'
                state['group'] = str(code)
            app.stats_pie_state = state
            app.mostrar_estadisticas()
        except Exception:
            pass

    canvas.mpl_connect('pick_event', _on_pick)
    return canvas

def _stats_compute_and_draw(app):
    # Validar datos TRA cargados
    ventas = getattr(app, 'cached_ventas_tra', None)
    if not ventas:
        try:
            messagebox.showinfo("Estadísticas", "Primero cargue un reporte en la pestaña RI (TRA)")
        except Exception:
            pass
        _stats_clear_container(app)
        lbl = ttk.Label(app.graph_container, text="Sin datos para graficar. Cargue RI y presione 'Actualizar Gráficos'.")
        lbl.pack(pady=20)
        return

    # Estado inicial según filtros actuales de TRA
    if not hasattr(app, 'stats_pie_state') or not app.stats_pie_state:
        dept, group, sub = _stats_get_current_selection(app)
        if sub:
            app.stats_pie_state = {"level": "sub", "dept": dept, "group": group}
        elif group:
            app.stats_pie_state = {"level": "group", "dept": dept, "group": group}
        elif dept:
            app.stats_pie_state = {"level": "group", "dept": dept, "group": None}
        else:
            app.stats_pie_state = {"level": "dept", "dept": None, "group": None}

    state = app.stats_pie_state
    inv = getattr(app, '_stats_inv_maps', _stats_build_inverse_maps(app))
    app._stats_inv_maps = inv

    # Aplicar exclusiones de departamentos (global)
    try:
        excluded = set(str(x) for x in (getattr(app, 'excluded_depts', []) or []))
    except Exception:
        excluded = set()
    # Preferir dataset ya filtrado si existe
    try:
        ventas_effective = getattr(app, 'cached_ventas_tra_effective', None)
        if ventas_effective is not None:
            ventas = ventas_effective
    except Exception:
        pass
    if excluded:
        ventas = [r for r in ventas if len(r) > 2 and str(r[2]) not in excluded]

    # Determinar nivel y agregar datos
    if state['level'] == 'dept':
        # Agregar por departamento en todos los datos (sin filtrar por dept)
        data_map = _stats_aggregate(ventas, 'dept')
        if not data_map:
            _stats_clear_container(app)
            ttk.Label(app.graph_container, text="No hay ventas por departamento para mostrar").pack(pady=10)
            return
        labels, sizes, meta, legend = _stats_format_labels(data_map, inv_maps=inv, level='dept')
        title = "Representación por Departamento (RI)"
        _stats_update_breadcrumb(app)
        _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        return
    elif state['level'] == 'group':
        dept = state.get('dept')
        # Filtrar por dept y agregar grupos
        data_map = _stats_aggregate(ventas, 'group', dept=dept)
        if not data_map:
            _stats_clear_container(app)
            name = inv['dept'].get(str(dept), str(dept)) if dept else 'N/A'
            ttk.Label(app.graph_container, text=f"Sin datos de grupos para {name}").pack(pady=10)
            return
        labels, sizes, meta, legend = _stats_format_labels(data_map, inv_maps=inv, level='group', dept=dept)
        name = inv['dept'].get(str(dept), str(dept)) if dept else ''
        title = f"{name} — Representación por Grupo"
        _stats_update_breadcrumb(app)
        _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        return
    else:  # sub
        dept = state.get('dept')
        group = state.get('group')
        data_map = _stats_aggregate(ventas, 'sub', dept=dept, group=group)
        if not data_map:
            _stats_clear_container(app)
            dname = inv['dept'].get(str(dept), str(dept)) if dept else 'N/A'
            gname = inv['group'].get((str(dept), str(group)), str(group)) if group else 'N/A'
            ttk.Label(app.graph_container, text=f"Sin datos de subgrupos para {dname} / {gname}").pack(pady=10)
            return
        labels, sizes, meta, legend = _stats_format_labels(data_map, inv_maps=inv, level='sub', dept=dept, group=group)
        dname = inv['dept'].get(str(dept), str(dept)) if dept else ''
        gname = inv['group'].get((str(dept), str(group)), str(group)) if group else ''
        title = f"{dname} → {gname} — Representación por Subgrupo"
        _stats_update_breadcrumb(app)
        _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        return

def setup_stats_tab(app):
    """Configura la pestaña de Estadísticas en la aplicación"""
    app.stats_frame = ttk.Frame(app.stats_tab)
    app.stats_frame.pack(fill=tk.BOTH, expand=True)

    # Barra superior con acciones y breadcrumb
    top_bar = ttk.Frame(app.stats_frame)
    top_bar.pack(fill=tk.X, pady=(8, 4))

    app.stats_btn_back = ttk.Button(top_bar, text="◄ Volver", command=lambda: _stats_go_back(app))
    try:
        app.stats_btn_back.state(["disabled"])  # deshabilitado al inicio
    except Exception:
        pass
    app.stats_btn_back.pack(side=tk.LEFT)

    app.stats_breadcrumb_var = tk.StringVar(value="Departamentos")
    ttk.Label(top_bar, textvariable=app.stats_breadcrumb_var).pack(side=tk.LEFT, padx=10)

    ttk.Button(
        top_bar,
        text="Actualizar Gráficos",
        command=lambda: getattr(app, 'mostrar_estadisticas', lambda: None)()
    ).pack(side=tk.RIGHT)

    # Contenedor para gráficos
    app.graph_container = ttk.Frame(app.stats_frame)
    app.graph_container.pack(fill=tk.BOTH, expand=True)

    # Expone función pública en app
    def _mostrar_estadisticas_public():
        """Renderiza el gráfico adecuado según la selección actual del módulo RI (TRA)."""
        try:
            _stats_compute_and_draw(app)
        except Exception as e:
            try:
                app.log(f"Error mostrando estadísticas: {e}", "ERROR")
            except Exception:
                pass
    app.mostrar_estadisticas = _mostrar_estadisticas_public
