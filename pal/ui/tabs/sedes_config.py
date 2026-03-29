import tkinter as tk
from tkinter import ttk, messagebox
from pal.core.config_manager import ConfigManager
from pal.core.log import get_logger

logger = get_logger("UI_SEDES")

class SedesAlmacenesTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.config_manager = ConfigManager(app.db_manager)
        self.sedes_data = {}
        
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        # Layout principal: SplitPane (Izquierda: Sedes, Derecha: Configuración)
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # --- Panel Izquierdo: Lista de Sedes ---
        left_frame = ttk.LabelFrame(paned, text="Sedes", padding=5)
        paned.add(left_frame, minsize=200)
        
        # Lista de Sedes
        self.sedes_listbox = tk.Listbox(left_frame, selectmode=tk.SINGLE)
        self.sedes_listbox.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        self.sedes_listbox.bind("<<ListboxSelect>>", self._on_sede_select)
        
        # Botones CRUD Sede
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="+ Agregar", command=self._add_sede).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="- Eliminar", command=self._remove_sede).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- Panel Derecho: Detalles y Almacenes ---
        self.right_frame = ttk.LabelFrame(paned, text="Detalles de Sede", padding=10)
        paned.add(self.right_frame, minsize=350)
        
        # Campos básicos
        ttk.Label(self.right_frame, text="Nombre Sede:").grid(row=0, column=0, sticky="w", pady=2)
        self.var_sede_name = tk.StringVar()
        self.entry_sede_name = ttk.Entry(self.right_frame, textvariable=self.var_sede_name, state="readonly")
        self.entry_sede_name.grid(row=0, column=1, sticky="ew", pady=2, padx=5)

        ttk.Label(self.right_frame, text="Zona:").grid(row=1, column=0, sticky="w", pady=2)
        self.var_sede_zona = tk.StringVar()
        ttk.Entry(self.right_frame, textvariable=self.var_sede_zona).grid(row=1, column=1, sticky="ew", pady=2, padx=5)
        
        ttk.Label(self.right_frame, text="Descripción:").grid(row=2, column=0, sticky="w", pady=2)
        self.var_sede_desc = tk.StringVar()
        ttk.Entry(self.right_frame, textvariable=self.var_sede_desc).grid(row=2, column=1, sticky="ew", pady=2, padx=5)

        ttk.Label(self.right_frame, text="Código Localidad ODC:").grid(row=3, column=0, sticky="w", pady=2)
        self.var_sede_cod_localidad = tk.StringVar()
        ttk.Entry(self.right_frame, textvariable=self.var_sede_cod_localidad).grid(row=3, column=1, sticky="ew", pady=2, padx=5)
        ttk.Label(self.right_frame, text="(Código en MA_ODC.c_CODLOCALIDAD, ej: 01, 03, 04)", foreground="gray").grid(row=4, column=1, sticky="w", padx=5)

        # Separador
        ttk.Separator(self.right_frame, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)
        
        self.deposits_frame = ttk.Frame(self.right_frame)
        self.deposits_frame.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=5)
        self.right_frame.rowconfigure(6, weight=1)
        
        # Encabezados Almacenes
        header_frame = ttk.Frame(self.deposits_frame)
        header_frame.pack(fill=tk.X, padx=2)
        ttk.Label(header_frame, text="Almacén", width=30).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Tratable", width=10).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="CDT", width=10).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Transito", width=10).pack(side=tk.LEFT)
        
        # Canvas para scrollear checkboxes si son muchos
        self.canvas = tk.Canvas(self.deposits_frame)
        self.scrollbar = ttk.Scrollbar(self.deposits_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Botón Guardar
        ttk.Button(self.right_frame, text="💾 Guardar Cambios", command=self._save_changes).grid(row=7, column=0, columnspan=2, pady=10)

        # Variables para checkboxes: { "cod_deposito": {"tratable": BooleanVar, "cdt": BooleanVar} }
        self.deposit_vars = {}
        self.all_deposits = [] # [(cod, desc), ...]

    def _load_data(self):
        # Cargar configuración actual
        self.sedes_data = self.config_manager.get_sedes_config()
        
        # Cargar lista de depósitos disponibles desde BD
        try:
            sql = "SELECT c_coddeposito, c_descripcion FROM MA_DEPOSITO ORDER BY c_coddeposito"
            self.all_deposits = self.app.db_manager.fetch_data(sql)
        except Exception as e:
            logger.error(f"Error cargando depósitos: {e}")
            self.all_deposits = []

        # Poblar lista de Sedes
        self.sedes_listbox.delete(0, tk.END)
        for name in self.sedes_data.keys():
            self.sedes_listbox.insert(tk.END, name)
            
        # Crear checkboxes de depósitos (vacíos por ahora)
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        self.deposit_vars = {}
        for code, desc in self.all_deposits:
            row = ttk.Frame(self.scrollable_frame)
            row.pack(fill="x")
            
            ttk.Label(row, text=f"{code} - {desc}", width=30).pack(side=tk.LEFT, padx=2)
            
            var_tratable = tk.BooleanVar()
            cb_tratable = ttk.Checkbutton(row, variable=var_tratable)
            cb_tratable.pack(side=tk.LEFT, padx=15)
            
            var_cdt = tk.BooleanVar()
            cb_cdt = ttk.Checkbutton(row, variable=var_cdt)
            cb_cdt.pack(side=tk.LEFT, padx=15)

            var_transito = tk.BooleanVar()
            cb_transito = ttk.Checkbutton(row, variable=var_transito)
            cb_transito.pack(side=tk.LEFT, padx=15)
            
            self.deposit_vars[code] = {
                "tratable": var_tratable,
                "cdt": var_cdt,
                "transito": var_transito
            }
            
    def _on_sede_select(self, event):
        selection = self.sedes_listbox.curselection()
        if not selection:
            return
            
        sede_name = self.sedes_listbox.get(selection[0])
        data = self.sedes_data.get(sede_name, {})
        
        self.var_sede_name.set(sede_name)
        self.var_sede_desc.set(data.get("descripcion", ""))
        self.var_sede_zona.set(data.get("zona", ""))
        self.var_sede_cod_localidad.set(data.get("codigo_localidad", ""))
        
        # Marcar checkboxes
        active_deposits = set(data.get("almacenes_tratables", []))
        cdt_deposits = set(data.get("almacenes_cdt", []))
        transito_deposits = set(data.get("almacenes_transito", []))
        
        for code, vars in self.deposit_vars.items():
            vars["tratable"].set(code in active_deposits)
            if "almacenes_cdt" in data:
                 vars["cdt"].set(code in cdt_deposits)
            else:
                 vars["cdt"].set(False)
            
            if "almacenes_transito" in data:
                vars["transito"].set(code in transito_deposits)
            else:
                vars["transito"].set(False)

    def _add_sede(self):
        from tkinter import simpledialog
        name = simpledialog.askstring("Nueva Sede", "Nombre de la Sede:")
        if name:
            if name in self.sedes_data:
                messagebox.showerror("Error", "La sede ya existe.")
                return
            
            self.sedes_data[name] = {
                "descripcion": "",
                "zona": "",
                "almacenes_tratables": [],
                "almacenes_cdt": [],
                "almacenes_transito": []
            }
            self.sedes_listbox.insert(tk.END, name)
            self.sedes_listbox.selection_clear(0, tk.END)
            self.sedes_listbox.selection_set(tk.END)
            self._on_sede_select(None)

    def _remove_sede(self):
        selection = self.sedes_listbox.curselection()
        if not selection:
            return
        
        name = self.sedes_listbox.get(selection[0])
        if messagebox.askyesno("Confirmar", f"¿Eliminar sede '{name}'?"):
            del self.sedes_data[name]
            self.sedes_listbox.delete(selection[0])
            self._save_changes(silent=True) # Guardar autometicamente al borrar

    def _save_changes(self, silent=False):
        current_name = self.var_sede_name.get()
        if not current_name:
            return

        # Recoger datos del form
        selected_tratables = [code for code, vars in self.deposit_vars.items() if vars["tratable"].get()]
        selected_cdt = [code for code, vars in self.deposit_vars.items() if vars["cdt"].get()]
        selected_transito = [code for code, vars in self.deposit_vars.items() if vars["transito"].get()]
        
        self.sedes_data[current_name] = {
            "descripcion": self.var_sede_desc.get(),
            "zona": self.var_sede_zona.get(),
            "codigo_localidad": self.var_sede_cod_localidad.get().strip(),
            "almacenes_tratables": selected_tratables,
            "almacenes_cdt": selected_cdt,
            "almacenes_transito": selected_transito
        }
        
        # Guardar en BD via ConfigManager
        success = self.config_manager.save_sedes_config(self.sedes_data)
        
        if success:
            if not silent:
                messagebox.showinfo("Éxito", "Configuración guardada correctamente.")
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")

def create_sedes_almacenes_tab(parent, app):
    """Factory function para usar en app.py"""
    SedesAlmacenesTab(parent, app)
    return parent
