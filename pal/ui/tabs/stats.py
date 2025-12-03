"""
Módulo de configuración de pestaña de Estadísticas
"""
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
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
    """Actualiza el breadcrumb teniendo en cuenta el proveedor seleccionado y la jerarquía."""
    state = getattr(app, 'stats_pie_state', {"level": "dept", "dept": None, "group": None, "sub": None})
    inv = getattr(app, '_stats_inv_maps', _stats_build_inverse_maps(app))
    app._stats_inv_maps = inv

    parts = []

    # Si hay proveedor activo en TRA, mostrarlo siempre como raíz del breadcrumb
    try:
        prov_cod = getattr(app, 'tra_proveedor_codigo', None)
        prov_desc = getattr(app, 'tra_proveedor_descripcion', None)
    except Exception:
        prov_cod = None
        prov_desc = None

    if prov_cod:
        parts.append(f"Proveedor: {prov_desc or prov_cod}")
    else:
        # Sin proveedor: raíz genérica
        parts.append("Todos los proveedores")

    # Nivel jerárquico interno (Depto/Grupo/Sub)
    if state.get('dept'):
        dname = inv['dept'].get(str(state['dept']), str(state['dept']))
        parts.append(dname)
    if state.get('group'):
        gname = inv['group'].get((str(state['dept']), str(state['group'])), str(state['group']))
        parts.append(gname)
    if state.get('sub'):
        sname = inv['sub'].get(
            (str(state.get('dept')), str(state.get('group')), str(state.get('sub'))),
            str(state.get('sub')),
        )
        parts.append(sname)

    app.stats_breadcrumb_var.set(" / ".join(parts))

# Habilitar/Deshabilitar botón volver
    lvl = state.get('level', 'dept')
    if lvl == 'dept':
        # En raíz de jerarquía interna no hay nada a donde volver
        app.stats_btn_back.state(["disabled"]) if hasattr(app, 'stats_btn_back') else None
    else:
        try:
            app.stats_btn_back.state(["!disabled"])  # habilitar
        except Exception:
            pass

def _stats_go_back(app):
    state = getattr(app, 'stats_pie_state', {"level": "dept", "dept": None, "group": None})
    lvl = state.get('level', 'dept')
    if lvl == 'product':
        state['level'] = 'sub'
        state['sub'] = None
    elif lvl == 'sub':
        state['level'] = 'group'
        state['group'] = None
    elif lvl == 'group':
        state['level'] = 'dept'
        state['dept'] = None
        state['group'] = None
    app.stats_pie_state = state
    app.mostrar_estadisticas()

