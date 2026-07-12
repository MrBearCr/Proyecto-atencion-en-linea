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
    """Actualiza el breadcrumb teniendo en cuenta el modo actual, proveedor y jerarquía."""
    state = getattr(app, 'stats_pie_state', {"mode": "tra", "level": "dept", "dept": None, "group": None, "sub": None})
    inv = getattr(app, '_stats_inv_maps', _stats_build_inverse_maps(app))
    app._stats_inv_maps = inv

    parts = []

    mode = state.get('mode', 'tra')

    if mode == 'mbrp':
        # Raíz específica para estadísticas MBRP (días sin venta)
        parts.append("MBRP — Días sin venta")
    else:
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
        if hasattr(app, 'stats_btn_back'):
            app.stats_btn_back.state(["disabled"])
    else:
        try:
            if hasattr(app, 'stats_btn_back'):
                app.stats_btn_back.state(["!disabled"])  # habilitar
        except Exception:
            pass


def _stats_go_back(app):
    state = getattr(app, 'stats_pie_state', {"mode": "tra", "level": "dept", "dept": None, "group": None})
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
                    pct = info.get('pct', 0.0)

                    # Soportar tanto métricas de ventas (TRA) como días sin venta (MBRP)
                    dias = info.get('dias', None)
                    if dias is not None:
                        try:
                            dias_txt = f"{int(round(dias))}"
                        except Exception:
                            dias_txt = str(dias)
                        hover_label_var.set(f"{nombre}\nCod: {cod}  •  Días sin venta: {dias_txt}  •  {pct:.1f}%")
                    else:
                        ventas = info.get('ventas', 0)
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
    ax.set_xlabel('Valor')
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
                    pct = info.get('pct', 0.0)

                    # Soportar tanto métricas de ventas (TRA) como días sin venta (MBRP)
                    dias = info.get('dias', None)
                    if dias is not None:
                        try:
                            dias_txt = f"{int(round(dias))}"
                        except Exception:
                            dias_txt = str(dias)
                        hover_label_var.set(f"{nombre}\nCod: {cod}  •  Días sin venta: {dias_txt}  •  {pct:.1f}%")
                    else:
                        ventas = info.get('ventas', 0)
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


def _stats_transform_for_metric(app, records):
    """Devuelve una nueva lista de registros TRA con el campo índice 5 en unidades o dólares.

    Si el checkbox "Ventas en $" de TRA está activo, convierte las unidades a monto en dólares
    usando la lógica centralizada de la app (cache de precios + IVA). En caso contrario,
    devuelve una copia superficial de los registros originales.
    """
    if not records:
        return []

    # Determinar si estamos en modo dólares
    try:
        mostrar_dolares_var = getattr(app, 'tra_mostrar_dolares_var', None)
        use_dollars = bool(mostrar_dolares_var and mostrar_dolares_var.get())
    except Exception:
        use_dollars = False

    # Si no se solicita dólares, devolver copia simple
    if not use_dollars:
        return list(records)

    # Verificar helper de conversión
    convertir = getattr(app, '_convertir_unidades_a_dolares', None)
    if not callable(convertir):
        # Sin helper, degradar a unidades
        return list(records)

    # Precargar precios en bulk si es posible (más eficiente que consulta por producto)
    try:
        codigos = []
        for r in records:
            try:
                if r and len(r) > 0 and r[0] is not None:
                    codigos.append(str(r[0]))
            except Exception:
                continue
        if codigos and hasattr(app, '_cargar_precios_bulk'):
            # Usar solo códigos únicos para minimizar la consulta
            app._cargar_precios_bulk(list(set(codigos)))
    except Exception:
        # Si algo falla, continuamos sin precarga (fallback a consultas individuales)
        pass

    new_records = []
    for r in records:
        try:
            if not r or len(r) < 6:
                new_records.append(r)
                continue

            codigo = str(r[0]) if r[0] is not None else None
            try:
                unidades = float(r[5] or 0)
            except Exception:
                unidades = 0.0

            if not codigo or unidades <= 0:
                # Nada que convertir; mantener registro con neto original
                new_records.append(r)
                continue

            try:
                valor_dolares = float(convertir(codigo, unidades) or 0.0)
            except Exception:
                # En caso de error de conversión, degradar a unidades
                valor_dolares = unidades

            r_list = list(r)
            if len(r_list) < 6:
                r_list.extend([None] * (6 - len(r_list)))
            r_list[5] = valor_dolares
            new_records.append(tuple(r_list))
        except Exception:
            # Ante cualquier excepción inesperada, preservar el registro tal cual
            new_records.append(r)

    return new_records


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


# Mapeo de nombre de sede a prefijo de depósito según convenciones del proyecto.
# Ref: docs/contexto/convenciones.md
_SEDE_NOMBRE_A_CODIGO = {
    "barinas":   "01",
    "cabudare":  "03",
    "guanare":   "04",
    "araure":    "05",
}
# Colores por sede para el gráfico multi-línea
_SEDE_COLORES = {
    "01": "#1F77B4",  # Barinas - azul
    "03": "#FF7F0E",  # Cabudare - naranja
    "04": "#2CA02C",  # Guanare - verde
    "05": "#D62728",  # Araure - rojo
}


def _sede_val_to_codigo(sede_val: str) -> str:
    """Convierte la cadena del combo de sede a código de depósito."""
    v = sede_val.strip()
    if "ICH" in v or v.startswith("00"):
        return "ICH"
    # Formato "01 - Barinas"
    parte = v.split(" ")[0].strip()
    if parte.isdigit():
        return parte.zfill(2)
    # Fallback: buscar por nombre
    return _SEDE_NOMBRE_A_CODIGO.get(v.lower(), "ICH")


