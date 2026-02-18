
import tkinter as tk
from tkinter import ttk

class AdminMenu(ttk.Frame):
    """
    Menú de tarjetas para el módulo de Administración (Configuraciones Globales).
    """
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.configure(style="Dashboard.TFrame")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.create_widgets()

    def _create_module_card(self, parent, icon, name, desc, command):
        """
        Crea una tarjeta de módulo con estilo visual moderno (estilo Windows/Web).
        """
        self.accent_color = "#004C97"  # Brand Blue
        self.bg_hover = "#F9FAFB"
        self.border_normal = "#E5E7EB"
        self.border_hover = "#004C97"
        
        card_frame = tk.Frame(
            parent,
            bg="#FFFFFF",
            highlightthickness=1,
            highlightbackground=self.border_normal,
            cursor="hand2"
        )
        
        inner = tk.Frame(card_frame, bg="#FFFFFF")
        inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(
            inner,
            text=icon,
            font=("Segoe UI", 32),
            bg="#FFFFFF"
        ).pack(pady=(0, 10))
        
        tk.Label(
            inner,
            text=name.upper(),
            font=("Segoe UI", 11, "bold"),
            foreground="#111827",
            bg="#FFFFFF"
        ).pack()

        tk.Label(
            inner,
            text=desc,
            font=("Segoe UI", 9),
            foreground="#6B7280",
            bg="#FFFFFF",
            wraplength=160,
            justify="center"
        ).pack(pady=(5, 0))

        def on_enter(e):
            card_frame.configure(highlightbackground=self.border_hover, highlightthickness=2)
            card_frame.configure(bg=self.bg_hover)
            inner.configure(bg=self.bg_hover)
            for widget in inner.winfo_children():
                widget.configure(bg=self.bg_hover)

        def on_leave(e):
            card_frame.configure(highlightbackground=self.border_normal, highlightthickness=1)
            card_frame.configure(bg="#FFFFFF")
            inner.configure(bg="#FFFFFF")
            for widget in inner.winfo_children():
                widget.configure(bg="#FFFFFF")
        
        for widget in [card_frame, inner] + inner.winfo_children():
             widget.bind("<Enter>", on_enter)
             widget.bind("<Leave>", on_leave)
             widget.bind("<Button-1>", lambda e, cmd=command: cmd())
        
        return card_frame

    def create_widgets(self):
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Usar un flow layout simple (grid) para las tarjetas
        cards_frame = ttk.Frame(container)
        cards_frame.pack(anchor="center")

        # --- Fila 1 ---
        # 1. Sedes (Servidores VAD20)
        self._create_module_card(
            cards_frame, "🖥️", "Servidores", "Configurar conexiones remotas (VAD20)",
            lambda: self.controller.show_admin_sub_view('sedes_servidores')
        ).grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # 2. Almacenes (Quiebre de Stock)
        self._create_module_card(
            cards_frame, "📦", "Almacenes", "Definir depósitos tratables por sede",
            lambda: self.controller.show_admin_sub_view('sedes_almacenes')
        ).grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # 3. Exclusiones
        self._create_module_card(
            cards_frame, "🚫", "Exclusiones", "Departamentos excluidos de reportes",
            lambda: self.controller.show_admin_sub_view('exclusiones')
        ).grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        # --- Fila 2 ---
        # 4. Usuarios
        self._create_module_card(
            cards_frame, "👤", "Usuarios", "Gestión de cuentas y accesos",
            lambda: self.controller.show_admin_sub_view('usuarios')
        ).grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # 5. Roles
        self._create_module_card(
            cards_frame, "🔑", "Roles", "Permisos y niveles de seguridad",
            lambda: self.controller.show_admin_sub_view('roles')
        ).grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        # 6. Auditoría
        self._create_module_card(
            cards_frame, "📜", "Auditoría", "Historial de acciones del sistema",
            lambda: self.controller.show_admin_sub_view('auditoria')
        ).grid(row=1, column=2, padx=10, pady=10, sticky="nsew")

        # --- Fila 3 ---
        # 7. Temas
        self._create_module_card(
            cards_frame, "🎨", "Temas", "Personalizar la apariencia de la UI",
            lambda: self.controller.show_admin_sub_view('temas')
        ).grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