def _stats_render_pie(app, labels, sizes, title, *, on_pick_codes, legend_rows, colors=None, hover_meta=None):
    """Renderiza gráfico de pastel + tabla detalle.

    Las etiquetas de cada segmento se muestran siempre; la tabla lateral
    complementa la lectura cuando hay muchos segmentos pequeños.
    """
    _stats_clear_container(app)

    # Contenedor con dos columnas: gráfico (izquierda) y detalle (derecha)
    container = ttk.Frame(app.graph_container)
    container.pack(fill=tk.BOTH, expand=True)
    left = ttk.Frame(container)
    # Panel derecho con ancho fijo para que el layout no cambie aunque el texto aparezca/desaparezca
    right = ttk.Frame(container, padding=(8, 0), width=260)
    left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    right.pack(side=tk.RIGHT, fill=tk.Y)
    # Evitar que el frame se redimensione según su contenido
    right.pack_propagate(False)

    fig = Figure(figsize=(7, 5), dpi=100)
    ax = fig.add_subplot(111)
    # Tooltip para mostrar datos completos al pasar el mouse (solo se usa si hover_meta no es None)
    tooltip = ax.annotate(
        "",
        # Mostrar el tooltip debajo del área del gráfico, centrado
        xy=(0.5, -0.12),
        xycoords="axes fraction",
        ha="center",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", fc="w", ec="#333333", alpha=0.9),
    )
    tooltip.set_visible(False)

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

    # Panel derecho: solo label con información extendida del ítem (sin Treeview de detalle)
    hover_label_var = None
    try:
        if hover_meta:
            # Destruir label anterior si existe
            old_label = getattr(app, 'stats_hover_detail_label', None)
            if old_label is not None:
                try:
                    old_label.destroy()
                except Exception:
                    pass
            if not hasattr(app, 'stats_hover_detail_var'):
                app.stats_hover_detail_var = tk.StringVar(value="")
            else:
                app.stats_hover_detail_var.set("")
            hover_label_var = app.stats_hover_detail_var
            app.stats_hover_detail_label = ttk.Label(
                right,
                textvariable=hover_label_var,
                wraplength=260,
                justify='left',
            )
            app.stats_hover_detail_label.pack(anchor='w', pady=(6, 0))
    except Exception:
        hover_label_var = None

    def _on_pick(event):
        try:
            artist = event.artist
            code = getattr(artist, '_stats_code', None)
            if not code:
                return
            # Actualizar estado y volver a renderizar
            state = getattr(app, 'stats_pie_state', {"level": "dept", "dept": None, "group": None, "sub": None})
            lvl = state.get('level', 'dept')

            if lvl == 'provider':
                # Nivel raíz: proveedor vs resto
                if str(code).upper() == 'PROV':
                    state['level'] = 'dept'
                    state['subset'] = 'provider'
                elif str(code).upper() == 'REST':
                    state['level'] = 'dept'
                    state['subset'] = 'rest'
            elif lvl == 'dept':
                state['level'] = 'group'
                state['dept'] = str(code)
                state['group'] = None
                state.setdefault('sub', None)
            elif lvl == 'group':
                state['level'] = 'sub'
                state['group'] = str(code)
                state.setdefault('sub', None)
            elif lvl == 'sub':
                state['level'] = 'product'
                state['sub'] = str(code)

            app.stats_pie_state = state
            app.mostrar_estadisticas()
        except Exception:
            pass

    canvas.mpl_connect('pick_event', _on_pick)

    # Mostrar tooltip al pasar el mouse por encima de un segmento (solo si tenemos meta de productos)
    def _on_motion(event):
        try:
            if not hover_meta or hover_label_var is None:
                return
            if event.inaxes is not ax:
                hover_label_var.set("")
                return
            found = False
            for w, code in zip(wedges, on_pick_codes):
                if w.contains_point((event.x, event.y)):
                    info = hover_meta.get(str(code)) or hover_meta.get(code)
                    if not info:
                        continue
                    nombre = str(info.get('full_name', code))
                    cod = str(info.get('code', code))
                    ventas = info.get('ventas', 0)
                    pct = info.get('pct', 0.0)
                    try:
                        ventas_txt = f"{int(round(ventas))}"
                    except Exception:
                        ventas_txt = str(ventas)
                    hover_label_var.set(f"{nombre}\nCod: {cod}  •  Ventas: {ventas_txt}  •  {pct:.1f}%")
                    found = True
                    break
            if not found:
                hover_label_var.set("")
        except Exception:
            pass

    canvas.mpl_connect('motion_notify_event', _on_motion)
    return canvas