def _stats_compute_and_draw_timeline(app):
    import threading
    _stats_clear_container(app)

    try:
        fecha_ini = getattr(app, 'stats_timeline_fecha_inicio', None)
        fecha_fin = getattr(app, 'stats_timeline_fecha_fin', None)
        if not fecha_ini or not fecha_fin:
            ttk.Label(app.graph_container, text="Seleccione el rango de fechas.").pack(pady=20)
            return

        start_date = fecha_ini.get_date()
        end_date = fecha_fin.get_date()

        sede_var = getattr(app, 'stats_timeline_sede_var', None)
        sede_val = sede_var.get() if sede_var else "00 - ICH"
        sede_codigo = _sede_val_to_codigo(sede_val)

        metrica_var = getattr(app, 'stats_timeline_metric_var', None)
        is_dollars = bool(metrica_var and "Monto" in metrica_var.get())

        lbl_loading = ttk.Label(app.graph_container, text="⏳ Consultando historial de ventas... por favor espere.")
        lbl_loading.pack(pady=30)

        def task():
            # Modo ICH: una consulta por cada sede configurada
            if sede_codigo == "ICH":
                try:
                    sedes_config = app.db_manager.get_sedes_config()
                except Exception:
                    sedes_config = []

                series = {}  # {label: {fecha: valor}}
                for sc in sedes_config:
                    nombre = sc.get('nombre_sede', 'Sede')
                    cod = _SEDE_NOMBRE_A_CODIGO.get(nombre.lower(), None)
                    if not cod:
                        continue
                    rows = app.db_manager.get_ventas_timeline(start_date, end_date, cod, include_monto=is_dollars)
                    series[nombre] = _aggregate_rows(rows, is_dollars)

                app.root.after(0, lambda s=series: _stats_render_timeline_multiline(
                    app, s, is_dollars, lbl_loading, sede_val))
            else:
                data = app.db_manager.get_ventas_timeline(start_date, end_date, sede_codigo, include_monto=is_dollars)
                app.root.after(0, lambda d=data: _stats_render_timeline_result(
                    app, d, is_dollars, lbl_loading, sede_val, sede_codigo))

        threading.Thread(target=task, daemon=True).start()
    except Exception as e:
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text=f"Error al iniciar consulta: {e}").pack(pady=20)


def _aggregate_rows(rows, is_dollars):
    """Agrupa filas (fecha, unidades[, monto]) en {fecha: valor_total}.
    
    Cuando include_monto=True la query ya devuelve (fecha, unidades, monto).
    Cuando include_monto=False devuelve (fecha, unidades).
    """
    from datetime import date as _date
    acumulado = {}
    for r in (rows or []):
        if not r or len(r) < 2:
            continue
        fecha = r[0]
        # Normalizar a datetime.date
        if hasattr(fecha, 'date'):
            fecha = fecha.date()
        if is_dollars:
            # columna 2 = monto ya calculado en SQL
            valor = float(r[2] if len(r) > 2 else 0) if r[2] else 0.0
        else:
            valor = float(r[1] or 0)
        if valor <= 0:
            continue
        acumulado[fecha] = acumulado.get(fecha, 0.0) + valor
    return acumulado


def _stats_render_timeline_result(app, data, is_dollars, lbl_loading, sede_val, sede_codigo):
    """Renderiza una única línea (sede específica)."""
    try:
        lbl_loading.destroy()
    except Exception:
        pass
    _stats_clear_container(app)

    ventas_por_dia = _aggregate_rows(data, is_dollars)

    if not ventas_por_dia:
        ttk.Label(app.graph_container,
                  text=f"No se encontraron ventas para '{sede_val}' en el período seleccionado.").pack(pady=20)
        return

    try:
        from datetime import datetime
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import matplotlib.dates as mdates

        fechas_ordenadas = sorted(ventas_por_dia.keys())
        # Convertir datetime.date a datetime.datetime para matplotlib
        fechas_dt = [datetime(f.year, f.month, f.day) for f in fechas_ordenadas]
        valores = [ventas_por_dia[f] for f in fechas_ordenadas]

        color = _SEDE_COLORES.get(sede_codigo, '#1F77B4')
        eje_y = "Monto ($)" if is_dollars else "Unidades Netas"

        fig = Figure(figsize=(9, 5), dpi=100)
        ax = fig.add_subplot(111)
        line, = ax.plot(fechas_dt, valores, marker='o', markersize=4, linestyle='-',
                        color=color, linewidth=2, label=sede_val)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        fig.autofmt_xdate()
        ax.set_ylabel(eje_y)
        ax.set_title(f"Comportamiento de Ventas — {sede_val}")
        ax.grid(True, linestyle='--', alpha=0.5)

        annot = ax.annotate("", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
                            bbox=dict(boxstyle="round,pad=0.4", fc="#FFFDE7", ec="#333"),
                            arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)

        def hover(event):
            if event.inaxes != ax:
                if annot.get_visible():
                    annot.set_visible(False)
                    fig.canvas.draw_idle()
                return
            cont, ind = line.contains(event)
            if cont:
                idx = ind["ind"][0]
                f = fechas_ordenadas[idx]  # datetime.date original
                v = valores[idx]
                annot.xy = (fechas_dt[idx], v)
                val_str = f"${v:,.2f}" if is_dollars else f"{v:,.0f} unds"
                annot.set_text(f"{f.strftime('%d/%m/%Y')}\n{val_str}")
                annot.set_visible(True)
                fig.canvas.draw_idle()
            else:
                if annot.get_visible():
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

        canvas = FigureCanvasTkAgg(fig, master=app.graph_container)
        canvas.mpl_connect("motion_notify_event", hover)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    except Exception as e:
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text=f"Error renderizando: {e}").pack(pady=20)


