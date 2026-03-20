import tkinter as tk
from tkinter import ttk, messagebox
import logging
import threading

from typing import Optional, List, Dict, Any

logger = logging.getLogger("ABASTECIMIENTO_UI")

class AbastecimientoTab(ttk.Frame):
    def __init__(self, parent, app_instance):
        super().__init__(parent)
        self.app = app_instance
        self.db_manager = app_instance.db_manager
        self.config_manager = app_instance.config_manager
        
        # Initialize attributes with type hints
        self.sede_var = tk.StringVar()
        self.notebook: Optional[ttk.Notebook] = None
        self.tab_abastecimiento: Optional[ttk.Frame] = None
        self.tab_autorizaciones: Optional[ttk.Frame] = None
        self.tab_pendientes: Optional[ttk.Frame] = None
        self.tree: Optional[ttk.Treeview] = None
        self.tree_auto: Optional[ttk.Treeview] = None
        self.tree_pend: Optional[ttk.Treeview] = None
        self.sede_combo: Optional[ttk.Combobox] = None
        self.btn_calc: Optional[ttk.Button] = None
        self.btn_export: Optional[ttk.Button] = None
        self.btn_roja: Optional[ttk.Button] = None
        self.progress: Optional[ttk.Progressbar] = None
        self.calculando = False
        self.last_sugerencias: List[Dict[str, Any]] = []
        self.last_sede_destino: str = ""
        
        # Paginación
        self.current_page = 1
        self.page_size = 250
        self.total_pages = 1
        self.filtered_results: List[Dict[str, Any]] = []
        
        # Variables de filtros
        self.dept_var = tk.StringVar(value="Todos")
        self.group_var = tk.StringVar(value="Todos")
        self.sub_var = tk.StringVar(value="Todos")
        self.dept_combo: Optional[ttk.Combobox] = None
        self.group_combo: Optional[ttk.Combobox] = None
        self.sub_combo: Optional[ttk.Combobox] = None
        
        # Búsqueda por texto
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._aplicar_filtro_local())
        self.ocultar_sin_cdt_var = tk.BooleanVar(value=False)
        
        self._setup_ui()
        
    def _setup_ui(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(header, text="📦 Planeación de Abastecimiento", font=("Helvetica", 16, "bold")).pack(side="left")
        
        # Configuration Button
        self.btn_config = ttk.Button(header, text="⚙️ Configurar Parámetros", command=self.on_configurar)
        self.btn_config.pack(side="right", padx=10)
        
        # Notebook for Sub-modules
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_subtab_changed)
        
        # Tab 1: Abastecimiento
        self.tab_abastecimiento = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_abastecimiento, text="Abastecimiento")
        self._setup_tab_abastecimiento(self.tab_abastecimiento)
        
        # Tab 2: Autorizaciones
        self.tab_autorizaciones = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_autorizaciones, text="Autorizaciones")
        self._setup_tab_autorizaciones(self.tab_autorizaciones)
        
        # Tab 3: Pendientes de Procesar
        self.tab_pendientes = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_pendientes, text="Pendientes de Procesar")
        self._setup_tab_pendientes(self.tab_pendientes)

    def _on_subtab_changed(self, event=None):
        try:
            current_tab = self.notebook.tab(self.notebook.select(), "text")
            if current_tab == "Autorizaciones":
                self.refresh_autorizaciones()
            elif current_tab == "Pendientes de Procesar":
                self.refresh_pendientes()
        except:
            pass

    def _setup_tab_abastecimiento(self, parent_frame):
        # Controls
        controls = ttk.Frame(parent_frame)
        controls.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(controls, text="Sede Destino:").pack(side="left")
        
        # Cargar sedes dinámicas desde ConfigManager
        sedes_data = self.config_manager.get_sedes_config()
        sedes_list = ["ICH (Todas las sedes)"] + [f"{s} - {sedes_data[s].get('descripcion', '')}" for s in sedes_data.keys()]
        
        self.sede_combo = ttk.Combobox(controls, textvariable=self.sede_var, values=sedes_list, state="readonly", width=40)
        self.sede_combo.pack(side="left", padx=5)
        
        self.btn_calc = ttk.Button(controls, text="Calcular Sugerencias", command=self.on_calcular)
        self.btn_calc.pack(side="left", padx=10)

        # Progress bar (hidden by default)
        self.progress = ttk.Progressbar(controls, mode="indeterminate", length=150)
        
        # Filtros Avanzados Frame
        filter_frame = ttk.Frame(parent_frame)
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        # Department
        ttk.Label(filter_frame, text="Depto:").pack(side="left", padx=5)
        self.dept_combo = ttk.Combobox(filter_frame, textvariable=self.dept_var, state="readonly", width=15)
        self.dept_combo['values'] = ["Todos"]
        self.dept_combo.pack(side="left", padx=5)
        
        # Group
        ttk.Label(filter_frame, text="Grupo:").pack(side="left", padx=5)
        self.group_combo = ttk.Combobox(filter_frame, textvariable=self.group_var, state="readonly", width=15)
        self.group_combo['values'] = ["Todos"]
        self.group_combo.pack(side="left", padx=5)
        
        # Subgroup
        ttk.Label(filter_frame, text="Subgrupo:").pack(side="left", padx=5)
        self.sub_combo = ttk.Combobox(filter_frame, textvariable=self.sub_var, state="readonly", width=15)
        self.sub_combo['values'] = ["Todos"]
        self.sub_combo.pack(side="left", padx=5)
        
        # Bindings
        self.dept_combo.bind('<<ComboboxSelected>>', self.on_dept_selected)
        self.group_combo.bind('<<ComboboxSelected>>', self.on_group_selected)
        self.sub_combo.bind('<<ComboboxSelected>>', lambda e: self._aplicar_filtro_local())

        # Search Bar
        search_frame = ttk.Frame(parent_frame)
        search_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(search_frame, text="🔍 Buscar:").pack(side="left", padx=5)
        self.ent_search = ttk.Entry(search_frame, textvariable=self.search_var)
        self.ent_search.pack(side="left", fill="x", expand=True, padx=5)
        
        ttk.Checkbutton(
            search_frame,
            text="Ocultar sin stock CDT",
            variable=self.ocultar_sin_cdt_var,
            command=self._aplicar_filtro_local
        ).pack(side="left", padx=10)
        
        # Treeview
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Añadimos columna 'sel' al inicio para el checkbox
        columns = ("sel", "producto", "descripcion", "destino", "origen", "cantidad", "stock_dest", "autorizacion")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        self.tree.heading("sel", text="[ ]")
        self.tree.heading("producto", text="Código")
        self.tree.heading("descripcion", text="Descripción")
        self.tree.heading("destino", text="Sede Destino")
        self.tree.heading("origen", text="Sede Origen (CDT)")
        self.tree.heading("cantidad", text="Cant. Sugerida")
        self.tree.heading("stock_dest", text="Stock Destino")
        self.tree.heading("autorizacion", text="Requiere Aut.")
        
        self.tree.column("sel", width=35, anchor="center")
        self.tree.column("producto", width=100)
        self.tree.column("descripcion", width=250)
        self.tree.column("destino", width=100)
        self.tree.column("origen", width=90)
        self.tree.column("cantidad", width=90)
        self.tree.column("stock_dest", width=90)
        self.tree.column("autorizacion", width=90)
        
        # Toggle checkbox on click
        self.tree.bind("<Button-1>", self._on_tree_click)
        
        self.tree.pack(side="left", fill="both", expand=True)

        # Controles de paginación
        pag_frame = ttk.Frame(parent_frame)
        pag_frame.pack(fill="x", padx=10, pady=5)

        self.btn_prev = ttk.Button(pag_frame, text="◄ Anterior", width=10, command=lambda: self.on_cambiar_pagina(-1), state='disabled')
        self.btn_prev.pack(side="left")

        self.lbl_pagina = ttk.Label(pag_frame, text="Página 1/1", width=15)
        self.lbl_pagina.pack(side="left", padx=10)

        self.btn_next = ttk.Button(pag_frame, text="Siguiente ►", width=10, command=lambda: self.on_cambiar_pagina(1), state='disabled')
        self.btn_next.pack(side="left")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        if self.tree and scrollbar:
            self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        
        # Configurar colores para estados especiales
        self.tree.tag_configure('rojo', background='#ffcccc')      # Rojo suave para lista roja
        self.tree.tag_configure('sin_stock', background='#e0b0ff') # Púrpura suave para sin stock CDT
        self.tree.tag_configure('ajustado', background='#fff9c4')  # Amarillo suave para stock ajustado (proporcional)
        
        # Footer Actions
        footer = ttk.Frame(parent_frame)
        footer.pack(fill="x", padx=10, pady=10)
        
        btn_sel_all = ttk.Button(footer, text="☑ Seleccionar Todos", command=lambda: self._select_all(True))
        btn_sel_all.pack(side="left", padx=5)
        
        btn_unsel_all = ttk.Button(footer, text="☐ Deseleccionar Todos", command=lambda: self._select_all(False))
        btn_unsel_all.pack(side="left", padx=5)

        ttk.Button(footer, text="🚀 Procesar Sugerencias", command=self.on_procesar).pack(side="right", padx=5)
        self.btn_export = ttk.Button(footer, text="📊 Exportar a Excel", command=self.on_exportar)
        self.btn_export.pack(side="right", padx=5)
        
        # Button for "Red List"
        self.btn_roja = ttk.Button(footer, text="🚫 Productos No Trasladables", command=self.on_gestionar_roja)
        self.btn_roja.pack(side="left", padx=5)

    def _setup_tab_autorizaciones(self, parent_frame):
        ttk.Label(parent_frame, text="Módulo de Autorizaciones no implementado aún.", font=("Helvetica", 12)).pack(pady=50)

    def on_gestionar_roja(self):
        # UI for managing "Red List" products
        self.modal_roja = tk.Toplevel(self)
        self.modal_roja.title("Productos No Trasladables")
        self.modal_roja.geometry("600x450")
        self.modal_roja.transient(self)
        self.modal_roja.grab_set()

        ttk.Label(self.modal_roja, text="Gestión de Productos No Trasladables (Lista Roja)", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        ttk.Label(self.modal_roja, text="Esta función permite bloquear transferencias de productos específicos.", wraplength=450).pack(pady=5)
        
        # Tools Frame (Botones)
        tools_frame = ttk.Frame(self.modal_roja)
        tools_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(tools_frame, text="➕ Agregar Producto", command=self.on_add_roja).pack(side="left", padx=5)
        ttk.Button(tools_frame, text="❌ Remover Seleccionado", command=self.on_remove_roja).pack(side="left", padx=5)
        
        # Basic layout
        frame = ttk.Frame(self.modal_roja)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Columns
        columns = ("id", "producto", "destino", "motivo", "fecha")
        self.tree_roja = ttk.Treeview(frame, columns=columns, show="headings")
        self.tree_roja.heading("id", text="ID")
        self.tree_roja.heading("producto", text="Código Producto")
        self.tree_roja.heading("destino", text="Sede Destino")
        self.tree_roja.heading("motivo", text="Motivo")
        self.tree_roja.heading("fecha", text="Fecha")
        
        self.tree_roja.column("id", width=30, stretch=False)
        self.tree_roja.column("producto", width=100)
        self.tree_roja.column("destino", width=100)
        self.tree_roja.column("motivo", width=200)
        self.tree_roja.column("fecha", width=120)
        
        self.tree_roja.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree_roja.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree_roja.configure(yscrollcommand=scrollbar.set)

        bottom_frame = ttk.Frame(self.modal_roja)
        bottom_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(bottom_frame, text="Cerrar", command=self.modal_roja.destroy).pack(side="right")
        
        self.cargar_datos_roja()

    def cargar_datos_roja(self):
        from pal.services.abastecimiento import AbastecimientoService
        service = AbastecimientoService(self.app.db_manager)
        datos = service.get_red_list()
        
        for item in self.tree_roja.get_children():
            self.tree_roja.delete(item)
            
        for row in datos:
            # row: id, producto_codigo, sede_destino, motivo, fecha_registro
            id_reg, prod, dest, motiv, fecha = row
            dest_str = dest if dest else "TODAS"
            self.tree_roja.insert("", "end", values=(id_reg, prod, dest_str, motiv, fecha))

    def on_add_roja(self):
        add_modal = tk.Toplevel(self.modal_roja)
        add_modal.title("Agregar Producto No Trasladable")
        add_modal.geometry("400x300")
        add_modal.transient(self.modal_roja)
        add_modal.grab_set()

        ttk.Label(add_modal, text="Agregar a Lista Roja", font=("Helvetica", 12, "bold")).pack(pady=10)

        form = ttk.Frame(add_modal)
        form.pack(fill="both", expand=True, padx=20, pady=10)

        # Producto
        ttk.Label(form, text="Código Producto:").grid(row=0, column=0, sticky="w", pady=5)
        ent_prod = ttk.Entry(form, width=20)
        ent_prod.grid(row=0, column=1, sticky="w", pady=5)

        # Destino
        ttk.Label(form, text="Sede Destino:").grid(row=1, column=0, sticky="w", pady=5)
        sedes_data = self.config_manager.get_sedes_config()
        sedes_list = ["TODAS"] + [str(s) for s in sedes_data.keys()]
        combo_dest = ttk.Combobox(form, values=sedes_list, state="readonly", width=18)
        combo_dest.set("TODAS")
        combo_dest.grid(row=1, column=1, sticky="w", pady=5)

        # Motivo
        ttk.Label(form, text="Motivo:").grid(row=2, column=0, sticky="nw", pady=5)
        txt_motivo = tk.Text(form, width=25, height=4)
        txt_motivo.grid(row=2, column=1, sticky="w", pady=5)

        def save():
            prod = ent_prod.get().strip()
            dest = combo_dest.get()
            dest_val = None if dest == "TODAS" else dest
            motivo = txt_motivo.get("1.0", "end-1c").strip()

            if not prod:
                messagebox.showerror("Error", "El código de producto es requerido.", parent=add_modal)
                return

            from pal.services.abastecimiento import AbastecimientoService
            service = AbastecimientoService(self.app.db_manager)
            success = service.add_to_red_list(prod, dest_val, motivo)
            if success:
                messagebox.showinfo("Éxito", "Producto agregado a la lista roja.", parent=add_modal)
                self.cargar_datos_roja()
                add_modal.destroy()
            else:
                messagebox.showerror("Error", "No se pudo agregar el producto.", parent=add_modal)

        btn_frame = ttk.Frame(add_modal)
        btn_frame.pack(fill="x", padx=20, pady=10)
        ttk.Button(btn_frame, text="Cancelar", command=add_modal.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Guardar", command=save).pack(side="right", padx=5)

    def on_remove_roja(self):
        selection = self.tree_roja.selection()
        if not selection:
            messagebox.showwarning("Atención", "Seleccione un producto para remover.", parent=self.modal_roja)
            return
            
        item = self.tree_roja.item(selection[0])
        id_reg = item['values'][0]
        prod = item['values'][1]
        
        if messagebox.askyesno("Confirmar", f"¿Está seguro de remover el producto {prod} de la lista roja?", parent=self.modal_roja):
            from pal.services.abastecimiento import AbastecimientoService
            service = AbastecimientoService(self.app.db_manager)
            if service.remove_from_red_list(id_reg):
                self.cargar_datos_roja()
            else:
                messagebox.showerror("Error", "No se pudo remover el producto.", parent=self.modal_roja)

    def on_dept_selected(self, event=None):
        dept = self.dept_var.get()
        if not self.group_combo or not self.sub_combo: return
        
        if dept == 'Todos':
            self.group_combo['values'] = ['Todos']
            self.group_var.set('Todos')
            self.sub_combo['values'] = ['Todos']
            self.sub_var.set('Todos')
            return
            
        dept_cod = self.app.tra_dept_dict.get(dept)
        if dept_cod and hasattr(self.app, 'tra_group_dict'):
            grupos = self.app.tra_group_dict.get(dept_cod, {})
            self.group_combo['values'] = ['Todos'] + list(grupos.keys())
            self.group_var.set('Todos')
            
            # Reset subgrupos
            self.sub_combo['values'] = ['Todos']
            self.sub_var.set('Todos')

    def on_group_selected(self, event=None):
        dept = self.dept_var.get()
        group = self.group_var.get()
        if not self.sub_combo: return
        
        if group == 'Todos' or dept == 'Todos':
            self.sub_combo['values'] = ['Todos']
            self.sub_var.set('Todos')
            return
            
        dept_cod = self.app.tra_dept_dict.get(dept)
        if dept_cod and hasattr(self.app, 'tra_group_dict'):
            grupos = self.app.tra_group_dict.get(dept_cod, {})
            group_cod = grupos.get(group)
            
            if group_cod and hasattr(self.app, 'tra_sub_dict'):
                key = f"{dept_cod}|{group_cod}"
                subgrupos = self.app.tra_sub_dict.get(key, {})
                self.sub_combo['values'] = ['Todos'] + list(subgrupos.keys())
                self.sub_var.set('Todos')

    def _on_tree_click(self, event):
        """Maneja el clic en la columna de selección."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#1": # Columna 'sel'
                item_id = self.tree.identify_row(event.y)
                if item_id:
                    self._toggle_selection(item_id)

    def _toggle_selection(self, item_id):
        """Cambia el estado del checkbox para un item."""
        values = list(self.tree.item(item_id, "values"))
        current = values[0]
        # Usamos caracteres Unicode para simular checkbox
        new_val = "☑" if current == "☐" else "☐"
        values[0] = new_val
        self.tree.item(item_id, values=values)
        
        # Actualizar en la lista original (filtered_results) para persistencia al paginar
        codigo = values[1]
        destino = values[3]
        for item in self.filtered_results:
            if item.get("producto_codigo") == codigo and item.get("sucursal_destino") == destino:
                item["_seleccionado"] = (new_val == "☑")
                break

    def _select_all(self, state):
        """Selecciona o deselecciona todos los elementos FILTRADOS."""
        char = "☑" if state else "☐"
        for item in self.filtered_results:
            item["_seleccionado"] = state
        
        # Actualizar visualmente la página actual
        for item_id in self.tree.get_children():
            values = list(self.tree.item(item_id, "values"))
            values[0] = char
            self.tree.item(item_id, values=values)

    def on_calcular(self):
        if self.calculando:
            return

        sede_full = self.sede_var.get()
        if not sede_full:
            messagebox.showwarning("Atención", "Seleccione una sede destino o Cálculo Global.")
            return
        
        is_global = "ICH" in sede_full or "GLOBAL" in sede_full
        sede = "GLOBAL" if is_global else sede_full.split(" - ")[0]
        
        # Bloquear UI
        self.calculando = True
        if self.btn_calc: self.btn_calc.config(state="disabled")
        if self.sede_combo: self.sede_combo.config(state="disabled")
        if self.btn_export: self.btn_export.config(state="disabled")
        
        if self.progress:
            self.progress.pack(side="left", padx=5)
            self.progress.start()
        
        # Limpiar treeview previo
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        # Iniciar hilo de cálculo
        threading.Thread(target=self._bg_calcular, args=(sede, is_global), daemon=True).start()

    def _bg_calcular(self, sede, is_global=False):
        """Lógica de cálculo en hilo secundario."""
        try:
            from pal.services.abastecimiento import AbastecimientoService
            service = AbastecimientoService(self.app.db_manager)
            
            # Extract codes to pass to service
            dept_cod = None
            group_cod = None
            sub_cod = None
            
            dept = self.dept_var.get()
            group = self.group_var.get()
            sub = self.sub_var.get()
            
            if dept != 'Todos' and hasattr(self.app, 'tra_dept_dict'):
                dept_cod = self.app.tra_dept_dict.get(dept)
                
            if dept_cod and group != 'Todos' and hasattr(self.app, 'tra_group_dict'):
                grupos = self.app.tra_group_dict.get(dept_cod, {})
                group_cod = grupos.get(group)
                
            if dept_cod and group_cod and sub != 'Todos' and hasattr(self.app, 'tra_sub_dict'):
                key = f"{dept_cod}|{group_cod}"
                subgrupos = self.app.tra_sub_dict.get(key, {})
                sub_cod = subgrupos.get(sub)

            # Pass filters to service
            if is_global:
                sugerencias = service.calcular_abastecimiento_global(dept_cod=dept_cod, group_cod=group_cod, sub_cod=sub_cod)
            else:
                sugerencias = service.calcular_sugerencias(sede, dept_cod=dept_cod, group_cod=group_cod, sub_cod=sub_cod)
            
            # Inicializar estado de selección
            for s in sugerencias:
                s["_seleccionado"] = True # Por defecto seleccionados todos
            
            # Notificar a la UI para actualizar
            self.after(0, lambda: self._finalizar_calculo(sugerencias, sede))
        except Exception as e:
            logger.error(f"Error en hilo de abastecimiento: {e}")
            import traceback
            traceback.print_exc()
            self.after(0, lambda: self._finalizar_calculo([], sede, error=str(e)))

    def _finalizar_calculo(self, sugerencias, sede, error=None):
        """Actualiza la UI con los resultados del hilo secundario."""
        try:
            if self.progress:
                self.progress.stop()
                self.progress.pack_forget()
            
            if error:
                messagebox.showerror("Error", f"Ocurrió un error durante el cálculo: {error}")
                self.calculando = False
                if self.btn_calc: self.btn_calc.config(state="normal")
                if self.sede_combo: self.sede_combo.config(state="normal")
                if self.btn_export: self.btn_export.config(state="normal")
                return

            self.last_sugerencias = sugerencias
            self.last_sede_destino = sede
            
            # Resetear búsqueda local para mostrar todos los resultados de la nueva consulta
            self.search_var.set("")
            
            # Aplicar filtro inicial (que disparará la paginación)
            self._aplicar_filtro_local()
            
            self.app.log(f"Se encontraron {len(sugerencias)} sugerencias para {sede}", "INFO")

        except Exception as e:
            logger.error(f"Error actualizando UI de abastecimiento: {e}", exc_info=True)
            messagebox.showerror("Error UI", f"No se pudieron mostrar los resultados: {e}")
        finally:
            self.calculando = False
            if self.btn_calc: self.btn_calc.config(state="normal")
            if self.sede_combo: self.sede_combo.config(state="normal")
            if self.btn_export: self.btn_export.config(state="normal")

    def _aplicar_filtro_local(self):
        """Aplica filtro de búsqueda por texto a los resultados cargados."""
        if not hasattr(self, 'last_sugerencias') or not self.last_sugerencias:
            return
            
        texto = self.search_var.get().lower().strip()
        
        # Filtrar por texto
        if not texto:
            self.filtered_results = list(self.last_sugerencias)
        else:
            self.filtered_results = [
                s for s in self.last_sugerencias 
                if texto in str(s.get("producto_codigo", "")).lower() or 
                   texto in str(s.get("producto_descripcion", "")).lower()
            ]
        
        # Filtrar por CDT si el checkbox está activo
        if self.ocultar_sin_cdt_var.get():
            self.filtered_results = [
                s for s in self.filtered_results
                if s.get("sucursal_origen_sugerida") != "SIN STOCK CDT"
            ]
            
        # Resetear a la primera página tras filtrar
        self.current_page = 1
        self._actualizar_paginacion()

    def on_cambiar_pagina(self, delta):
        """Maneja el cambio de página."""
        nueva_pag = self.current_page + delta
        if 1 <= nueva_pag <= self.total_pages:
            self.current_page = nueva_pag
            self._actualizar_paginacion()

    def _actualizar_paginacion(self):
        """Actualiza el Treeview con los datos de la página actual."""
        if not self.tree:
            return

        import math
        total_items = len(self.filtered_results)
        self.total_pages = max(1, math.ceil(total_items / self.page_size))
        
        # Asegurar página válida
        self.current_page = max(1, min(self.current_page, self.total_pages))
        
        # UI Feedback
        if hasattr(self, 'lbl_pagina') and self.lbl_pagina:
            self.lbl_pagina.config(text=f"Página {self.current_page}/{self.total_pages}")
        
        if hasattr(self, 'btn_prev') and self.btn_prev:
            self.btn_prev.config(state='normal' if self.current_page > 1 else 'disabled')
        if hasattr(self, 'btn_next') and self.btn_next:
            self.btn_next.config(state='normal' if self.current_page < self.total_pages else 'disabled')
            
        # Limpiar treeview
        self.tree.delete(*self.tree.get_children())
        
        # Obtener rebanada (slice)
        inicio = (self.current_page - 1) * self.page_size
        fin = inicio + self.page_size
        pagina_datos = self.filtered_results[inicio:fin]
        
        for s in pagina_datos:
            tags = []
            if s.get("es_rojo"): tags.append("rojo")
            if s.get("sucursal_origen_sugerida") == "SIN STOCK CDT": tags.append("sin_stock")
            if s.get("ajustado"): tags.append("ajustado")

            sel_char = "☑" if s.get("_seleccionado", True) else "☐"
            
            # Formatear Sede Origen: "Stock / Depósito"
            origen_base = s.get("sucursal_origen_sugerida", "")
            stock_org = s.get("stock_origen", 0)
            if origen_base and origen_base != "SIN STOCK CDT":
                origen_display = f"{int(stock_org)} / {origen_base}"
            else:
                origen_display = origen_base

            self.tree.insert("", "end", values=(
                sel_char,
                s["producto_codigo"],
                s.get("producto_descripcion", ""),
                s.get("sucursal_destino", ""),
                origen_display,
                s["cantidad_sugerida"],
                s["stock_actual"],
                "Sí" if s["requiere_autorizacion"] else "No"
            ), tags=tags)

    def on_exportar(self):
        if not hasattr(self, 'last_sugerencias') or not self.last_sugerencias:
            messagebox.showwarning("Atención", "No hay sugerencias calculadas para exportar.")
            return

        from tkinter import filedialog
        from datetime import datetime
        
        default_name = f"Abastecimiento_{self.last_sede_destino}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=default_name
        )
        
        if not filename:
            return

        try:
            from pal.services.exports import export_abastecimiento_excel
            export_abastecimiento_excel(filename, self.last_sugerencias, self.last_sede_destino)
            messagebox.showinfo("Éxito", f"Reporte exportado correctamente a:\n{filename}")
        except Exception as e:
            logger.error(f"Error exportando a Excel: {e}")
            messagebox.showerror("Error", f"No se pudo exportar el reporte: {e}")

    def on_procesar(self):
        """Guarda SOLO las sugerencias SELECCIONADAS en la base de datos."""
        # Obtener lista de seleccionadas desde last_sugerencias
        seleccionadas = [s for s in self.last_sugerencias if s.get("_seleccionado", True)]

        if not seleccionadas:
            messagebox.showwarning("Atención", "No hay sugerencias seleccionadas para procesar.")
            return
            
        if not messagebox.askyesno("Confirmar", f"¿Desea procesar y guardar las {len(seleccionadas)} sugerencias seleccionadas?"):
            return
            
        try:
            from pal.services.abastecimiento import AbastecimientoService
            service = AbastecimientoService(self.app.db_manager)
            
            if service.save_sugerencias(seleccionadas):
                messagebox.showinfo("Éxito", f"{len(seleccionadas)} sugerencias guardadas correctamente.")
                
                # Remover las seleccionadas de la lista actual para que no aparezcan de nuevo si el usuario sigue trabajando
                self.last_sugerencias = [s for s in self.last_sugerencias if not s.get("_seleccionado", False)]
                self._aplicar_filtro_local()
            else:
                messagebox.showerror("Error", "Error al guardar sugerencias. Revise los detalles en los logs.")
        except Exception as e:
            logger.error(f"Error en on_procesar: {e}")
            messagebox.showerror("Error", f"Error inesperado procesando sugerencias: {e}")

    def on_configurar(self):
        """Abre ventana para configurar días de stock y umbral de autorización."""
        sub = tk.Toplevel(self.app.root)
        sub.title("Configuración de Abastecimiento")
        sub.geometry("400x300")
        sub.transient(self.app.root)
        sub.grab_set()

        from pal.services.abastecimiento import AbastecimientoService
        service = AbastecimientoService(self.app.db_manager)
        
        # Cargar parámetros actuales (Global)
        params = service.obtener_parametros()
        # Buscar el registro global (categoria_id is None)
        global_params = next((p for p in params if p[0] is None), (None, 7, 50, 10, 365))
        
        tk.Label(sub, text="Configuración Global", font=("Segoe UI", 12, "bold")).pack(pady=10)

        frame = tk.Frame(sub, padx=20, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Días de Stock Objetivo (Inventario):").grid(row=0, column=0, sticky=tk.W, pady=5)
        var_dias = tk.StringVar(value=str(global_params[1]))
        ent_dias = tk.Entry(frame, textvariable=var_dias, width=10)
        ent_dias.grid(row=0, column=1, pady=5)

        lbl_status_tag = tk.Label(frame, text="", font=("Segoe UI", 9, "bold"))
        lbl_status_tag.grid(row=0, column=2, padx=10, sticky="w")

        def update_status_tag(*args):
            try:
                val = int(var_dias.get())
                if val < 25:
                    txt, col = "Posible quiebre", "#d32f2f"
                elif 25 <= val <= 59:
                    txt, col = "Alerta Compra", "#ff9800"
                elif 60 <= val <= 90:
                    txt, col = "Optimo", "#4caf50"
                elif 91 <= val <= 119:
                    txt, col = "Critico", "#e53935"
                else:
                    txt, col = "Sobre Stock", "#9c27b0"
                lbl_status_tag.config(text=f"({txt})", fg=col)
            except:
                lbl_status_tag.config(text="")

        var_dias.trace_add("write", update_status_tag)
        update_status_tag()

        tk.Label(frame, text="Umbral Autorización (Cantidad Máx):").grid(row=1, column=0, sticky=tk.W, pady=5)
        var_auto = tk.StringVar(value=str(global_params[3]))
        tk.Entry(frame, textvariable=var_auto, width=10).grid(row=1, column=1, pady=5)

        def save():
            try:
                d = int(var_dias.get())
                a = float(var_auto.get())
                # Mantener los otros valores por defecto al guardar el global
                if service.save_parametro(None, d, 50, a, 365):
                    self.app.log("Configuración guardada exitosamente.", "SUCCESS")
                    sub.destroy()
                else:
                    self.app.log("Error al guardar la configuración.", "ERROR")
            except ValueError:
                self.app.log("Por favor ingrese valores numéricos válidos.", "WARNING")

        tk.Button(sub, text="Guardar Configuración", command=save, bg="#4CAF50", fg="white", pady=5).pack(pady=20)

    def _setup_tab_autorizaciones(self, parent_frame):
        """Configura la UI para la pestaña de autorizaciones."""
        header = ttk.Frame(parent_frame)
        header.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(header, text="🛡️ Autorizaciones Pendientes", font=("Helvetica", 12, "bold")).pack(side="left")
        ttk.Button(header, text="🔄 Refrescar", command=self.refresh_autorizaciones).pack(side="right")
        
        # Treeview para autorizaciones
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ("id", "producto", "descripcion", "destino", "origen", "cantidad", "stock_dest", "fecha")
        self.tree_auto = ttk.Treeview(tree_frame, columns=columns, show="headings", displaycolumns=("producto", "descripcion", "destino", "origen", "cantidad", "stock_dest", "fecha"))
        
        self.tree_auto.heading("id", text="ID")
        self.tree_auto.heading("producto", text="Código")
        self.tree_auto.heading("descripcion", text="Descripción")
        self.tree_auto.heading("destino", text="Destino")
        self.tree_auto.heading("origen", text="Origen Sug.")
        self.tree_auto.heading("cantidad", text="Cant.")
        self.tree_auto.heading("stock_dest", text="Stock Dest.")
        self.tree_auto.heading("fecha", text="Fecha")
        
        self.tree_auto.column("id", width=0, stretch=False)
        self.tree_auto.column("producto", width=90)
        self.tree_auto.column("descripcion", width=250)
        self.tree_auto.column("destino", width=100)
        self.tree_auto.column("origen", width=100)
        self.tree_auto.column("cantidad", width=60)
        self.tree_auto.column("stock_dest", width=60)
        self.tree_auto.column("fecha", width=120)
        
        self.tree_auto.pack(side="left", fill="both", expand=True)
        
        scrolly = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_auto.yview)
        self.tree_auto.configure(yscrollcommand=scrolly.set)
        scrolly.pack(side="right", fill="y")
        
        # Actions
        footer = ttk.Frame(parent_frame)
        footer.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(footer, text="✅ Autorizar Seleccionada", command=self.on_autorizar).pack(side="right", padx=5)
        ttk.Button(footer, text="❌ Rechazar", command=self.on_rechazar).pack(side="right", padx=5)

    def _setup_tab_pendientes(self, parent_frame):
        """Configura la UI para la pestaña de sugerencias pendientes de procesar."""
        header = ttk.Frame(parent_frame)
        header.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(header, text="⏳ Transferencias Pendientes de Procesar", font=("Helvetica", 12, "bold")).pack(side="left")
        ttk.Button(header, text="🔄 Refrescar", command=self.refresh_pendientes).pack(side="right")
        
        # Treeview para pendientes
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ("id", "producto", "descripcion", "destino", "origen", "cantidad", "stock_dest", "fecha")
        self.tree_pend = ttk.Treeview(tree_frame, columns=columns, show="headings", displaycolumns=("producto", "descripcion", "destino", "origen", "cantidad", "stock_dest", "fecha"))
        
        self.tree_pend.heading("id", text="ID")
        self.tree_pend.heading("producto", text="Código")
        self.tree_pend.heading("descripcion", text="Descripción")
        self.tree_pend.heading("destino", text="Destino")
        self.tree_pend.heading("origen", text="Origen Sug.")
        self.tree_pend.heading("cantidad", text="Cant.")
        self.tree_pend.heading("stock_dest", text="Stock Dest.")
        self.tree_pend.heading("fecha", text="Fecha Aprobación")
        
        self.tree_pend.column("id", width=0, stretch=False)
        self.tree_pend.column("producto", width=90)
        self.tree_pend.column("descripcion", width=250)
        self.tree_pend.column("destino", width=100)
        self.tree_pend.column("origen", width=100)
        self.tree_pend.column("cantidad", width=60)
        self.tree_pend.column("stock_dest", width=60)
        self.tree_pend.column("fecha", width=120)
        
        self.tree_pend.pack(side="left", fill="both", expand=True)
        
        scrolly = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_pend.yview)
        self.tree_pend.configure(yscrollcommand=scrolly.set)
        scrolly.pack(side="right", fill="y")
        
        footer = ttk.Frame(parent_frame)
        footer.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(footer, text="📊 Exportar a Excel", command=self.exportar_pendientes).pack(side="right", padx=5)

    def refresh_autorizaciones(self):
        """Carga las sugerencias pendientes de autorización."""
        for i in self.tree_auto.get_children():
            self.tree_auto.delete(i)
            
        try:
            query = """
                SELECT t.id, t.producto_codigo, COALESCE(p.cu_descripcion_corta, p.C_DESCRI, 'SIN DESCRIPCIÓN') as descripcion,
                       t.sucursal_destino, t.sucursal_origen_sugerida, 
                       t.cantidad_sugerida, t.stock_actual, t.fecha_generacion
                FROM pal_sugerencias_transferencia t
                LEFT JOIN MA_PRODUCTOS p ON t.producto_codigo = p.C_CODIGO COLLATE DATABASE_DEFAULT
                WHERE t.requiere_autorizacion = 1 AND t.estado = 'pendiente'
                ORDER BY t.fecha_generacion DESC
            """
            rows = self.app.db_manager.fetch_data(query)
            for r in rows:
                # Formatear datos para la UI
                r_list = list(r)
                # r_list[5] es cantidad_sugerida (Decimal)
                # r_list[6] es stock_actual (Decimal)
                # r_list[7] es fecha_generacion (datetime)
                
                try:
                    r_list[5] = f"{float(r_list[5]):.2f}" if r_list[5] is not None else "0.00"
                    r_list[6] = f"{float(r_list[6]):.2f}" if r_list[6] is not None else "0.00"
                    if r_list[7] and hasattr(r_list[7], 'strftime'):
                        r_list[7] = r_list[7].strftime("%Y-%m-%d %H:%M")
                except:
                    pass
                    
                self.tree_auto.insert("", "end", values=r_list)
        except Exception as e:
            logger.error(f"Error refrescando autorizaciones: {e}")

    def refresh_pendientes(self):
        """Carga las sugerencias que ya fueron aprobadas pero no procesadas."""
        for i in self.tree_pend.get_children():
            self.tree_pend.delete(i)
            
        try:
            query = """
                SELECT t.id, t.producto_codigo, COALESCE(p.cu_descripcion_corta, p.C_DESCRI, 'SIN DESCRIPCIÓN') as descripcion,
                       t.sucursal_destino, t.sucursal_origen_sugerida, 
                       t.cantidad_sugerida, t.stock_actual, t.fecha_autorizacion
                FROM pal_sugerencias_transferencia t
                LEFT JOIN MA_PRODUCTOS p ON t.producto_codigo = p.C_CODIGO COLLATE DATABASE_DEFAULT
                WHERE t.estado = 'aprobada'
                ORDER BY t.fecha_autorizacion DESC
            """
            rows = self.app.db_manager.fetch_data(query)
            for r in rows:
                # Formatear datos para la UI
                r_list = list(r)
                try:
                    r_list[5] = f"{float(r_list[5]):.2f}" if r_list[5] is not None else "0.00"
                    r_list[6] = f"{float(r_list[6]):.2f}" if r_list[6] is not None else "0.00"
                    if r_list[7] and hasattr(r_list[7], 'strftime'):
                        r_list[7] = r_list[7].strftime("%Y-%m-%d %H:%M")
                except:
                    pass
                self.tree_pend.insert("", "end", values=r_list)
        except Exception as e:
            logger.error(f"Error refrescando pendientes: {e}")

    def exportar_pendientes(self):
        """Exporta las transferencias pendientes a Excel."""
        items = self.tree_pend.get_children()
        if not items:
            messagebox.showwarning("Atención", "No hay transferencias pendientes para exportar.")
            return

        from tkinter import filedialog
        from datetime import datetime
        import openpyxl
        
        default_name = f"Transferencias_Pendientes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=default_name
        )
        
        if not filename:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Pendientes"
            
            headers = ["ID", "Producto", "Descripción", "Destino", "Origen", "Cantidad", "Stock Destino", "Fecha Aprobación"]
            ws.append(headers)
            
            for item in items:
                values = self.tree_pend.item(item)['values']
                ws.append(values)
                
            wb.save(filename)
            messagebox.showinfo("Éxito", f"Reporte exportado correctamente a:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar el reporte: {e}")

    def on_autorizar(self):
        """Abre diálogo para autorizar la sugerencia seleccionada."""
        selected = self.tree_auto.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una sugerencia para autorizar.")
            return
            
        item = self.tree_auto.item(selected[0])
        s_id = item['values'][0]
        prod = item['values'][1]
        cant_sug = item['values'][5]
        
        # Modal de autorización
        modal = tk.Toplevel(self)
        modal.title(f"Autorizar: {prod}")
        modal.geometry("350x250")
        modal.transient(self)
        modal.grab_set()
        
        ttk.Label(modal, text=f"Autorizar Producto: {prod}", font=("Helvetica", 10, "bold")).pack(pady=10)
        
        frame = ttk.Frame(modal, padding=15)
        frame.pack(fill="both")
        
        ttk.Label(frame, text="Cantidad Autorizada:").grid(row=0, column=0, sticky="w", pady=5)
        var_cant = tk.StringVar(value=str(cant_sug))
        ttk.Entry(frame, textvariable=var_cant, width=15).grid(row=0, column=1, pady=5)
        
        ttk.Label(frame, text="Motivo/Nota:").grid(row=1, column=0, sticky="w", pady=5)
        ent_motivo = ttk.Entry(frame, width=25)
        ent_motivo.grid(row=1, column=1, pady=5)
        
        def confirm():
            try:
                nueva_cant = float(var_cant.get())
                motivo = ent_motivo.get()
                
                from pal.services.abastecimiento import AbastecimientoService
                service = AbastecimientoService(self.app.db_manager)
                
                # Obtener usuario actual del app
                user_id = getattr(self.app, 'current_user_id', None)
                
                if service.registrar_autorizacion(s_id, user_id, nueva_cant, motivo):
                    messagebox.showinfo("Éxito", "Autorización registrada correctamente.", parent=modal)
                    modal.destroy()
                    self.refresh_autorizaciones()
                    self.refresh_pendientes()
                else:
                    messagebox.showerror("Error", "No se pudo registrar la autorización.", parent=modal)
            except ValueError:
                messagebox.showerror("Error", "La cantidad debe ser numérica.", parent=modal)

        btn_frame = ttk.Frame(modal, padding=10)
        btn_frame.pack(side="bottom", fill="x")
        ttk.Button(btn_frame, text="Cancelar", command=modal.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Confirmar ✅", command=confirm).pack(side="right", padx=5)

    def on_rechazar(self):
        """Rechaza la sugerencia seleccionada."""
        selected = self.tree_auto.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una sugerencia para rechazar.")
            return
            
        if not messagebox.askyesno("Confirmar", "¿Está seguro de rechazar esta sugerencia?"):
            return
            
        item = self.tree_auto.item(selected[0])
        s_id = item['values'][0]
        
        try:
            sql = "UPDATE pal_sugerencias_transferencia SET estado = 'rechazada' WHERE id = ?"
            self.app.db_manager.execute_query(sql, (s_id,))
            self.refresh_autorizaciones()
            messagebox.showinfo("Éxito", "Sugerencia rechazada.")
        except Exception as e:
            logger.error(f"Error rechazando sugerencia: {e}")
            messagebox.showerror("Error", "No se pudo rechazar la sugerencia.")

    def refresh_data(self):
        """Método llamado cuando se selecciona la pestaña principal."""
        # Actualizar lista de sedes
        sedes_data = self.config_manager.get_sedes_config()
        sedes_list = ["ICH (Todas las sedes)"] + [f"{s} - {sedes_data[s].get('descripcion', '')}" for s in sedes_data.keys()]
        if self.sede_combo:
            self.sede_combo['values'] = sedes_list
            
        # Si las pestañas secundarias están visibles, refrescarlas
        try:
            current_tab = self.notebook.tab(self.notebook.select(), "text")
            if current_tab == "Autorizaciones":
                self.refresh_autorizaciones()
            elif current_tab == "Pendientes de Procesar":
                self.refresh_pendientes()
        except:
            pass
            
        # Configurar jerarquía
        if not hasattr(self.app, 'tra_dept_dict') or not self.app.tra_dept_dict:
            if hasattr(self.app, 'cargar_jerarquia_unificada'):
                self.app.cargar_jerarquia_unificada()
                
        # Llenar departamento
        if hasattr(self.app, 'tra_dept_dict') and self.app.tra_dept_dict:
            valores_dept = ['Todos'] + list(self.app.tra_dept_dict.keys())
            if self.dept_combo:
                self.dept_combo['values'] = valores_dept