def _stats_render_bar(app, labels, sizes, title, *, on_pick_codes, legend_rows, hover_meta=None):
    """Renderiza gráfico de barras horizontales descendente + tabla detalle.

    Las barras se ordenan de mayor a menor valor, mostrando el nombre
    a la izquierda y el valor / porcentaje al final de cada barra.
    """
    _stats_clear_container(app)

    container = ttk.Frame(app.graph_container)
    container.pack(fill=tk.BOTH, expand=True)
    left = ttk.Frame(container)
    # Panel derecho con ancho fijo para que el layout no cambie aunque el texto aparezca/desaparezca
    right = ttk.Frame(container, padding=(8, 0), width=260)
    left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    right.pack(side=tk.RIGHT, fill=tk.Y)
    right.pack_propagate(False)

    # Usar legend_rows ya viene ordenado de forma descendente
    names = [row[0] for row in legend_rows]
    pcts = [row[1] for row in legend_rows]
    vals = [row[2] for row in legend_rows]

    fig = Figure(figsize=(7, 5), dpi=100)
    ax = fig.add_subplot(111)
    # Tooltip para productos al pasar el mouse por encima de una barra
    tooltip = ax.annotate(
        "",
        # Mostrar el tooltip debajo del área del gráfico de barras, centrado
        xy=(0.5, -0.16),
        xycoords="axes fraction",
        ha="center",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", fc="w", ec="#333333", alpha=0.9),
    )
    tooltip.set_visible(False)
    y_pos = list(range(len(vals)))

    bars = ax.barh(y_pos, vals, align='center', color='#4C72B0')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names)
    ax.invert_yaxis()  # mayor valor arriba
    ax.set_xlabel('Ventas netas')
    ax.set_title(title)

    # Hacer cada barra seleccionable para drill-down
    for bar, code in zip(bars, on_pick_codes):
        try:
            bar.set_picker(True)
            bar._stats_code = code
        except Exception:
            pass

    # Reducir tamaño de fuente de etiquetas del eje Y para mejorar legibilidad
    ax.tick_params(axis='y', labelsize=8)

    # Etiquetas de valor y % al final de cada barra
    total = sum(vals) or 1.0
    for i, (v, pct) in enumerate(zip(vals, pcts)):
        try:
            x = v
            pct_txt = f"{pct:.1f}%"
            val_disp = int(round(v))
            ax.text(x, i, f" {val_disp} ({pct_txt})", va='center', ha='left', fontsize=8)
        except Exception:
            continue

    canvas = FigureCanvasTkAgg(fig, master=left)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Manejar clic en barras para drill-down (igual lógica que detalle)
    def _on_pick(event):
        try:
            artist = event.artist
            code = getattr(artist, '_stats_code', None)
            if not code:
                return
            state = getattr(app, 'stats_pie_state', {"level": "dept", "dept": None, "group": None, "sub": None})
            lvl = state.get('level', 'dept')

            if lvl == 'provider':
                if str(code).upper() == 'PROV':
                    state['level'] = 'dept'
                    state['subset'] = 'provider'
                elif str(code).upper() == 'REST':
                    state['level'] = 'dept'
                    state['subset'] = 'rest'
            elif lvl == 'dept':
                state['level'] = 'group'
                state['dept'] = str(code)
                state['group'] = None
                state.setdefault('sub', None)
            elif lvl == 'group':
                state['level'] = 'sub'
                state['group'] = str(code)
                state.setdefault('sub', None)
            elif lvl == 'sub':
                state['level'] = 'product'
                state['sub'] = str(code)
            app.stats_pie_state = state
            app.mostrar_estadisticas()
        except Exception:
            pass

    canvas.mpl_connect('pick_event', _on_pick)

    # Tooltip en movimiento sobre barras
    def _on_motion(event):
        try:
            if not hover_meta or hover_label_var is None:
                return
            if event.inaxes is not ax:
                hover_label_var.set("")
                return
            found = False
            for bar, code in zip(bars, on_pick_codes):
                if bar.contains_point((event.x, event.y)):
                    info = hover_meta.get(str(code)) or hover_meta.get(code)
                    if not info:
                        continue
                    nombre = str(info.get('full_name', code))
                    cod = str(info.get('code', code))
                    ventas = info.get('ventas', 0)
                    pct = info.get('pct', 0.0)
                    try:
                        ventas_txt = f"{int(round(ventas))}"
                    except Exception:
                        ventas_txt = str(ventas)
                    hover_label_var.set(f"{nombre}\nCod: {cod}  •  Ventas: {ventas_txt}  •  {pct:.1f}%")
                    found = True
                    break
            if not found:
                hover_label_var.set("")
        except Exception:
            pass

    canvas.mpl_connect('motion_notify_event', _on_motion)

    # Panel derecho: solo label con información extendida del ítem (sin Treeview de detalle)
    hover_label_var = None
    try:
        if hover_meta:
            old_label = getattr(app, 'stats_hover_detail_label', None)
            if old_label is not None:
                try:
                    old_label.destroy()
                except Exception:
                    pass
            if not hasattr(app, 'stats_hover_detail_var'):
                app.stats_hover_detail_var = tk.StringVar(value="")
            else:
                app.stats_hover_detail_var.set("")
            hover_label_var = app.stats_hover_detail_var
            app.stats_hover_detail_label = ttk.Label(
                right,
                textvariable=hover_label_var,
                wraplength=260,
                justify='left',
            )
            app.stats_hover_detail_label.pack(anchor='w', pady=(6, 0))
    except Exception:
        hover_label_var = None

    return canvas


def _stats_get_days_suffix(app):
    """Devuelve sufijo " - X días" según el rango de fechas actual de TRA, o cadena vacía."""
    try:
        fecha_ini = getattr(app, 'fecha_inicio_entry', None)
        fecha_fin = getattr(app, 'fecha_fin_entry', None)
        if not fecha_ini or not fecha_fin:
            return ""
        start = fecha_ini.get_date()
        end = fecha_fin.get_date()
        try:
            dias = (end - start).days + 1
        except Exception:
            return ""
        if dias <= 0:
            return ""
        return f" - {dias} días"
    except Exception:
        return ""