def _stats_render_timeline_multiline(app, series, is_dollars, lbl_loading, sede_val):
    """Renderiza múltiples líneas (ICH = una línea por sede)."""
    try:
        lbl_loading.destroy()
    except Exception:
        pass
    _stats_clear_container(app)

    if not any(v for v in series.values()):
        ttk.Label(app.graph_container, text="No se encontraron ventas para ninguna sede en el período.").pack(pady=20)
        return

    try:
        from datetime import datetime
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import matplotlib.dates as mdates

        fig = Figure(figsize=(9, 5), dpi=100)
        ax = fig.add_subplot(111)
        eje_y = "Monto ($)" if is_dollars else "Unidades Netas"

        all_lines = []  # (nombre, fechas_dt, fechas_orig, valores, line_obj)
        for nombre, ventas in series.items():
            if not ventas:
                continue
            fechas_orig = sorted(ventas.keys())
            fechas_dt = [datetime(f.year, f.month, f.day) for f in fechas_orig]
            valores = [ventas[f] for f in fechas_orig]
            cod = _SEDE_NOMBRE_A_CODIGO.get(nombre.lower(), '01')
            color = _SEDE_COLORES.get(cod, '#1F77B4')
            line, = ax.plot(fechas_dt, valores, marker='o', markersize=4, linestyle='-',
                            color=color, linewidth=2, label=nombre)
            all_lines.append((nombre, fechas_dt, fechas_orig, valores, line))

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        fig.autofmt_xdate()
        ax.set_ylabel(eje_y)
        ax.set_title("Comportamiento de Ventas — Todas las Sedes (ICH)")
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(loc='upper left', fontsize=9)

        annot = ax.annotate("", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
                            bbox=dict(boxstyle="round,pad=0.4", fc="#FFFDE7", ec="#333"),
                            arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)

        def hover(event):
            if event.inaxes != ax:
                if annot.get_visible():
                    annot.set_visible(False)
                    fig.canvas.draw_idle()
                return
            found = False
            for (nombre, fechas_dt_l, fechas_orig_l, valores_l, line) in all_lines:
                cont, ind = line.contains(event)
                if cont:
                    idx = ind["ind"][0]
                    f = fechas_orig_l[idx]
                    v = valores_l[idx]
                    annot.xy = (fechas_dt_l[idx], v)
                    val_str = f"${v:,.2f}" if is_dollars else f"{v:,.0f} unds"
                    annot.set_text(f"{nombre}\n{f.strftime('%d/%m/%Y')}\n{val_str}")
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                    found = True
                    break
            if not found and annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()

        canvas = FigureCanvasTkAgg(fig, master=app.graph_container)
        canvas.mpl_connect("motion_notify_event", hover)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    except Exception as e:
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text=f"Error renderizando ICH: {e}").pack(pady=20)



def _stats_compute_and_draw(app):
    # Determinar tipo de gráfico (pie o barras)
    chart_mode = getattr(app, 'stats_chart_type_var', None)
    chart_type = 'pie'
    try:
        if chart_mode is not None:
            sel = chart_mode.get() or ''
            chart_type = 'bar' if 'Barra' in sel else 'pie'
    except Exception:
        chart_type = 'pie'

    # Determinar modo de vista (Jerarquía TRA, Proveedores, MBRP días sin venta, Mapa de Calor, Línea de tiempo)
    view_mode_var = getattr(app, 'stats_view_mode_var', None)
    stats_mode = 'hierarchy'
    try:
        if view_mode_var is not None:
            sel = (view_mode_var.get() or '').strip()
            if 'Proveed' in sel:
                stats_mode = 'providers'
            elif 'MBRP' in sel or 'sin venta' in sel or 'Sin venta' in sel:
                stats_mode = 'mbrp_days'
            elif 'Mapa de Calor' in sel or 'calor' in sel.lower():
                stats_mode = 'heatmap'
            elif 'Comportamiento de Ventas' in sel or 'Línea de tiempo' in sel:
                stats_mode = 'timeline'
    except Exception:
        stats_mode = 'hierarchy'
        
    if stats_mode == 'timeline':
        _stats_compute_and_draw_timeline(app)
        return

    # Si el usuario seleccionó vista basada en MBRP (días sin venta), delegar a rutina específica
    if stats_mode == 'mbrp_days':
        _stats_compute_and_draw_mbrp(app, chart_type)
        return

    # Si el usuario seleccionó mapa de calor, delegar a rutina específica
    if stats_mode == 'heatmap':
        _stats_compute_and_draw_heatmap(app)
        return

    # ==========================
    # Modo RI / TRA (unidades/$)
    # ==========================
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
    # Adaptar métrica según modo (unidades vs dólares) utilizando helper centralizado
    ventas_total_universo = _stats_transform_for_metric(app, ventas_total_universo)

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
                "mode": "tra",
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
                app.stats_pie_state = {"mode": "tra", "level": "sub", "dept": dept, "group": group, "sub": sub}
            elif group:
                app.stats_pie_state = {"mode": "tra", "level": "group", "dept": dept, "group": group, "sub": None}
            elif dept:
                app.stats_pie_state = {"mode": "tra", "level": "group", "dept": dept, "group": None, "sub": None}
            else:
                app.stats_pie_state = {"mode": "tra", "level": "dept", "dept": None, "group": None, "sub": None}

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

