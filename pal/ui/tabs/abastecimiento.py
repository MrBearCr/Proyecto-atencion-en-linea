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
        
        # Animación para estado "En Tránsito" (Derecha a Izquierda)
        self.anim_frame = 0
        self.anim_sequence = [
            "En Transito🚚",
            "En Transi🚚",
            "En Tran🚚",
            "En Tra🚚",
            "En Tr🚚",
            "En 🚚",
            "En🚚",
            "🚚"
        ]
        self.anim_running = False
        
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
        
        # Toggle checkbox on click y menú contextual
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Button-3>", self._mostrar_menu_contextual_abastecimiento)
        
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
        
        # Treeview Tags - Pintado de FONDO (como solicitó el usuario)
        self.tree.tag_configure('rojo', background='#ffcccc')
        self.tree.tag_configure('sin_stock', background='#e0b0ff')
        self.tree.tag_configure('ajustado', background='#fff9c4')
        self.tree.tag_configure("aumentado", background="#ffcc80") # Naranja
        self.tree.tag_configure("disminuido", background="#81d4fa") # Azul
        
        # Estilo corregido: Solo definimos el color de SELECCIÓN. 
        # Al NO definir '!selected', permitimos que los Tags pinten el fondo de la fila.
        style = ttk.Style()
        style.configure("Treeview", fieldbackground="white")
        style.map('Treeview', background=[('selected', '#347083')]) 
        
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
            error_msg = str(e)
            self.after(0, lambda msg=error_msg: self._finalizar_calculo([], sede, error=msg))

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

            # Inicializar cantidad original para detectar cambios manuales
            for s in sugerencias:
                if "_cantidad_original" not in s:
                    s["_cantidad_original"] = s["cantidad_sugerida"]

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
            
            # Comparar con la cantidad original decidida por el sistema
            cant_sug = float(s.get("cantidad_sugerida", 0))
            cant_orig = float(s.get("_cantidad_original", cant_sug))
            
            if cant_sug > cant_orig:
                tags.append("aumentado")
                logger.info(f"Producto {s['producto_codigo']} ({s.get('sucursal_destino', 'N/A')}) marcado como AUMENTADO: {cant_sug} > {cant_orig}")
            elif cant_sug < cant_orig:
                tags.append("disminuido")
                logger.info(f"Producto {s['producto_codigo']} ({s.get('sucursal_destino', 'N/A')}) marcado como DISMINUIDO: {cant_sug} < {cant_orig}")

            sel_char = "☑" if s.get("_seleccionado", True) else "☐"
            
            # Formatear Código con ceros si es numérico (zfill 6)
            cod_raw = str(s["producto_codigo"]).strip()
            cod_display = cod_raw.zfill(6) if cod_raw.isdigit() else cod_raw

            # Formatear Sede Origen: "Stock / Depósito"
            origen_base = s.get("sucursal_origen_sugerida", "")
            stock_org = s.get("stock_origen", 0)
            if origen_base and origen_base != "SIN STOCK CDT":
                origen_display = f"{int(stock_org)} / {origen_base}"
            else:
                origen_display = origen_base

            self.tree.insert("", "end", values=(
                sel_char,
                cod_display,
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
            
            # Obtener ID de usuario (corregido de current_user_id a current_user['id'])
            user_id = self.app.current_user['id'] if self.app.current_user else None
            
            if service.save_sugerencias(seleccionadas, usuario_id=user_id):
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

        tk.Label(frame, text="Umbral de Quiebre (Gatillo Días):").grid(row=2, column=0, sticky=tk.W, pady=5)
        var_quiebre = tk.StringVar(value=str(global_params[2] if global_params[2] is not None else 50))
        tk.Entry(frame, textvariable=var_quiebre, width=10).grid(row=2, column=1, pady=5)

        def save():
            try:
                d = int(var_dias.get())
                a = float(var_auto.get())
                q = float(var_quiebre.get())
                # Guardar en la base de datos
                if service.save_parametro(None, d, q, a, 365):
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
        
        # Tags de color para autorizaciones
        self.tree_auto.tag_configure('rojo', background='#ffcccc')
        
        # Actions
        footer = ttk.Frame(parent_frame)
        footer.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(footer, text="✅ Autorizar Seleccionada", command=self.on_autorizar).pack(side="right", padx=5)
        ttk.Button(footer, text="❌ Rechazar", command=self.on_rechazar).pack(side="right", padx=5)

    def _setup_tab_pendientes(self, parent_frame):
        """Configura la UI para la pestaña de seguimiento de órdenes de transferencia."""
        header = ttk.Frame(parent_frame)
        header.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(header, text="🚚 Seguimiento de Órdenes de Transferencia (En Tránsito)", font=("Helvetica", 12, "bold")).pack(side="left")
        ttk.Button(header, text="🔄 Refrescar", command=self.refresh_pendientes).pack(side="right")
        
        # Treeview para órdenes (maestros)
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ("id", "numero", "destino", "fecha", "items", "usuario", "estado")
        self.tree_pend = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        self.tree_pend.heading("id", text="ID")
        self.tree_pend.heading("numero", text="N° Orden")
        self.tree_pend.heading("destino", text="Sede Destino")
        self.tree_pend.heading("fecha", text="Fecha Despacho")
        self.tree_pend.heading("items", text="Cant. Productos")
        self.tree_pend.heading("usuario", text="Usuario Despacha")
        self.tree_pend.heading("estado", text="Estado")
        
        self.tree_pend.column("id", width=50, anchor="center")
        self.tree_pend.column("numero", width=120, anchor="center")
        self.tree_pend.column("destino", width=150)
        self.tree_pend.column("fecha", width=150, anchor="center")
        self.tree_pend.column("items", width=100, anchor="center")
        self.tree_pend.column("usuario", width=150)
        self.tree_pend.column("estado", width=100, anchor="center")
        
        self.tree_pend.pack(side="left", fill="both", expand=True)
        
        scrolly = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_pend.yview)
        self.tree_pend.configure(yscrollcommand=scrolly.set)
        scrolly.pack(side="right", fill="y")
        
        # Tags de color para pendientes
        self.tree_pend.tag_configure('rojo', background='#ffcccc')
        
        # Actions
        footer = ttk.Frame(parent_frame)
        footer.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(footer, text="📋 Ver Detalle de Orden", command=self.on_ver_detalle_orden).pack(side="left", padx=5)
        ttk.Button(footer, text="📦 Confirmar Recepción ✅", command=self.on_cerrar_orden).pack(side="right", padx=5)
        ttk.Button(footer, text="📊 Exportar a Excel", command=self.exportar_pendientes).pack(side="right", padx=5)

    def refresh_autorizaciones(self):
        """Carga las sugerencias pendientes de autorización."""
        for i in self.tree_auto.get_children():
            self.tree_auto.delete(i)
            
        try:
            query = """
                SELECT t.id, t.producto_codigo, COALESCE(p.cu_descripcion_corta, p.C_DESCRI, 'SIN DESCRIPCIÓN') as descripcion,
                       t.sucursal_destino, t.sucursal_origen_sugerida, 
                       t.cantidad_sugerida, t.stock_actual, t.fecha_generacion, t.es_producto_rojo
                FROM pal_sugerencias_transferencia t
                LEFT JOIN MA_PRODUCTOS p ON t.producto_codigo = p.C_CODIGO COLLATE DATABASE_DEFAULT
                WHERE t.requiere_autorizacion = 1 AND t.estado = 'pendiente'
                ORDER BY t.fecha_generacion DESC
            """
            rows = self.app.db_manager.fetch_data(query)
            for r in rows:
                # Formatear datos para la UI
                r_list = list(r)[:8] # Tomamos los primeros 8 para los valores visibles
                tags = []
                if r[8]: # es_producto_rojo
                    tags.append('rojo')
                
                try:
                    r_list[5] = f"{float(r_list[5]):.2f}" if r_list[5] is not None else "0.00"
                    r_list[6] = f"{float(r_list[6]):.2f}" if r_list[6] is not None else "0.00"
                    if r_list[7] and hasattr(r_list[7], 'strftime'):
                        r_list[7] = r_list[7].strftime("%Y-%m-%d %H:%M")
                except:
                    pass
                    
                self.tree_auto.insert("", "end", values=r_list, tags=tags)
        except Exception as e:
            logger.error(f"Error refrescando autorizaciones: {e}")

    def refresh_pendientes(self):
        """Carga las órdenes de transferencia que están en tránsito."""
        for i in self.tree_pend.get_children():
            self.tree_pend.delete(i)
            
        try:
            from pal.services.abastecimiento import AbastecimientoService
            service = AbastecimientoService(self.app.db_manager)
            ordenes = service.get_ordenes_activas()
            
            for r in ordenes:
                # r: id, numero, destino, fecha, estado, total_items, usuario_nombre, items_completados
                if len(r) >= 8:
                    m_id, num, dest, fecha, estado, items, usuario, items_completados = r[:8]
                else:
                    m_id, num, dest, fecha, estado, items, usuario = r[:7]
                    items_completados = 0
                
                fecha_str = fecha.strftime("%Y-%m-%d %H:%M") if fecha else ""
                
                tags = []
                estado_display = estado
                if estado == 'en_transito':
                    estado_display = "En Tránsito 🚚" # Se animará luego si aplica
                    tags.append("anim_transito")
                elif estado == 'recibida_parcial':
                    estado_display = f"Parcial ({items_completados}/{items})"
                    tags.append("parcial")
                
                self.tree_pend.insert("", "end", values=(
                    m_id, num, dest, fecha_str, items, usuario or "N/A", estado_display
                ), tags=tags)
            
            # Iniciar animación si no está corriendo y hay algo que animar
            if not self.anim_running and self.tree_pend.tag_has("anim_transito"):
                self.anim_running = True
                self._update_status_animation()
                
        except Exception as e:
            logger.error(f"Error refrescando órdenes: {e}")

    def _update_status_animation(self):
        """Ciclo de animación para las filas en tránsito."""
        if not self.anim_running:
            return
            
        # Verificar si todavía hay filas con el tag
        animated_items = self.tree_pend.tag_has("anim_transito")
        if not animated_items:
            self.anim_running = False
            return
            
        # Siguiente frame
        self.anim_frame = (self.anim_frame + 1) % len(self.anim_sequence)
        current_text = self.anim_sequence[self.anim_frame]
        
        # Actualizar cada ítem animado (columna Estado es el índice 6)
        for item_id in animated_items:
            try:
                vals = list(self.tree_pend.item(item_id, "values"))
                vals[6] = current_text
                self.tree_pend.item(item_id, values=vals)
            except:
                pass # Item podría haber sido borrado
                
        # Programar siguiente frame (800ms para que sea fluido pero no distraiga demasiado)
        self.after(800, self._update_status_animation)

    def on_ver_detalle_orden(self):
        """Muestra los productos incluidos en la orden seleccionada."""
        selected = self.tree_pend.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una orden para ver el detalle.")
            return
            
        item = self.tree_pend.item(selected[0])
        m_id = item['values'][0]
        num_orden = item['values'][1]
        
        # Modal de detalle
        modal = tk.Toplevel(self)
        modal.title(f"Detalle de Orden: {num_orden}")
        modal.geometry("700x450")
        modal.transient(self)
        modal.grab_set()
        
        ttk.Label(modal, text=f"Productos en Orden {num_orden}", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        frame = ttk.Frame(modal)
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        cols = ("producto", "descripcion", "cantidad", "origen")
        tree_det = ttk.Treeview(frame, columns=cols, show="headings")
        tree_det.heading("producto", text="Código")
        tree_det.heading("descripcion", text="Descripción")
        tree_det.heading("cantidad", text="Cant.")
        tree_det.heading("origen", text="Origen")
        
        tree_det.column("producto", width=100)
        tree_det.column("descripcion", width=300)
        tree_det.column("cantidad", width=80, anchor="center")
        tree_det.column("origen", width=100)
        
        tree_det.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        scrolly = ttk.Scrollbar(frame, orient="vertical", command=tree_det.yview)
        tree_det.configure(yscrollcommand=scrolly.set)
        scrolly.pack(side="right", fill="y")
        
        # Cargar datos
        try:
            from pal.services.abastecimiento import AbastecimientoService
            service = AbastecimientoService(self.app.db_manager)
            detalles = service.get_detalle_orden(m_id)
            
            for d in detalles:
                # d: id, codigo, descripcion, cantidad, origen, es_rojo
                tags = ('rojo',) if d[5] else ()
                tree_det.insert("", "end", values=(d[1], d[2], d[3], d[4]), tags=tags)
                
            tree_det.tag_configure('rojo', background='#ffcccc')
        except Exception as e:
            logger.error(f"Error cargando detalle: {e}")
            
        ttk.Button(modal, text="Cerrar", command=modal.destroy).pack(pady=10)

    def on_cerrar_orden(self):
        """Abre el diálogo para registrar la recepción de mercancía (parcial o total) con soporte de LOTES."""
        selected = self.tree_pend.selection()
        if not selected:
            messagebox.showwarning("Atención", "Seleccione una orden para registrar recepción.")
            return
            
        item = self.tree_pend.item(selected[0])
        m_id = item['values'][0]
        num_orden = item['values'][1]
        
        # Almacenamiento temporal de lotes: {sugerencia_id: [{lote_fabrica, vencimiento, cantidad, lote_interno}, ...]}
        lotes_temp = {}

        # Modal de recepción
        modal = tk.Toplevel(self)
        modal.title(f"Recepción de Mercancía: {num_orden}")
        modal.geometry("1100x700") # Más ancho para columna lotes
        modal.transient(self)
        modal.grab_set()
        
        ttk.Label(modal, text=f"Registrar Recepción para Orden {num_orden}", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        # Instrucciones
        info_frame = ttk.Frame(modal)
        info_frame.pack(fill="x", padx=10)
        ttk.Label(info_frame, text="Haga DOBLE CLIC en 'A Recibir' para cantidad simple o en 'Lotes 📝' para detalle.", foreground="blue").pack(pady=2)
        
        # Treeview editable
        frame = ttk.Frame(modal)
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        cols = ("id", "producto", "descripcion", "solicitado", "recibido_prev", "pendiente", "a_recibir", "lotes")
        tree_rec = ttk.Treeview(frame, columns=cols, show="headings")
        
        tree_rec.heading("id", text="ID")
        tree_rec.heading("producto", text="Código")
        tree_rec.heading("descripcion", text="Descripción")
        tree_rec.heading("solicitado", text="Solicitado")
        tree_rec.heading("recibido_prev", text="Recibido Prev.")
        tree_rec.heading("pendiente", text="Pendiente")
        tree_rec.heading("a_recibir", text="A Recibir (Editar)")
        tree_rec.heading("lotes", text="Lotes(Gestión)")
        
        tree_rec.column("id", width=0, stretch=False)
        tree_rec.column("producto", width=100)
        tree_rec.column("descripcion", width=300)
        tree_rec.column("solicitado", width=80, anchor="center")
        tree_rec.column("recibido_prev", width=100, anchor="center")
        tree_rec.column("pendiente", width=80, anchor="center")
        tree_rec.column("a_recibir", width=120, anchor="center")
        tree_rec.column("lotes", width=100, anchor="center")
        
        tree_rec.pack(side="left", fill="both", expand=True)
        
        scrolly = ttk.Scrollbar(frame, orient="vertical", command=tree_rec.yview)
        tree_rec.configure(yscrollcommand=scrolly.set)
        scrolly.pack(side="right", fill="y")
        
        # Service instance
        from pal.services.abastecimiento import AbastecimientoService
        service = AbastecimientoService(self.app.db_manager)

        # Cargar datos
        try:
            detalles = service.get_detalle_orden(m_id)
            
            count_pendientes = 0
            for d in detalles:
                # d: id, codigo, descripcion, cantidad_sug, origen, es_rojo, cant_recibida_total, estado_recepcion
                cant_sug = float(d[3])
                cant_rec = float(d[6]) if len(d) > 6 else 0.0
                pendiente = max(0, cant_sug - cant_rec)
                a_recibir = pendiente
                
                if pendiente > 0:
                    tree_rec.insert("", "end", values=(d[0], d[1], d[2], cant_sug, cant_rec, pendiente, a_recibir, "⚠️ Sin Lotes"))
                    count_pendientes += 1
            
            if count_pendientes == 0:
                messagebox.showinfo("Información", "Esta orden ya ha sido recibida completamente.", parent=modal)
                modal.destroy()
                return
                
        except Exception as e:
            logger.error(f"Error cargando detalle para recepción: {e}")
            messagebox.showerror("Error", "No se pudieron cargar los detalles de la orden.")
            modal.destroy()
            return

        # --- SUB-MODAL GESTIÓN LOTES ---
        from datetime import datetime
        def abrir_gestion_lotes(item_id, sug_id, prod_cod, prod_desc, pendiente):
            sub = tk.Toplevel(modal)
            sub.title(f"Gestión de Lotes: {prod_cod}")
            sub.geometry("600x400")
            sub.transient(modal)
            sub.grab_set()
            
            ttk.Label(sub, text=f"Lotes para {prod_desc}", font=("Arial", 11, "bold")).pack(pady=10)
            ttk.Label(sub, text=f"Pendiente Total: {pendiente}", foreground="red").pack()
            
            # Lista de lotes agregados
            l_frame = ttk.Frame(sub)
            l_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            cols_l = ("lote", "venc", "cant")
            tree_lotes = ttk.Treeview(l_frame, columns=cols_l, show="headings", height=8)
            tree_lotes.heading("lote", text="Lote Fábrica")
            tree_lotes.heading("venc", text="Vencimiento")
            tree_lotes.heading("cant", text="Cantidad")
            tree_lotes.column("lote", width=150)
            tree_lotes.column("venc", width=100)
            tree_lotes.column("cant", width=80)
            tree_lotes.pack(side="left", fill="both", expand=True)
            
            # Cargar existentes si hay
            current_lotes = lotes_temp.get(sug_id, [])
            for l in current_lotes:
                tree_lotes.insert("", "end", values=(l.get('lote_fabrica', '-'), l.get('fecha_vencimiento', '-'), l.get('cantidad', 0)))

            # Formulario agregar
            f_add = ttk.LabelFrame(sub, text="Agregar Lote")
            f_add.pack(fill="x", padx=10, pady=5)
            
            ttk.Label(f_add, text="Lote Fábrica:").grid(row=0, column=0, padx=5)
            e_lote = ttk.Entry(f_add, width=15)
            e_lote.grid(row=0, column=1, padx=5)
            
            ttk.Label(f_add, text="Vence (YYYY-MM-DD):").grid(row=0, column=2, padx=5)
            e_venc = ttk.Entry(f_add, width=12)
            e_venc.grid(row=0, column=3, padx=5)
            
            ttk.Label(f_add, text="Cantidad:").grid(row=0, column=4, padx=5)
            e_cant = ttk.Entry(f_add, width=8)
            e_cant.grid(row=0, column=5, padx=5)
            
            def add_lote(silent=False):
                """Agrega el lote del formulario al treeview. Retorna True si agregó, False si error o vacío."""
                try:
                    cant_str = e_cant.get().strip()
                    if not cant_str: 
                        if not silent: messagebox.showwarning("Atención", "Ingrese una cantidad.", parent=sub)
                        return False
                        
                    c = float(cant_str)
                    if c <= 0: raise ValueError
                    
                    l_fab = e_lote.get().strip() or "S/L"
                    venc = e_venc.get().strip()
                    # Validar fecha simple
                    if venc:
                        try:
                            datetime.strptime(venc, "%Y-%m-%d")
                        except:
                            if not silent: messagebox.showerror("Error", "Formato de fecha inválido. Use YYYY-MM-DD", parent=sub)
                            return False
                    else:
                        venc = None
                        
                    # Agregar a treeview
                    tree_lotes.insert("", "end", values=(l_fab, venc or "N/A", c))
                    
                    # Limpiar
                    e_cant.delete(0, 'end')
                    e_lote.delete(0, 'end')
                    # No limpiamos fecha por comodidad al meter varios lotes misma fecha
                    e_lote.focus()
                    return True
                except ValueError:
                    if not silent: messagebox.showerror("Error", "Cantidad inválida", parent=sub)
                    return False

            ttk.Button(f_add, text="➕", command=lambda: add_lote(), width=4).grid(row=0, column=6, padx=5)

            def guardar_lotes():
                # Validar si hay datos pendientes en los campos
                if e_cant.get().strip():
                    if messagebox.askyesno("Datos pendientes", "Hay datos en el formulario sin agregar. ¿Desea agregarlos antes de guardar?", parent=sub):
                        if not add_lote():
                            return # Si falla agregar, no guardar aún

                # Recopilar del treeview
                nuevos_lotes = []
                total_lotes = 0.0
                for item in tree_lotes.get_children():
                    v = tree_lotes.item(item)['values']
                    cant = float(v[2])
                    l_obj = {
                        'lote_fabrica': str(v[0]) if v[0] != '-' else None,
                        'fecha_vencimiento': str(v[1]) if v[1] != 'N/A' else None,
                        'cantidad': cant
                    }
                    nuevos_lotes.append(l_obj)
                    total_lotes += cant
                
                # Actualizar memoria temporal
                lotes_temp[sug_id] = nuevos_lotes
                
                # Actualizar UI Principal
                vals = list(tree_rec.item(item_id, "values"))
                vals[6] = total_lotes # Actualizar 'A Recibir' con la suma de lotes
                vals[7] = f"✅ {len(nuevos_lotes)} Lotes"
                tree_rec.item(item_id, values=vals)
                
                sub.destroy()

            ttk.Button(sub, text="Guardar Lotes", command=guardar_lotes).pack(pady=10)

        # Función para editar cantidad o lotes
        def on_double_click(event):
            item_id = tree_rec.identify_row(event.y)
            column = tree_rec.identify_column(event.x)
            
            if not item_id: return
            
            vals = tree_rec.item(item_id, "values")
            sug_id = int(vals[0])
            prod_cod = vals[1]
            prod_desc = vals[2]
            pendiente = float(vals[5])

            if column == "#8": # Columna Lotes
                abrir_gestion_lotes(item_id, sug_id, prod_cod, prod_desc, pendiente)
                return
            
            if column == "#7": # Columna A Recibir (Edición simple)
                # Crear entry widget sobre la celda
                x, y, width, height = tree_rec.bbox(item_id, column)
                current_val = vals[6]
                
                entry = ttk.Entry(tree_rec, width=10)
                entry.place(x=x, y=y, width=width, height=height)
                entry.insert(0, current_val)
                entry.select_range(0, 'end')
                entry.focus()
                
                def save_edit(event=None):
                    try:
                        val_str = entry.get()
                        if not val_str: val_str = "0"
                        new_val = float(val_str)
                        if new_val < 0: raise ValueError
                        
                        # Validar contra pendiente
                        if new_val > pendiente:
                            messagebox.showwarning("Cuidado", f"Está recibiendo más ({new_val}) de lo pendiente ({pendiente}).", parent=modal)
                        
                        # Advertencia si hay lotes definidos y no coinciden
                        if sug_id in lotes_temp:
                             sum_lotes = sum(l['cantidad'] for l in lotes_temp[sug_id])
                             if sum_lotes != new_val:
                                 if messagebox.askyesno("Conflicto Lotes", f"La cantidad ({new_val}) no coincide con la suma de lotes definidos ({sum_lotes}).\n¿Desea borrar los lotes definidos?", parent=modal):
                                     del lotes_temp[sug_id]
                                     vals_u = list(tree_rec.item(item_id, "values"))
                                     vals_u[7] = "⚠️ Sin Lotes" # Reset lotes visual
                                     tree_rec.item(item_id, values=vals_u)
                                 else:
                                     entry.destroy(); return

                        # Actualizar treeview
                        vals = list(tree_rec.item(item_id, "values"))
                        vals[6] = new_val
                        tree_rec.item(item_id, values=vals)
                        entry.destroy()
                    except ValueError:
                        messagebox.showerror("Error", "Ingrese un número válido.", parent=modal)
                        entry.focus()
                
                entry.bind("<Return>", save_edit)
                entry.bind("<FocusOut>", lambda e: entry.destroy())

        tree_rec.bind("<Double-1>", on_double_click)

        # Botones de acción
        btn_frame = ttk.Frame(modal, padding=10)
        btn_frame.pack(side="bottom", fill="x")
        
        def recibir_todo():
            """Pone todas las cantidades a recibir igual al pendiente."""
            for item in tree_rec.get_children():
                vals = list(tree_rec.item(item, "values"))
                vals[6] = vals[5] # A recibir = Pendiente
                tree_rec.item(item, values=vals)
        
        def procesar_recepcion():
            """Recoge los datos y llama al servicio."""
            items_a_procesar = []
            
            for item in tree_rec.get_children():
                vals = tree_rec.item(item, "values")
                sug_id = int(vals[0])
                a_recibir = float(vals[6])
                
                if a_recibir > 0:
                    item_data = {
                        'sugerencia_id': sug_id,
                        'cantidad': a_recibir
                    }
                    # Adjuntar lotes si existen
                    if sug_id in lotes_temp:
                        lotes = lotes_temp[sug_id]
                        # Validar suma
                        sum_l = sum(l['cantidad'] for l in lotes)
                        if abs(sum_l - a_recibir) > 0.01:
                            messagebox.showerror("Error de Validación", f"Para el producto ID {sug_id}, la suma de lotes ({sum_l}) no coincide con la cantidad a recibir ({a_recibir}). Ajuste los lotes o la cantidad.", parent=modal)
                            return
                        item_data['lotes'] = lotes
                    
                    items_a_procesar.append(item_data)
            
            if not items_a_procesar:
                messagebox.showwarning("Atención", "No hay cantidades a recibir ingresadas (mayores a 0).", parent=modal)
                return

            if not messagebox.askyesno("Confirmar", f"¿Desea registrar la recepción de {len(items_a_procesar)} productos?", parent=modal):
                return
                
            try:
                user_id = self.app.current_user['id'] if self.app.current_user else None
                result = service.registrar_recepcion(m_id, items_a_procesar, user_id)
                
                if result['success']:
                    rec_num = result['numero_recepcion']
                    estado_trs = result['estado_transferencia']
                    
                    msg = f"Recepción {rec_num} registrada correctamente."
                    if estado_trs == 'recibida_total':
                        msg += "\n\nLa orden se ha completado en su totalidad. 🎉"
                    else:
                        msg += "\n\nLa orden queda PARCIALMENTE recibida."
                        
                    messagebox.showinfo("Éxito", msg, parent=modal)
                    modal.destroy()
                    self.refresh_pendientes()
                else:
                    messagebox.showerror("Error", f"Error registrando recepción: {result.get('error', 'Desconocido')}", parent=modal)
            except Exception as e:
                logger.error(f"Error procesando recepción: {e}")
                messagebox.showerror("Error", f"Error inesperado: {e}", parent=modal)

        ttk.Button(btn_frame, text="Cancelar", command=modal.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="✅ Registrar Recepción", command=procesar_recepcion).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Recibir Todo (Pendiente)", command=recibir_todo).pack(side="left", padx=5)

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
                
                # Obtener usuario actual del app (corregido de current_user_id a current_user['id'])
                user_id = self.app.current_user['id'] if self.app.current_user else None
                
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
    def _mostrar_menu_contextual_abastecimiento(self, event):
        """Muestra menú contextual en la tabla de resultados de abastecimiento."""
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Cambiar monto a transferir", command=self._cambiar_monto_abastecimiento)
            menu.tk_popup(event.x_root, event.y_root)

    def _cambiar_monto_abastecimiento(self):
        """Permite cambiar el monto de una sugerencia antes de procesarla."""
        selected = self.tree.selection()
        if not selected: return
        
        item_data = self.tree.item(selected[0])
        values = item_data['values']
        # values: (sel_char, producto, descripcion, destino, origen, cantidad, stock_dest, autorizacion)
        # Aseguramos que los valores del tree sean tratados como strings limpios
        prod_codigo = str(values[1]).strip()
        desc_prod = values[2]
        dest_sede = str(values[3]).strip()
        cant_actual = values[5]
        
        from tkinter import simpledialog
        prompt = f"Producto: {prod_codigo}\n{desc_prod}\nSede: {dest_sede}\n\nNueva cantidad para transferir:"
        logger.info(f"Abriendo diálogo de ajuste para [{prod_codigo}] en sede [{dest_sede}]. Cantidad actual: {cant_actual}")
        
        nuevo_monto = simpledialog.askfloat("Modificar Cantidad", prompt, initialvalue=float(cant_actual), parent=self)
        
        if nuevo_monto is not None and nuevo_monto >= 0:
            # Buscar en last_sugerencias para actualizar
            encontrado = False
            
            # Normalizar el código buscado (quitar ceros si es numérico)
            p_buscado_norm = prod_codigo.lstrip('0') if prod_codigo.isdigit() else prod_codigo
            if not p_buscado_norm: p_buscado_norm = "0" # Caso código "000"
            
            for s in self.last_sugerencias:
                s_prod = str(s.get("producto_codigo", "")).strip()
                s_dest = str(s.get("sucursal_destino", "")).strip()
                
                # Normalizar el código de la lista interna
                s_prod_norm = s_prod.lstrip('0') if s_prod.isdigit() else s_prod
                if not s_prod_norm: s_prod_norm = "0"
                
                # Comparación robusta: Código (sin ceros) y Sede (en MAYÚSCULAS)
                if s_prod_norm == p_buscado_norm and s_dest.upper() == dest_sede.upper():
                    logger.info(f"Ajuste confirmado: {s_prod} en {s_dest}: {s['cantidad_sugerida']} -> {nuevo_monto}")
                    s["cantidad_sugerida"] = nuevo_monto
                    encontrado = True
                    break
            
            if not encontrado:
                logger.warning(f"No se encontró la sugerencia para [{prod_codigo}] (norm: [{p_buscado_norm}]) en la sede [{dest_sede}] en last_sugerencias.")
                messagebox.showwarning("Atención", f"No se pudo localizar el producto {prod_codigo} en la lista interna para actualizarlo.")
            
            # Refrescar UI (esto actualiza filtered_results y el treeview)
            self._aplicar_filtro_local()
        else:
            logger.info("Ajuste de monto cancelado por el usuario.")