def _stats_draw_providers_universe(app, ventas_total_universo, total_universo, chart_type):
    """Dibuja la distribución de ventas por proveedor (universo completo de proveedores).

    Usa ÚNICAMENTE el universo actual de RI precargado (cached_ventas_tra) con todos los
    filtros ya aplicados (fechas, sede, texto, jerarquía, etc.) para garantizar coherencia.
    NO hace consultas adicionales a la BD - usa los mismos datos que departamentos.
    """
    from tkinter import ttk as _ttk  # alias local para evitar conflictos en linters

    try:
        # IMPORTANTE: Usar cached_proveedor_por_codigo si existe (precargado en RI)
        # para evitar consultas adicionales y garantizar consistencia con los filtros
        codigos_proveedor = getattr(app, 'cached_proveedor_por_codigo', None)
        
        if not codigos_proveedor:
            _stats_clear_container(app)
            _ttk.Label(
                app.graph_container, 
                text="No hay datos de proveedores cargados. Cargue el módulo RI primero."
            ).pack(pady=20)
            return

        # 1) Mapa código de producto -> neto total en el universo (ya filtrado por RI)
        product_neto = {}
        for r in ventas_total_universo or []:
            if not r or len(r) < 6:
                continue
            try:
                codigo = str(r[0]).strip()
            except Exception:
                continue
            if not codigo:
                continue
            try:
                neto = float(r[5] or 0)
            except Exception:
                neto = 0.0
            if neto <= 0:
                continue
            product_neto[codigo] = product_neto.get(codigo, 0.0) + neto

        if not product_neto:
            _stats_clear_container(app)
            _ttk.Label(app.graph_container, text="No hay ventas netas para agrupar por proveedor.").pack(pady=20)
            return

        # 2) Agrupar ventas por proveedor usando SOLO los datos precargados
        prov_totals = {}  # cod_proveedor -> (descripcion, neto_acumulado)
        productos_sin_proveedor = 0.0
        
        for codigo, neto in product_neto.items():
            # Buscar proveedor en cache precargado
            prov_info = codigos_proveedor.get(codigo)
            
            if not prov_info:
                # Producto sin proveedor asignado en los datos precargados
                productos_sin_proveedor += neto
                continue
            
            # prov_info puede ser (cod_prov, desc_prov) o solo cod_prov
            try:
                if isinstance(prov_info, (tuple, list)) and len(prov_info) >= 2:
                    cod_prov_str = str(prov_info[0]).strip()
                    desc_prov = str(prov_info[1]) if prov_info[1] else cod_prov_str
                else:
                    cod_prov_str = str(prov_info).strip()
                    desc_prov = cod_prov_str
            except Exception:
                continue
            
            if not cod_prov_str:
                productos_sin_proveedor += neto
                continue
            
            # Acumular ventas por proveedor
            cur_desc, cur_neto = prov_totals.get(cod_prov_str, (desc_prov, 0.0))
            prov_totals[cod_prov_str] = (cur_desc, cur_neto + neto)

        if not prov_totals and productos_sin_proveedor <= 0:
            _stats_clear_container(app)
            _ttk.Label(
                app.graph_container,
                text="No hay ventas asociadas a proveedores para el universo actual."
            ).pack(pady=20)
            return

        # 3) Construir serie para gráfico
        asignado = sum(val[1] for val in prov_totals.values())
        # Recalcular total_universo basado en product_neto para evitar inconsistencias
        total_universo = sum(product_neto.values())
        unassigned = productos_sin_proveedor  # Usar valor calculado directamente

        # Limitar número de proveedores visibles y agrupar el resto como "Otros"
        max_prov = 20
        items = sorted(prov_totals.items(), key=lambda kv: kv[1][1], reverse=True)
        top = items[:max_prov]
        rest = items[max_prov:]

        series = []  # (code, desc, neto)
        for code, (desc, neto) in top:
            series.append((code, desc, neto))

        if rest:
            rest_total = sum(v[1] for _, v in rest)
            if rest_total > 0:
                series.append(("__OTROS__", "Otros proveedores", rest_total))

        if unassigned > 0:
            series.append(("__SIN_PROV__", "Sin proveedor asignado", unassigned))

        if not series:
            _stats_clear_container(app)
            _ttk.Label(app.graph_container, text="No hay datos para mostrar por proveedor.").pack(pady=20)
            return

        total_for_pct = total_universo if (total_universo and total_universo > 0) else sum(s[2] for s in series) or 1.0

        labels = []
        sizes = []
        meta = []
        legend_rows = []
        for code, desc, neto in series:
            pct = (neto / total_for_pct) * 100.0
            labels.append(f"{desc}\n{pct:.1f}%")
            sizes.append(neto)
            meta.append(code)
            legend_rows.append((desc, pct, float(neto)))

        days_suffix = _stats_get_days_suffix(app)
        title = f"Distribución de ventas por proveedor (RI){days_suffix}"
        _stats_update_breadcrumb(app)

        if chart_type == 'bar':
            _stats_render_bar(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend_rows)
        else:
            _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend_rows)

    except Exception as e:
        _stats_clear_container(app)
        _ttk.Label(app.graph_container, text=f"Error generando estadísticas por proveedor: {e}").pack(pady=20)


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

    # Aplicar exclusiones globales de departamentos (mismo universo que RI)
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

    # Clonar lista para tener referencia del universo total (antes de filtrar por proveedor)
    ventas_total_universo = list(ventas)

    # Aplicar filtro de texto de RI (por código o descripción) al universo completo
    try:
        search_var = getattr(app, 'tra_search_var', None)
        texto = search_var.get().strip().lower() if search_var is not None else ''
        if texto:
            ventas_filtradas = []
            for r in ventas_total_universo:
                try:
                    cod = str(r[0]).lower() if len(r) > 0 and r[0] is not None else ''
                    desc = str(r[1]).lower() if len(r) > 1 and r[1] is not None else ''
                    if texto in cod or texto in desc:
                        ventas_filtradas.append(r)
                except Exception:
                    continue
            ventas_total_universo = ventas_filtradas
    except Exception:
        pass

    # A partir de aquí, ventas_total_universo representa el universo con filtros globales (excepto proveedor)
    if not ventas_total_universo:
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text="Sin datos para graficar con los filtros actuales de RI.").pack(pady=20)
        return

    # Calcular participación del proveedor (si hay filtro activo en RI)
    ventas_prov = []
    ventas_rest = []
    total_universo = 0.0
    total_prov = 0.0
    provider_share_txt = ""

    def _safe_neto(rec):
        try:
            return float(rec[5] or 0) if len(rec) > 5 else 0.0
        except Exception:
            return 0.0

    try:
        proveedor_cod = getattr(app, 'tra_proveedor_codigo', None)
        proveedor_desc = getattr(app, 'tra_proveedor_descripcion', None)

        # Calcular totales base del universo
        total_universo = sum(_safe_neto(r) for r in ventas_total_universo)

        if proveedor_cod and ventas_total_universo and total_universo > 0:
            # Usar cache precargado de producto->proveedor para consistencia
            cached_proveedor = getattr(app, 'cached_proveedor_por_codigo', {})
            if cached_proveedor:
                # Filtrar usando el mapeo precargado
                for r in ventas_total_universo:
                    if len(r) == 0:
                        continue
                    try:
                        cod = str(r[0])
                    except Exception:
                        continue
                    
                    # Buscar proveedor del producto en cache precargado
                    prov_info = cached_proveedor.get(cod)
                    if prov_info:
                        # prov_info es (cod_prov, desc_prov)
                        prov_cod_producto = str(prov_info[0]) if isinstance(prov_info, (tuple, list)) else str(prov_info)
                        if prov_cod_producto == str(proveedor_cod):
                            ventas_prov.append(r)
                        else:
                            ventas_rest.append(r)
                    else:
                        # Producto sin proveedor asignado -> resto
                        ventas_rest.append(r)
            else:
                # Fallback: usar método antiguo si no hay cache precargado
                codigos_prov = getattr(app, '_get_codigos_por_proveedor_cached', lambda _c: set())(proveedor_cod)
                if codigos_prov:
                    codigos_prov = set(str(c) for c in codigos_prov)
                    for r in ventas_total_universo:
                        if len(r) == 0:
                            continue
                        try:
                            cod = str(r[0])
                        except Exception:
                            continue
                        if cod in codigos_prov:
                            ventas_prov.append(r)
                        else:
                            ventas_rest.append(r)
                else:
                    ventas_prov = []
                    ventas_rest = list(ventas_total_universo)

            total_prov = sum(_safe_neto(r) for r in ventas_prov)
            if total_prov > 0:
                pct = (total_prov / total_universo) * 100.0
                prov_label = proveedor_desc or proveedor_cod
                provider_share_txt = f"Proveedor {prov_label}: {pct:.1f}% de la rotación (filtros actuales)"
    except Exception:
        proveedor_cod = None
        proveedor_desc = None

    # Actualizar etiqueta en la barra superior
    try:
        if hasattr(app, 'stats_provider_share_var'):
            app.stats_provider_share_var.set(provider_share_txt)
    except Exception:
        pass

    # Determinar tipo de gráfico (pie o barras)
    chart_mode = getattr(app, 'stats_chart_type_var', None)
    chart_type = 'pie'
    try:
        if chart_mode is not None:
            sel = chart_mode.get() or ''
            chart_type = 'bar' if 'Barra' in sel else 'pie'
    except Exception:
        chart_type = 'pie'

    # Determinar modo de vista: jerarquía (Depto/Grupo/Sub) vs universo de proveedores
    view_mode_var = getattr(app, 'stats_view_mode_var', None)
    stats_mode = 'hierarchy'
    try:
        if view_mode_var is not None:
            sel = view_mode_var.get() or ''
            if 'Proveed' in sel:
                stats_mode = 'providers'
    except Exception:
        stats_mode = 'hierarchy'

    # Si el usuario seleccionó vista por proveedor, dibujar y salir
    if stats_mode == 'providers':
        _stats_draw_providers_universe(app, ventas_total_universo, total_universo, chart_type)
        return

