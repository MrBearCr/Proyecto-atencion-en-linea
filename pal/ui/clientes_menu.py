
import tkinter as tk
from tkinter import ttk
from pal.ui.tabs.clientes_reportes import ClientesReportesTab

class ClientesMenu(ttk.Frame):
    """
    Un frame que muestra el menú de submódulos para el módulo de Clientes,
    utilizando un diseño de tarjetas similar al dashboard principal.
    """
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        
        # Asigna un estilo al frame principal para que coincida con el fondo del dashboard
        self.configure(style="Dashboard.TFrame")

        # Configuración del grid para centrar las tarjetas
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Crear las tarjetas de submódulos
        self.create_widgets()

    def _create_module_card(self, parent, icon, name, command):
        """
        Crea una tarjeta de módulo con estilo, que actúa como un botón.
        """
        card_frame = tk.Frame(
            parent,
            bg="#FFFFFF",
            relief=tk.RAISED,
            bd=1,
            cursor="hand2"
        )
        
        inner = tk.Frame(card_frame, bg="#FFFFFF")
        inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(
            inner,
            text=icon,
            font=("Segoe UI", 36),
            bg="#FFFFFF"
        ).pack(pady=(10, 12))
        
        tk.Label(
            inner,
            text=name,
            font=("Segoe UI", 14, "bold"),
            foreground="#1F2937",
            bg="#FFFFFF"
        ).pack()

        # --- Handlers de eventos ---
        def on_enter(e):
            card_frame.configure(relief=tk.SUNKEN, bd=2, bg="#F3F4F6")
            inner.configure(bg="#F3F4F6")
            for widget in inner.winfo_children():
                widget.configure(bg="#F3F4F6")

        def on_leave(e):
            card_frame.configure(relief=tk.RAISED, bd=1, bg="#FFFFFF")
            inner.configure(bg="#FFFFFF")
            for widget in inner.winfo_children():
                widget.configure(bg="#FFFFFF")
        
        # --- Bindings ---
        # Vincular eventos a todos los componentes de la tarjeta
        for widget in [card_frame, inner] + inner.winfo_children():
             widget.bind("<Enter>", on_enter)
             widget.bind("<Leave>", on_leave)
             widget.bind("<Button-1>", lambda e, cmd=command: cmd())
        
        return card_frame

    def create_widgets(self):
        """
        Crea y posiciona las tarjetas de submódulos en el frame.
        """
        # Contenedor para centrar las tarjetas
        center_frame = ttk.Frame(self)
        center_frame.pack(fill=tk.BOTH, expand=True)

        # Contenedor interno para las tarjetas (para el side=tk.LEFT)
        cards_inner_frame = ttk.Frame(center_frame)
        cards_inner_frame.pack(fill=tk.X, expand=False, pady=20)
        
        # Tarjeta para "Reportes"
        reportes_card = self._create_module_card(
            cards_inner_frame,
            icon="📄",
            name="Reportes",
            command=self.open_reportes
        )
        reportes_card.pack(side=tk.LEFT, padx=8, pady=8, fill=tk.BOTH, expand=True)

        # Tarjeta para "Estadísticas"
        estadisticas_card = self._create_module_card(
            cards_inner_frame,
            icon="📊",
            name="Estadísticas",
            command=self.open_estadisticas
        )
        estadisticas_card.pack(side=tk.LEFT, padx=8, pady=8, fill=tk.BOTH, expand=True)

    def open_reportes(self):
        """
        Abre el submódulo de reportes de clientes cambiando la vista.
        """
        self.controller.show_clientes_sub_view('reportes')
        self.controller.log("Abriendo submódulo de Reportes de Clientes...", "INFO")

    def open_estadisticas(self):
        """
        Placeholder para la acción de abrir el submódulo de estadísticas.
        """
        print("Abriendo submódulo de Estadísticas de Clientes...")
        # Lógica futura: self.controller.show_frame("ClientesEstadisticas")


