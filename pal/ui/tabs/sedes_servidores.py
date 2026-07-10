
import tkinter as tk
from tkinter import ttk, messagebox

class SedesServidoresTab(ttk.Frame):
    """
    Pestaña para gestionar las sedes remotas (conexiones VAD20).
    """
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db_manager = app.db_manager
        
        self.setup_ui()
        self.load_sedes()

    def setup_ui(self):
        # Frame de lista
        list_frame = ttk.LabelFrame(self, text="Sedes Configuradas", padding=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree = ttk.Treeview(list_frame, columns=("ID", "Nombre", "IP Principal", "IP Secundaria", "BD", "Estado"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("IP Principal", text="IP Principal")
        self.tree.heading("IP Secundaria", text="IP Secundaria")
        self.tree.heading("BD", text="BD")
        self.tree.heading("Estado", text="Estado")
        
        self.tree.column("ID", width=30)
        self.tree.column("Nombre", width=120)
        self.tree.column("IP Principal", width=100)
        self.tree.column("IP Secundaria", width=100)
        self.tree.column("BD", width=80)
        self.tree.column("Estado", width=60)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Botones CRUD
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Actualizar Lista", command=self.load_sedes).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Eliminar", command=self.delete_sede).pack(side=tk.RIGHT, padx=2)

        # Frame de edición
        self.edit_frame = ttk.LabelFrame(self, text="Detalles de Sede", padding=10)
        self.edit_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)

        fields = [
            ("Nombre Sede:", "nombre"),
            ("IP Principal:", "ip"),
            ("IP Secundaria:", "ip_secundaria"),
            ("Nombre BD:", "bd"),
            ("Usuario BD:", "user"),
            ("Password BD:", "pass")
        ]
        
        self.vars = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(self.edit_frame, text=label).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            entry = ttk.Entry(self.edit_frame, textvariable=var, width=25)
            if key == "pass": entry.configure(show="*")
            entry.grid(row=i, column=1, sticky="ew", pady=2, padx=5)
            self.vars[key] = var

        self.var_activa = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.edit_frame, text="Activa", variable=self.var_activa).grid(row=len(fields), column=1, sticky="w")

        ttk.Button(self.edit_frame, text="Limpiar", command=self.clear_form).grid(row=len(fields)+1, column=0, pady=10)
        ttk.Button(self.edit_frame, text="Guardar/Actualizar", command=self.save_sede).grid(row=len(fields)+1, column=1, pady=10)

        self.current_id = None

    def load_sedes(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            sedes = self.db_manager.get_sedes_config() # Retorna lista de dicts
            for s in sedes:
                estado = "Activa" if s['activa'] else "Inactiva"
                self.tree.insert("", tk.END, values=(s['id'], s['nombre_sede'], s['ip_servidor'], s.get('ip_secundaria', ''), s['nombre_bd'], estado))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar las sedes: {e}")

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        
        values = self.tree.item(sel[0], 'values')
        self.current_id = values[0]
        
        # Cargar datos completos para editar
        # Buscamos en el cache de sedes o volvemos a preguntar (mejor buscar en el Tree si tuviera todo, 
        # pero password no está en el Tree por seguridad)
        sedes = self.db_manager.get_sedes_config()
        sede = next((s for s in sedes if str(s['id']) == str(self.current_id)), None)
        
        if sede:
            self.vars['nombre'].set(sede['nombre_sede'])
            self.vars['ip'].set(sede['ip_servidor'])
            self.vars['ip_secundaria'].set(sede.get('ip_secundaria', ''))
            self.vars['bd'].set(sede['nombre_bd'])
            self.vars['user'].set(sede['usuario_bd'] or "")
            self.vars['pass'].set("") # No mostramos la pass por seguridad, si se deja vacía al guardar no se cambia? 
            # (Depende de cómo se implementó el backend, el backend actual pided password_bd_enc).
            # Para simplificar, pediremos re-ingresar pass si cambia.
            self.var_activa.set(sede['activa'])

    def clear_form(self):
        self.current_id = None
        for v in self.vars.values(): v.set("")
        self.var_activa.set(True)
        self.tree.selection_remove(self.tree.selection())

    def save_sede(self):
        data = {
            'nombre_sede': self.vars['nombre'].get(),
            'ip_servidor': self.vars['ip'].get(),
            'ip_secundaria': self.vars['ip_secundaria'].get() or None,
            'nombre_bd': self.vars['bd'].get(),
            'usuario_bd': self.vars['user'].get(),
            'activa': 1 if self.var_activa.get() else 0
        }
        
        password = self.vars['pass'].get()
        if password:
            try:
                # Encriptar password usando el SecureCredentialsManager de la app
                data['password_bd_enc'] = self.app.db_manager.credentials_manager.encrypt(password)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo encriptar la contraseña: {e}")
                return
        
        try:
            if self.current_id:
                # Actualizar. Si no hubo pass nueva, mantener la anterior? 
                # El backend actual reemplaza todo. 
                # Necesitamos consultar la pass vieja si no hay nueva.
                if not password:
                    old_sedes = self.db_manager.get_sedes_config()
                    old = next(s for s in old_sedes if str(s['id']) == str(self.current_id))
                    data['password_bd_enc'] = old['password_bd_enc']
                
                self.db_manager.update_sede(self.current_id, data)
                messagebox.showinfo("Éxito", "Sede actualizada")
            else:
                if not password:
                    messagebox.showwarning("Atención", "Debe ingresar una contraseña para nueva sede")
                    return
                self.db_manager.add_sede(data)
                messagebox.showinfo("Éxito", "Sede agregada")
            
            self.load_sedes()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    def delete_sede(self):
        if not self.current_id: return
        if messagebox.askyesno("Confirmar", "¿Desea eliminar esta sede?"):
            try:
                self.db_manager.delete_sede(self.current_id)
                self.load_sedes()
                self.clear_form()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar: {e}")