# Estado inicial según filtros actuales de TRA y proveedor
    # Resetear estado si cambió el proveedor seleccionado
    current_proveedor_key = f"{proveedor_cod}|{proveedor_desc}" if proveedor_cod else "no_proveedor"
    last_proveedor_key = getattr(app, '_stats_last_proveedor_key', None)
    
    state_changed = False
    if not hasattr(app, 'stats_pie_state') or not app.stats_pie_state:
        state_changed = True
    elif last_proveedor_key != current_proveedor_key:
        # El proveedor cambió, resetear estado
        state_changed = True
        app.stats_pie_state = None  # Forzar recreación
    
    app._stats_last_proveedor_key = current_proveedor_key
    
    if state_changed:
        if proveedor_cod and total_prov > 0 and total_universo > 0:
            # Empezar directamente desde nivel Departamento para el proveedor seleccionado
            # Esto permite drill-down inmediato sin importar el porcentaje de mercado
            app.stats_pie_state = {
                "level": "dept",
                "subset": "provider",  # usar solo datos del proveedor seleccionado
                "dept": None,
                "group": None,
                "sub": None,
            }
        else:
            # Sin proveedor: usar selección jerárquica actual de TRA como antes
            dept, group, sub = _stats_get_current_selection(app)
            if sub:
                app.stats_pie_state = {"level": "sub", "dept": dept, "group": group, "sub": sub}
            elif group:
                app.stats_pie_state = {"level": "group", "dept": dept, "group": group, "sub": None}
            elif dept:
                app.stats_pie_state = {"level": "group", "dept": dept, "group": None, "sub": None}
            else:
                app.stats_pie_state = {"level": "dept", "dept": None, "group": None, "sub": None}

    state = app.stats_pie_state
    inv = getattr(app, '_stats_inv_maps', _stats_build_inverse_maps(app))
    app._stats_inv_maps = inv

