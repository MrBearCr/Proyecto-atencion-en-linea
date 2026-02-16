
import tkinter as tk
from tkinter import ttk
from pal.ui.tabs.clientes_reportes import ClientesReportesTab
from pal.ui.tabs.clientes_estadisticas import ClientesEstadisticasTab

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
        inner.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        tk.Label(
            inner,
            text=icon,
            font=("Segoe UI", 42),
            bg="#FFFFFF"
        ).pack(pady=(5, 12))
        
        tk.Label(
            inner,
            text=name.upper(),
            font=("Segoe UI", 12, "bold"),
            foreground="#111827",
            bg="#FFFFFF"
        ).pack()

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
        Abre el submódulo de estadísticas de clientes.
        """
        self.controller.show_clientes_sub_view('estadisticas')
        self.controller.log("Abriendo submódulo de Estadísticas de Clientes...", "INFO")