def _stats_mbrp_compute_days_map(app, ventas):
    """Construye un mapa codigo -> días sin venta usando servicios MBRP.

    Usa y actualiza el caché `_mbrp_ultimas_ventas_cache` ya utilizado por el módulo MBRP
    para evitar consultas repetitivas a la base de datos.
    """
    if not ventas:
        return {}

    try:
        from pal.services.mbrp import obtener_ultimas_ventas_bulk, calcular_dias_sin_venta
    except Exception:
        # Si no se pueden importar servicios MBRP, no hay estadísticas disponibles
        return {}

    db_manager = getattr(app, 'db_manager', None)
    if db_manager is None:
        return {}

    # Construir conjunto de códigos únicos
    codigos = []
    for r in ventas:
        try:
            if r and len(r) > 0 and r[0] is not None:
                codigos.append(str(r[0]))
        except Exception:
            continue
    if not codigos:
        return {}
    codigos_unicos = list(set(codigos))

    sede = getattr(app, 'mbrp_sede_codigo', None) or '0301'

    # Inicializar/usar caché de últimas ventas compartido con MBRP
    if not hasattr(app, '_mbrp_ultimas_ventas_cache') or not isinstance(getattr(app, '_mbrp_ultimas_ventas_cache'), dict):
        app._mbrp_ultimas_ventas_cache = {}
    ultimas_cache = app._mbrp_ultimas_ventas_cache

    # Solo consultar códigos faltantes en caché
    codigos_faltantes = [c for c in codigos_unicos if c not in ultimas_cache]

    if codigos_faltantes:
        try:
            nuevos = obtener_ultimas_ventas_bulk(db_manager, codigos_faltantes, sede)
        except Exception:
            nuevos = {}
        if nuevos:
            # Merge con el caché existente
            for c, fecha in nuevos.items():
                ultimas_cache[str(c)] = fecha

    ultimas = ultimas_cache

    dias_map = {}
    for codigo in codigos_unicos:
        try:
            fecha = ultimas.get(codigo)
            dias = calcular_dias_sin_venta(fecha)
        except Exception:
            dias = -1
        dias_map[codigo] = dias

    # Ajustar productos sin ventas (días = -1) a un valor alto consistente
    max_pos = max((d for d in dias_map.values() if d >= 0), default=0)
    special = max_pos + 1 if max_pos > 0 else 30
    for codigo, dias in list(dias_map.items()):
        if dias < 0:
            dias_map[codigo] = special

    return dias_map


def _stats_mbrp_aggregate_days(ventas, dias_map, level, *, dept=None, group=None):
    """Agrega días sin venta por nivel jerárquico (promedio de días)."""
    if not ventas or not dias_map:
        return {}

    acc_sum = {}
    acc_cnt = {}

    for r in ventas:
        if len(r) < 6:
            continue
        # Determinar clave jerárquica igual que en _stats_aggregate
        if level == 'dept':
            key = str(r[2]) if len(r) > 2 and r[2] is not None else None
        elif level == 'group':
            if dept is None:
                continue
            if len(r) > 2 and str(r[2]) != str(dept):
                continue
            key = str(r[3]) if len(r) > 3 and r[3] is not None else None
        elif level == 'sub':
            if dept is None or group is None:
                continue
            if not (len(r) > 2 and str(r[2]) == str(dept) and len(r) > 3 and str(r[3]) == str(group)):
                continue
            key = str(r[4]) if len(r) > 4 and r[4] is not None else None
        else:
            key = None

        if not key:
            continue

        codigo = str(r[0])
        dias = dias_map.get(codigo)
        if dias is None:
            continue

        acc_sum[key] = acc_sum.get(key, 0.0) + float(dias)
        acc_cnt[key] = acc_cnt.get(key, 0) + 1

    # Promedio de días sin venta por clave
    values = {}
    for k, total_dias in acc_sum.items():
        cnt = acc_cnt.get(k) or 0
        if cnt > 0:
            values[k] = total_dias / cnt
    return values