# Elegir conjunto de ventas según el subset actual (proveedor / resto / universo)
    subset = state.get('subset')
    
    # Si hay proveedor seleccionado pero no hay subset explícito, usar datos del proveedor por defecto
    if subset is None:
        if proveedor_cod and total_prov > 0:
            subset = 'provider'
        else:
            subset = 'all'
    
    
    
    if subset == 'provider' and ventas_prov:
        ventas = list(ventas_prov)
    elif subset == 'rest' and ventas_rest:
        ventas = list(ventas_rest)
    else:
        # Solo usar universo completo si no hay proveedor seleccionado
        if proveedor_cod and ventas_prov:
            ventas = list(ventas_prov)
        else:
            ventas = list(ventas_total_universo)

    # Si después de aplicar filtros no quedan datos, mostrar mensaje y salir
    if not ventas:
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text="Sin datos para graficar con los filtros actuales de RI.").pack(pady=20)
        return

    # Determinar nivel y agregar datos
    lvl = state.get('level', 'dept')

    # Sufijo con criterio de tiempo (número de días del rango actual en TRA)
    days_suffix = _stats_get_days_suffix(app)

    # Sufijo con proveedor activo (si hay filtro por proveedor en RI/TRA)
    provider_suffix = ""
    try:
        prov_cod = getattr(app, 'tra_proveedor_codigo', None)
        prov_desc = getattr(app, 'tra_proveedor_descripcion', None)
        if prov_cod:
            prov_text = prov_desc or prov_cod
            provider_suffix = f" — Proveedor: {prov_text}"
    except Exception:
        provider_suffix = ""

    # Nivel raíz: proveedor vs resto del universo (solo si hay filtro por proveedor con datos)
    if lvl == 'provider':
        try:
            if not (total_universo and total_prov and total_universo > 0 and total_prov > 0):
                _stats_clear_container(app)
                ttk.Label(app.graph_container, text="No hay datos suficientes para mostrar participación por proveedor.").pack(pady=20)
                return

            total_rest = max(0.0, total_universo - total_prov)
            if total_rest <= 0:
                # Todo el universo es del proveedor actual: mostrar mensaje simple
                _stats_clear_container(app)
                ttk.Label(
                    app.graph_container,
                    text="El 100% de la rotación del período corresponde al proveedor seleccionado."
                ).pack(pady=20)
                return

            prov_label = prov_desc or prov_cod or 'Proveedor'
            data_map = {
                'PROV': total_prov,
                'REST': total_rest,
            }

            # Construir labels, sizes y meta específicos
            total = total_universo or 1.0
            labels = []
            sizes = []
            meta = []
            legend = []
            for key, val in data_map.items():
                pct = (val / total) * 100.0
                if key == 'PROV':
                    name = prov_label
                else:
                    name = 'Resto de proveedores'
                labels.append(f"{name}\n{pct:.1f}%")
                sizes.append(val)
                meta.append(key)
                legend.append((name, pct, float(val)))

            title = f"Participación del proveedor en la rotación (RI){days_suffix}"
            _stats_update_breadcrumb(app)
            if chart_type == 'bar':
                _stats_render_bar(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
            else:
                _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
            return
        except Exception:
            # Si algo falla, degradar a nivel depto usando el subset actual
            lvl = 'dept'

    if lvl == 'dept':
        # Agregar por departamento en todos los datos (sin filtrar por dept)
        data_map = _stats_aggregate(ventas, 'dept')
        if not data_map:
            _stats_clear_container(app)
            ttk.Label(app.graph_container, text=f"No hay ventas por departamento para mostrar{provider_suffix}").pack(pady=10)
            return
        labels, sizes, meta, legend = _stats_format_labels(data_map, inv_maps=inv, level='dept')
        title = f"Representación por Departamento (RI){days_suffix}{provider_suffix}"
        _stats_update_breadcrumb(app)
        if chart_type == 'bar':
            _stats_render_bar(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        else:
            _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        return
    elif lvl == 'group':
        dept = state.get('dept')
        # Filtrar por dept y agregar grupos
        data_map = _stats_aggregate(ventas, 'group', dept=dept)
        if not data_map:
            _stats_clear_container(app)
            name = inv['dept'].get(str(dept), str(dept)) if dept else 'N/A'
            ttk.Label(app.graph_container, text=f"Sin datos de grupos para {name}{provider_suffix}").pack(pady=10)
            return
        labels, sizes, meta, legend = _stats_format_labels(data_map, inv_maps=inv, level='group', dept=dept)
        name = inv['dept'].get(str(dept), str(dept)) if dept else ''
        title = f"{name} — Representación por Grupo{days_suffix}{provider_suffix}"
        _stats_update_breadcrumb(app)
        if chart_type == 'bar':
            _stats_render_bar(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        else:
            _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        return
    elif lvl == 'sub':
        dept = state.get('dept')
        group = state.get('group')
        data_map = _stats_aggregate(ventas, 'sub', dept=dept, group=group)
        if not data_map:
            _stats_clear_container(app)
            dname = inv['dept'].get(str(dept), str(dept)) if dept else 'N/A'
            gname = inv['group'].get((str(dept), str(group)), str(group)) if group else 'N/A'
            ttk.Label(app.graph_container, text=f"Sin datos de subgrupos para {dname} / {gname}{provider_suffix}").pack(pady=10)
            return
        labels, sizes, meta, legend = _stats_format_labels(data_map, inv_maps=inv, level='sub', dept=dept, group=group)
        dname = inv['dept'].get(str(dept), str(dept)) if dept else ''
        gname = inv['group'].get((str(dept), str(group)), str(group)) if group else ''
        title = f"{dname} → {gname} — Representación por Subgrupo{days_suffix}{provider_suffix}"
        _stats_update_breadcrumb(app)
        if chart_type == 'bar':
            _stats_render_bar(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        else:
            _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        return
    elif lvl == 'product':
        dept = state.get('dept')
        group = state.get('group')
        sub = state.get('sub')
        # Validar que haya contexto completo para productos
        if not (dept and group and sub):
            # Si falta algo, regresar a nivel de subgrupos
            state['level'] = 'sub'
            app.stats_pie_state = state
            app.mostrar_estadisticas()
            return

        # Filtrar registros del subgrupo seleccionado y agrupar por producto
        product_totals = {}
        product_names = {}
        for r in ventas:
            if len(r) < 6:
                continue
            try:
                if not (
                    str(r[2]) == str(dept)
                    and str(r[3]) == str(group)
                    and str(r[4]) == str(sub)
                ):
                    continue
            except Exception:
                continue
            code = str(r[0])
            name = str(r[1]) if len(r) > 1 and r[1] is not None else code
            try:
                neto = float(r[5] or 0)
            except Exception:
                neto = 0.0
            if neto <= 0:
                continue
            product_totals[code] = product_totals.get(code, 0.0) + neto
            if code not in product_names:
                product_names[code] = name

        if not product_totals:
            _stats_clear_container(app)
            dname = inv['dept'].get(str(dept), str(dept)) if dept else 'N/A'
            gname = inv['group'].get((str(dept), str(group)), str(group)) if group else 'N/A'
            sname = inv['sub'].get((str(dept), str(group), str(sub)), str(sub)) if sub else 'N/A'
            ttk.Label(app.graph_container, text=f"Sin datos de productos para {dname} / {gname} / {sname}{provider_suffix}").pack(pady=10)
            return

        # Ordenar productos por neto y limitar a top 25 para estética
        max_products = 25
        items = sorted(product_totals.items(), key=lambda kv: kv[1], reverse=True)[:max_products]
        total = sum(v for _, v in items) or 1.0

        labels = []
        sizes = []
        meta = []
        legend = []
        hover_meta = {}
        for code, val in items:
            full_name = product_names.get(code, code)
            # Limitar nombre visible a 15 caracteres para mantener estética en la etiqueta
            name = str(full_name)
            max_len = 15
            if len(name) > max_len:
                name = name[:max_len]
            pct = (val / total) * 100.0
            labels.append(f"{name}\n{pct:.1f}%")
            sizes.append(val)
            meta.append(code)
            legend.append((name, pct, float(val)))
            hover_meta[str(code)] = {
                'full_name': str(full_name),
                'code': str(code),
                'ventas': float(val),
                'pct': float(pct),
            }

        dname = inv['dept'].get(str(dept), str(dept)) if dept else ''
        gname = inv['group'].get((str(dept), str(group)), str(group)) if group else ''
        sname = inv['sub'].get((str(dept), str(group), str(sub)), str(sub)) if sub else ''
        title = f"{dname} → {gname} → {sname} — Top {len(items)} productos{days_suffix}{provider_suffix}"
        _stats_update_breadcrumb(app)
        if chart_type == 'bar':
            _stats_render_bar(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend, hover_meta=hover_meta)
        else:
            _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend, hover_meta=hover_meta)
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

    app.stats_breadcrumb_var = tk.StringVar(value="Todos los proveedores")
    ttk.Label(top_bar, textvariable=app.stats_breadcrumb_var).pack(side=tk.LEFT, padx=10)

    # Indicador de participación del proveedor en RI (se muestra solo si hay filtro activo)
    app.stats_provider_share_var = tk.StringVar(value="")
    app.stats_provider_share_label = ttk.Label(
        top_bar,
        textvariable=app.stats_provider_share_var,
        foreground="#555555",
    )
    app.stats_provider_share_label.pack(side=tk.LEFT, padx=10)

    # Selector de tipo de gráfico
    app.stats_chart_type_var = tk.StringVar(value="Pie (porcentaje)")
    chart_type_combo = ttk.Combobox(
        top_bar,
        textvariable=app.stats_chart_type_var,
        state='readonly',
        width=22,
        values=[
            "Pie (porcentaje)",
            "Barras horizontales"
        ],
    )
    chart_type_combo.pack(side=tk.RIGHT, padx=(5, 0))

    # Selector de tipo de estadística (Jerarquía vs Proveedores)
    app.stats_view_mode_var = tk.StringVar(value="Jerarquía productos (Depto/Grupo/Sub)")
    view_mode_combo = ttk.Combobox(
        top_bar,
        textvariable=app.stats_view_mode_var,
        state='readonly',
        width=32,
        values=[
            "Jerarquía productos (Depto/Grupo/Sub)",
            "Distribución por Proveedor",
        ],
    )
    view_mode_combo.pack(side=tk.RIGHT, padx=(5, 0))

    ttk.Button(
        top_bar,
        text="Actualizar Gráficos",
        command=lambda: getattr(app, 'mostrar_estadisticas', lambda: None)()
    ).pack(side=tk.RIGHT, padx=(0, 5))

    # Refrescar gráficos automáticamente al cambiar tipo de gráfico o de vista
    chart_type_combo.bind('<<ComboboxSelected>>', lambda e: getattr(app, 'mostrar_estadisticas', lambda: None)())
    view_mode_combo.bind('<<ComboboxSelected>>', lambda e: getattr(app, 'mostrar_estadisticas', lambda: None)())

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