def _stats_compute_and_draw_mbrp(app, chart_type):
    """Dibuja estadísticas MBRP basadas en días sin venta por Dept/Grupo/Sub/Producto.

    Nota: todo cálculo pesado (consulta de últimas ventas) se ejecuta en segundo
    plano para no bloquear el hilo principal de Tkinter.
    """
    # Validar datos MBRP cargados
    ventas = getattr(app, 'cached_ventas_mbrp_effective', None)
    if ventas is None:
        ventas = getattr(app, 'cached_ventas_mbrp', None)

    if not ventas:
        try:
            messagebox.showinfo("Estadísticas", "Primero cargue datos en la pestaña MBRP")
        except Exception:
            pass
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text="Sin datos MBRP para graficar. Cargue MBRP y presione 'Actualizar Gráficos'.").pack(pady=20)
        return

    # Aplicar exclusiones globales de departamentos
    try:
        excluded = set(str(x) for x in (getattr(app, 'excluded_depts', []) or []))
    except Exception:
        excluded = set()

    if excluded:
        ventas = [r for r in ventas if len(r) > 2 and str(r[2]) not in excluded]

    # Aplicar filtro por proveedor activo en MBRP (si existe)
    try:
        proveedor_cod = getattr(app, 'mbrp_proveedor_codigo', None)
        if proveedor_cod:
            get_codigos = getattr(app, '_get_codigos_por_proveedor_cached', None)
            if callable(get_codigos):
                codigos_prov = get_codigos(proveedor_cod)
                if codigos_prov:
                    codigos_set = set(str(c) for c in codigos_prov)
                    ventas = [r for r in ventas if r and str(r[0]) in codigos_set]
                else:
                    ventas = []
    except Exception:
        # En caso de error en el filtro de proveedor, continuar con dataset sin filtrar por proveedor
        pass

    if not ventas:
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text="Sin datos MBRP para graficar con los filtros actuales.").pack(pady=20)
        return

    # Construir mapa de días sin venta por producto (cacheado por dataset)
    try:
        cache_key = f"{len(ventas)}|{getattr(app, 'mbrp_fecha_inicio', None)}|{getattr(app, 'mbrp_fecha_fin', None)}|{getattr(app, 'mbrp_sede_codigo', None)}"
    except Exception:
        cache_key = None

    dias_map = getattr(app, '_stats_mbrp_dias_map', None)
    dias_key = getattr(app, '_stats_mbrp_dias_key', None)

    # Si no hay mapa de días calculado para el dataset actual, lanzarlo en background
    if dias_map is None or dias_key != cache_key:
        # Evitar lanzar múltiples hilos simultáneos para el mismo cálculo
        if not getattr(app, '_stats_mbrp_loading_dias', False):
            try:
                app._stats_mbrp_loading_dias = True
            except Exception:
                pass

            import threading

            def _worker():
                try:
                    new_map = _stats_mbrp_compute_days_map(app, ventas)
                except Exception:
                    new_map = {}

                def _on_finish():
                    try:
                        app._stats_mbrp_dias_map = new_map
                        app._stats_mbrp_dias_key = cache_key
                    except Exception:
                        pass
                    finally:
                        try:
                            app._stats_mbrp_loading_dias = False
                        except Exception:
                            pass
                    # Reintentar renderizado ahora que el cálculo terminó
                    try:
                        app.mostrar_estadisticas()
                    except Exception:
                        pass

                root = getattr(app, 'root', None)
                if root is not None:
                    try:
                        root.after(0, _on_finish)
                    except Exception:
                        _on_finish()
                else:
                    _on_finish()

            try:
                threading.Thread(target=_worker, daemon=True, name="StatsMBRPDias").start()
            except Exception:
                try:
                    app._stats_mbrp_loading_dias = False
                except Exception:
                    pass

        # Mostrar estado de carga sin bloquear la UI
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text="Calculando días sin venta para MBRP...").pack(pady=20)
        return

    if not dias_map:
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text="No se pudieron calcular días sin venta para MBRP.").pack(pady=20)
        return

    # Estado inicial específico para MBRP
    state = getattr(app, 'stats_pie_state', None)
    if not state or state.get('mode') != 'mbrp':
        app.stats_pie_state = {
            "mode": "mbrp",
            "level": "dept",
            "dept": None,
            "group": None,
            "sub": None,
        }
        state = app.stats_pie_state

    lvl = state.get('level', 'dept')

    inv = getattr(app, '_stats_inv_maps', _stats_build_inverse_maps(app))
    app._stats_inv_maps = inv

    # Días de rango MBRP (para título opcional)
    try:
        fecha_ini = getattr(app, 'mbrp_fecha_inicio', None)
        fecha_fin = getattr(app, 'mbrp_fecha_fin', None)
        if fecha_ini and fecha_fin:
            dias_rango = (fecha_fin - fecha_ini).days + 1
            rango_suffix = f" - Rango {dias_rango} días"
        else:
            rango_suffix = ""
    except Exception:
        rango_suffix = ""

    # Nivel Departamento
    if lvl == 'dept':
        data_map = _stats_mbrp_aggregate_days(ventas, dias_map, 'dept')
        if not data_map:
            _stats_clear_container(app)
            ttk.Label(app.graph_container, text="Sin datos de días sin venta por departamento.").pack(pady=10)
            return
        labels, sizes, meta, legend = _stats_format_labels(data_map, inv_maps=inv, level='dept')
        title = f"MBRP — Días sin venta promedio por Departamento{rango_suffix}"
        _stats_update_breadcrumb(app)
        if chart_type == 'bar':
            _stats_render_bar(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        else:
            _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        return

    # Nivel Grupo
    if lvl == 'group':
        dept = state.get('dept')
        data_map = _stats_mbrp_aggregate_days(ventas, dias_map, 'group', dept=dept)
        if not data_map:
            _stats_clear_container(app)
            name = inv['dept'].get(str(dept), str(dept)) if dept else 'N/A'
            ttk.Label(app.graph_container, text=f"Sin datos de días sin venta por grupo en {name}.").pack(pady=10)
            return
        labels, sizes, meta, legend = _stats_format_labels(data_map, inv_maps=inv, level='group', dept=dept)
        name = inv['dept'].get(str(dept), str(dept)) if dept else ''
        title = f"MBRP — {name} — Días sin venta promedio por Grupo{rango_suffix}"
        _stats_update_breadcrumb(app)
        if chart_type == 'bar':
            _stats_render_bar(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        else:
            _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        return

    # Nivel Subgrupo
    if lvl == 'sub':
        dept = state.get('dept')
        group = state.get('group')
        data_map = _stats_mbrp_aggregate_days(ventas, dias_map, 'sub', dept=dept, group=group)
        if not data_map:
            _stats_clear_container(app)
            dname = inv['dept'].get(str(dept), str(dept)) if dept else 'N/A'
            gname = inv['group'].get((str(dept), str(group)), str(group)) if group else 'N/A'
            ttk.Label(app.graph_container, text=f"Sin datos de días sin venta por subgrupo en {dname} / {gname}.").pack(pady=10)
            return
        labels, sizes, meta, legend = _stats_format_labels(data_map, inv_maps=inv, level='sub', dept=dept, group=group)
        dname = inv['dept'].get(str(dept), str(dept)) if dept else ''
        gname = inv['group'].get((str(dept), str(group)), str(group)) if group else ''
        title = f"MBRP — {dname} → {gname} — Días sin venta promedio por Subgrupo{rango_suffix}"
        _stats_update_breadcrumb(app)
        if chart_type == 'bar':
            _stats_render_bar(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        else:
            _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend)
        return

    # Nivel Producto dentro de un subgrupo
    if lvl == 'product':
        dept = state.get('dept')
        group = state.get('group')
        sub = state.get('sub')
        if not (dept and group and sub):
            state['level'] = 'sub'
            app.stats_pie_state = state
            app.mostrar_estadisticas()
            return

        product_days = {}
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
            dias = dias_map.get(code)
            if dias is None or dias < 0:
                continue
            product_days[code] = dias
            if code not in product_names:
                product_names[code] = name

        if not product_days:
            _stats_clear_container(app)
            dname = inv['dept'].get(str(dept), str(dept)) if dept else 'N/A'
            gname = inv['group'].get((str(dept), str(group)), str(group)) if group else 'N/A'
            sname = inv['sub'].get((str(dept), str(group), str(sub)), str(sub)) if sub else 'N/A'
            ttk.Label(app.graph_container, text=f"Sin datos de días sin venta por producto en {dname} / {gname} / {sname}.").pack(pady=10)
            return

        max_products = 25
        items = sorted(product_days.items(), key=lambda kv: kv[1], reverse=True)[:max_products]
        total = sum(v for _, v in items) or 1.0

        labels = []
        sizes = []
        meta = []
        legend = []
        hover_meta = {}
        for code, dias in items:
            full_name = product_names.get(code, code)
            name = str(full_name)
            max_len = 15
            if len(name) > max_len:
                name = name[:max_len]
            pct = (dias / total) * 100.0
            labels.append(f"{name}\n{dias:.0f} días ({pct:.1f}%)")
            sizes.append(dias)
            meta.append(code)
            legend.append((name, pct, float(dias)))
            hover_meta[str(code)] = {
                'full_name': str(full_name),
                'code': str(code),
                'dias': float(dias),
                'pct': float(pct),
            }

        dname = inv['dept'].get(str(dept), str(dept)) if dept else ''
        gname = inv['group'].get((str(dept), str(group)), str(group)) if group else ''
        sname = inv['sub'].get((str(dept), str(group), str(sub)), str(sub)) if sub else ''
        title = f"MBRP — {dname} → {gname} → {sname} — Top {len(items)} productos por días sin venta{rango_suffix}"
        _stats_update_breadcrumb(app)
        if chart_type == 'bar':
            _stats_render_bar(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend, hover_meta=hover_meta)
        else:
            _stats_render_pie(app, labels, sizes, title, on_pick_codes=meta, legend_rows=legend, hover_meta=hover_meta)
        return

def _stats_on_view_mode_change(app):
    """Maneja el cambio de modo de vista para mostrar/ocultar controles específicos."""
    view_mode_var = getattr(app, 'stats_view_mode_var', None)
    if view_mode_var is None:
        return
    
    sel = (view_mode_var.get() or '').strip()
    is_heatmap = 'Mapa de Calor' in sel or 'calor' in sel.lower()
    is_timeline = 'Comportamiento de Ventas' in sel or 'Línea de tiempo' in sel
    
    if hasattr(app, 'heatmap_controls_frame'):
        app.heatmap_controls_frame.pack_forget()
    if hasattr(app, 'timeline_controls_frame'):
        app.timeline_controls_frame.pack_forget()
        
    if is_heatmap:
        # Mostrar controles de mapa de calor
        app.heatmap_controls_frame.pack(fill=tk.X, pady=(8, 4))
        # Ocultar breadcrumb y botón volver
        if hasattr(app, 'stats_breadcrumb_var'):
            try:
                app.stats_breadcrumb_var.set("Mapa de Calor de Facturación")
            except:
                pass
        # Limpiar contenedor y mostrar mensaje instructivo
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text="Configure los parámetros y presione 'Generar Mapa'").pack(pady=20)
    elif is_timeline:
        # Mostrar controles de línea de tiempo
        app.timeline_controls_frame.pack(fill=tk.X, pady=(8, 4))
        if hasattr(app, 'stats_breadcrumb_var'):
            try:
                app.stats_breadcrumb_var.set("Comportamiento de Ventas")
            except:
                pass
        _stats_clear_container(app)
        ttk.Label(app.graph_container, text="Configure los parámetros y presione 'Generar Gráfico'").pack(pady=20)
    else:
        # Refrescar gráficos solo para otros modos
        getattr(app, 'mostrar_estadisticas', lambda: None)()

def _stats_compute_and_draw_heatmap(app):
    """Renderiza el mapa de calor de facturación por hora."""
    _stats_clear_container(app)
    
    try:
        # Obtener parámetros
        selected_sede = getattr(app, 'stats_heatmap_sede_var', None)
        if not selected_sede or not selected_sede.get():
            ttk.Label(app.graph_container, text="Seleccione una sede para generar el mapa de calor.").pack(pady=20)
            return
        
        metrica = getattr(app, 'stats_heatmap_metric_var', None)
        use_count = metrica and metrica.get() and "Conteo" in metrica.get()
        
        fecha_inicio = getattr(app, 'stats_heatmap_fecha_inicio', None)
        fecha_fin = getattr(app, 'stats_heatmap_fecha_fin', None)
        
        if not fecha_inicio or not fecha_fin:
            ttk.Label(app.graph_container, text="Seleccione las fechas para generar el mapa de calor.").pack(pady=20)
            return
        
        # Conectar a la sede
        sedes_config = app.db_manager.get_sedes_config()
        sede_info = next((s for s in sedes_config if s['nombre_sede'] == selected_sede.get()), None)
        
        if not sede_info:
            ttk.Label(app.graph_container, text="No se encontró la configuración de la sede.").pack(pady=20)
            return
        
        conn_sede = app.db_manager.connect_to_vad20_sede(sede_info)
        if not conn_sede:
            ttk.Label(app.graph_container, text="No se pudo conectar a la base de datos de la sede.").pack(pady=20)
            return
        
        # Obtener datos (sin filtro de clientes específicos)
        data = app.db_manager.get_client_heatmap_history(
            conn_sede, [], fecha_inicio.get_date(), fecha_fin.get_date()
        )
        conn_sede.close()
        
        if not data:
            ttk.Label(app.graph_container, text="No se encontraron datos para el período seleccionado.").pack(pady=20)
            return
        
        # Renderizar mapa de calor
        _stats_render_heatmap(app, data, use_count)
        
    except Exception as e:
        app.log(f"Error generando mapa de calor: {e}", "ERROR")
        ttk.Label(app.graph_container, text=f"Error: {e}").pack(pady=20)

def _stats_render_heatmap(app, data, use_count=False):
    """Renderiza el mapa de calor con los datos proporcionados."""
    _stats_clear_container(app)
    
    import numpy as np
    
    heatmap_data = np.zeros((7, 24))  # 7 días, 24 horas
    day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    
    total_valor = 0
    
    for row in data:
        rif, name, fecha, hora, total_usd = row
        if isinstance(fecha, str):
            try:
                from datetime import datetime
                fecha = datetime.strptime(fecha.split(' ')[0], '%Y-%m-%d')
            except:
                pass
        if hasattr(fecha, 'weekday'):
            day_idx = fecha.weekday()
            if 0 <= hora < 24:
                valor_a_sumar = 1 if use_count else total_usd
                heatmap_data[day_idx, hora] += valor_a_sumar
                total_valor += valor_a_sumar
    
    # Crear contenedor dividido
    container = ttk.Frame(app.graph_container)
    container.pack(fill=tk.BOTH, expand=True)
    
    left_panel = ttk.Frame(container)
    left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    right_panel = ttk.Frame(container, padding=(10, 0), width=250)
    right_panel.pack(side=tk.RIGHT, fill=tk.Y)
    right_panel.pack_propagate(False)
    
    # Crear figura
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    
    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    
    im = ax.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')
    
    ax.set_xticks(np.arange(24))
    ax.set_yticks(np.arange(7))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(day_names)
    
    ax.set_title("Mapa de Calor de Facturación (Por Día y Hora)", pad=20, fontsize=12, fontweight='bold')
    ax.set_xlabel("Hora del Día", fontsize=10)
    ax.set_ylabel("Día de la Semana", fontsize=10)
    
    label_color = "Cantidad de Facturas" if use_count else "Monto Facturado (USD)"
    fig.colorbar(im, ax=ax, label=label_color)
    
    canvas = FigureCanvasTkAgg(fig, master=left_panel)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    toolbar_frame = ttk.Frame(left_panel)
    toolbar_frame.pack(fill=tk.X)
    NavigationToolbar2Tk(canvas, toolbar_frame)
    
    # Panel derecho con resumen
    ttk.Label(right_panel, text="Resumen del Mapa", font=("Segoe UI", 12, "bold")).pack(pady=(15, 10), anchor=tk.W)
    
    if use_count:
        ttk.Label(right_panel, text=f"Total Registros: {int(total_valor)}").pack(pady=5, padx=10, anchor=tk.W)
    else:
        ttk.Label(right_panel, text=f"Total USD: ${total_valor:,.2f}").pack(pady=5, padx=10, anchor=tk.W)
    
    if total_valor > 0:
        max_val = np.max(heatmap_data)
        max_pos = np.unravel_index(np.argmax(heatmap_data), heatmap_data.shape)
        ttk.Label(right_panel, text=f"Pico: {day_names[max_pos[0]]} a las {max_pos[1]:02d}:00", foreground="#EF4444").pack(pady=5, padx=10, anchor=tk.W)
        if use_count:
            ttk.Label(right_panel, text=f"Max Facturas/Hora: {int(max_val)}").pack(pady=5, padx=10, anchor=tk.W)
        else:
            ttk.Label(right_panel, text=f"Max USD/Hora: ${max_val:,.2f}").pack(pady=5, padx=10, anchor=tk.W)

def setup_stats_tab(app):
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
        width=36,
        values=[
            "Jerarquía productos (Depto/Grupo/Sub)",
            "Distribución por Proveedor",
            "MBRP — Días sin venta (Depto/Grupo/Sub)",
            "Mapa de Calor (Facturación por Hora)",
            "Comportamiento de Ventas (Línea de tiempo)"
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
    view_mode_combo.bind('<<ComboboxSelected>>', lambda e: _stats_on_view_mode_change(app))

    # Controles de mapa de calor (inicialmente ocultos, en la barra superior)
    app.heatmap_controls_frame = ttk.Frame(top_bar)
    
    # Sede
    ttk.Label(app.heatmap_controls_frame, text="Sede:").pack(side=tk.LEFT, padx=(0, 5))
    app.stats_heatmap_sede_var = tk.StringVar()
    app.stats_heatmap_sede_combo = ttk.Combobox(app.heatmap_controls_frame, textvariable=app.stats_heatmap_sede_var, state='readonly', width=15)
    app.stats_heatmap_sede_combo.pack(side=tk.LEFT, padx=(0, 10))
    
    # Métrica
    ttk.Label(app.heatmap_controls_frame, text="Métrica:").pack(side=tk.LEFT, padx=(0, 5))
    app.stats_heatmap_metric_var = tk.StringVar(value="Monto (USD)")
    app.stats_heatmap_metric_combo = ttk.Combobox(
        app.heatmap_controls_frame, 
        textvariable=app.stats_heatmap_metric_var,
        state='readonly',
        width=10,
        values=["Monto (USD)", "Conteo (Facturas)"]
    )
    app.stats_heatmap_metric_combo.pack(side=tk.LEFT, padx=(0, 10))
    
    # Fechas
    from tkcalendar import DateEntry
    from datetime import datetime, timedelta
    
    def set_date_range(days):
        """Establece el rango de fechas según los días seleccionados"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        app.stats_heatmap_fecha_fin.set_date(end_date)
        app.stats_heatmap_fecha_inicio.set_date(start_date)
    
    # Combobox de selección rápida de días
    ttk.Label(app.heatmap_controls_frame, text="Rango:").pack(side=tk.LEFT, padx=(0, 5))
    app.stats_heatmap_range_var = tk.StringVar(value="30 días")
    app.stats_heatmap_range_combo = ttk.Combobox(
        app.heatmap_controls_frame,
        textvariable=app.stats_heatmap_range_var,
        state='readonly',
        width=10,
        values=["1 día", "7 días", "15 días", "30 días", "60 días"]
    )
    app.stats_heatmap_range_combo.pack(side=tk.LEFT, padx=(0, 10))
    app.stats_heatmap_range_combo.bind('<<ComboboxSelected>>', lambda e: set_date_range(int(app.stats_heatmap_range_var.get().split()[0])))
    
    ttk.Label(app.heatmap_controls_frame, text="Desde:").pack(side=tk.LEFT, padx=(0, 5))
    default_start = datetime.now() - timedelta(days=30)
    app.stats_heatmap_fecha_inicio = DateEntry(
        app.heatmap_controls_frame, width=10, background='#004C97', foreground='white',
        date_pattern='dd/mm/yyyy', year=default_start.year, month=default_start.month, day=default_start.day
    )
    app.stats_heatmap_fecha_inicio.pack(side=tk.LEFT, padx=(0, 5))
    
    ttk.Label(app.heatmap_controls_frame, text="Hasta:").pack(side=tk.LEFT, padx=(0, 5))
    app.stats_heatmap_fecha_fin = DateEntry(
        app.heatmap_controls_frame, width=10, background='#004C97', foreground='white',
        date_pattern='dd/mm/yyyy'
    )
    app.stats_heatmap_fecha_fin.pack(side=tk.LEFT, padx=(0, 10))
    
    # Botón generar
    ttk.Button(
        app.heatmap_controls_frame,
        text="Generar",
        command=lambda: _stats_compute_and_draw_heatmap(app)
    ).pack(side=tk.LEFT, padx=(0, 5))
    
    # Ocultar controles de mapa de calor inicialmente
    app.heatmap_controls_frame.pack_forget()

    # === Controles de Línea de Tiempo ===
    app.timeline_controls_frame = ttk.Frame(top_bar)
    
    ttk.Label(app.timeline_controls_frame, text="Sede:").pack(side=tk.LEFT, padx=(0, 5))
    app.stats_timeline_sede_var = tk.StringVar(value="00 - ICH")
    app.stats_timeline_sede_combo = ttk.Combobox(app.timeline_controls_frame, textvariable=app.stats_timeline_sede_var, state='readonly', width=15)
    app.stats_timeline_sede_combo.pack(side=tk.LEFT, padx=(0, 10))
    
    ttk.Label(app.timeline_controls_frame, text="Métrica:").pack(side=tk.LEFT, padx=(0, 5))
    app.stats_timeline_metric_var = tk.StringVar(value="Unidades Netas")
    app.stats_timeline_metric_combo = ttk.Combobox(app.timeline_controls_frame, textvariable=app.stats_timeline_metric_var, state='readonly', width=15, values=["Unidades Netas", "Monto (USD)"])
    app.stats_timeline_metric_combo.pack(side=tk.LEFT, padx=(0, 10))
    
    ttk.Label(app.timeline_controls_frame, text="Desde:").pack(side=tk.LEFT, padx=(0, 5))
    app.stats_timeline_fecha_inicio = DateEntry(app.timeline_controls_frame, width=10, background='#004C97', foreground='white', date_pattern='dd/mm/yyyy', year=default_start.year, month=default_start.month, day=default_start.day)
    app.stats_timeline_fecha_inicio.pack(side=tk.LEFT, padx=(0, 5))
    
    ttk.Label(app.timeline_controls_frame, text="Hasta:").pack(side=tk.LEFT, padx=(0, 5))
    app.stats_timeline_fecha_fin = DateEntry(app.timeline_controls_frame, width=10, background='#004C97', foreground='white', date_pattern='dd/mm/yyyy')
    app.stats_timeline_fecha_fin.pack(side=tk.LEFT, padx=(0, 10))
    
    ttk.Button(app.timeline_controls_frame, text="Generar Gráfico", command=lambda: _stats_compute_and_draw_timeline(app)).pack(side=tk.LEFT, padx=(0, 5))
    
    app.timeline_controls_frame.pack_forget()
    
    # Cargar sedes compartidas — formato "01 - Barinas" para extraer código fácilmente
    _CODIGO_A_NOMBRE_SEDE = {v: k.capitalize() for k, v in _SEDE_NOMBRE_A_CODIGO.items()}
    try:
        sedes_config = app.db_manager.get_sedes_config()
        sede_nombres = [s['nombre_sede'] for s in sedes_config]
        app.stats_heatmap_sede_combo['values'] = sede_nombres
        if sede_nombres:
            app.stats_heatmap_sede_combo.current(0)
        
        # Para timeline construir etiquetas con código: "01 - Barinas", "03 - Cabudare", ...
        timeline_vals = ["00 - ICH"]
        for nombre in sede_nombres:
            cod = _SEDE_NOMBRE_A_CODIGO.get(nombre.lower())
            if cod:
                timeline_vals.append(f"{cod} - {nombre}")
            else:
                timeline_vals.append(nombre)
        app.stats_timeline_sede_combo['values'] = timeline_vals
        app.stats_timeline_sede_combo.current(0)
    except Exception as e:
        app.log(f"Error cargando sedes para controles: {e}", "ERROR")

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
