"""
Módulo de header, estilos y widget de notificaciones para la aplicación PAL.

Incluye:
  - setup_styles()       — Configura los estilos ttk de la aplicación.
  - create_header()      — Crea el header con degradado y menú de usuario.
  - NotificationBell     — Widget de campana 🔔 con badge y panel desplegable.
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# Colores por prioridad
# ──────────────────────────────────────────────────────────────────────────────
PRIORITY_COLORS = {
    "urgent":  {"bg": "#f8d7da", "fg": "#721c24", "badge": "#dc3545", "icon": "🔴"},
    "warning": {"bg": "#fff3cd", "fg": "#856404", "badge": "#fd7e14", "icon": "🟠"},
    "info":    {"bg": "#d1ecf1", "fg": "#0c5460", "badge": "#17a2b8", "icon": "🔵"},
    "success": {"bg": "#d4edda", "fg": "#155724", "badge": "#28a745", "icon": "🟢"},
}
DEFAULT_COLOR = {"bg": "#e9ecef", "fg": "#343a40", "badge": "#6c757d", "icon": "⚪"}


def _fmt_timestamp(ts) -> str:
    """Formatea un timestamp como 'hace X min' o fecha corta."""
    if ts is None:
        return ""
    try:
        now = datetime.now()
        diff = now - ts
        secs = int(diff.total_seconds())
        if secs < 60:
            return "ahora"
        if secs < 3600:
            return f"hace {secs // 60} min"
        if secs < 86400:
            return f"hace {secs // 3600} h"
        return ts.strftime("%d/%m %H:%M")
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# Widget de campana de notificaciones
# ──────────────────────────────────────────────────────────────────────────────

class NotificationBell:
    """
    Widget de campana 🔔 con badge numérico y panel desplegable de notificaciones.

    Cada tarjeta de notificación muestra:
      - Icono de prioridad + título + módulo
      - Mensaje (truncado a 2 líneas)
      - Timestamp relativo
      - Botón "Tratar" (si notification.tiene_accion_tratar)
      - Botón "×" para descartar

    Uso:
        bell = NotificationBell(parent_frame, notification_manager, navigate_fn)
        bell.pack(side=tk.RIGHT, padx=8)

    Args:
        parent:              Frame contenedor (normalmente el header).
        notification_manager: Instancia de NotificationManager.
        navigate_fn:         Callable(modulo_ruta: str) que cambia la pestaña activa.
        usuario_actual:      Nombre del usuario logueado (para mark_as_treated).
    """

    PANEL_WIDTH  = 380
    PANEL_HEIGHT = 480
    MAX_CARDS    = 20

    def __init__(
        self,
        parent,
        notification_manager,
        navigate_fn=None,
        usuario_actual: Optional[str] = None,
    ):
        self._mgr          = notification_manager
        self._navigate_fn  = navigate_fn
        self._usuario      = usuario_actual
        self._panel_open   = False
        self._panel_win: Optional[tk.Toplevel] = None

        self._frame = tk.Frame(parent, bg="#004C97", cursor="hand2")

        self._btn = tk.Label(
            self._frame,
            text="🔔",
            font=("Segoe UI", 16),
            bg="#004C97",
            fg="white",
            cursor="hand2",
        )
        self._btn.pack(side=tk.LEFT)

        self._badge_var = tk.StringVar(value="")
        self._badge = tk.Label(
            self._frame,
            textvariable=self._badge_var,
            font=("Segoe UI", 7, "bold"),
            bg="#dc3545",
            fg="white",
            width=2,
            relief="flat",
        )

        self._btn.bind("<Button-1>",   self._toggle_panel)
        self._badge.bind("<Button-1>", self._toggle_panel)

        self._mgr.add_observer(self._on_notifications_changed)

        self._refresh_badge()

    def pack(self, **kwargs):
        self._frame.pack(**kwargs)

    def grid(self, **kwargs):
        self._frame.grid(**kwargs)

    def place(self, **kwargs):
        self._frame.place(**kwargs)

    def _refresh_badge(self):
        try:
            count = self._mgr.get_unread_count()
            if count > 0:
                label = str(count) if count < 100 else "99+"
                self._badge_var.set(label)
                self._badge.place(relx=0.6, rely=0.0, anchor="nw")
            else:
                self._badge_var.set("")
                self._badge.place_forget()
        except Exception:
            pass

    def _on_notifications_changed(self):
        try:
            self._frame.after(0, self._refresh_badge)
            if self._panel_open and self._panel_win and self._panel_win.winfo_exists():
                self._frame.after(0, self._rebuild_panel_content)
        except Exception:
            pass

    def _toggle_panel(self, event=None):
        if self._panel_open:
            self._close_panel()
        else:
            self._open_panel()

    def _open_panel(self):
        if self._panel_win and self._panel_win.winfo_exists():
            self._panel_win.lift()
            return

        bx = self._btn.winfo_rootx()
        by = self._btn.winfo_rooty() + self._btn.winfo_height() + 4
        screen_w = self._btn.winfo_screenwidth()
        px = min(bx, screen_w - self.PANEL_WIDTH - 10)

        win = tk.Toplevel(self._frame)
        win.wm_overrideredirect(True)
        win.attributes("-topmost", True)
        win.geometry(f"{self.PANEL_WIDTH}x{self.PANEL_HEIGHT}+{px}+{by}")
        win.configure(bg="white")

        outer = tk.Frame(win, bg="#ced4da", bd=1, relief="solid")
        outer.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        header_f = tk.Frame(outer, bg="#004C97")
        header_f.pack(fill=tk.X)

        tk.Label(
            header_f,
            text="🔔  Notificaciones",
            font=("Segoe UI", 11, "bold"),
            bg="#004C97",
            fg="white",
            padx=10,
            pady=8,
        ).pack(side=tk.LEFT)

        tk.Button(
            header_f,
            text="✓ Todo leído",
            font=("Segoe UI", 8),
            bg="#0066CC",
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=4,
            command=self._mark_all_read,
        ).pack(side=tk.RIGHT, padx=6, pady=4)

        tk.Button(
            header_f,
            text="✕",
            font=("Segoe UI", 10, "bold"),
            bg="#004C97",
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=6,
            command=self._close_panel,
        ).pack(side=tk.RIGHT, padx=2, pady=4)

        self._cards_outer = tk.Frame(outer, bg="white")
        self._cards_outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(self._cards_outer, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._cards_outer, orient="vertical", command=canvas.yview)
        self._cards_frame = tk.Frame(canvas, bg="white")

        self._cards_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=self._cards_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._canvas_ref = canvas
        self._panel_win  = win
        self._panel_open = True

        win.bind("<FocusOut>", self._on_focus_out)

        self._rebuild_panel_content()

    def _close_panel(self, event=None):
        self._panel_open = False
        if self._panel_win and self._panel_win.winfo_exists():
            self._panel_win.destroy()
        self._panel_win = None

    def _on_focus_out(self, event=None):
        try:
            if self._panel_win and self._panel_win.winfo_exists():
                self._panel_win.after(150, self._check_focus_and_close)
        except Exception:
            pass

    def _check_focus_and_close(self):
        try:
            if self._panel_win and self._panel_win.winfo_exists():
                focused = self._panel_win.focus_get()
                if focused is None:
                    self._close_panel()
        except Exception:
            self._close_panel()

    def _rebuild_panel_content(self):
        if not (self._panel_win and self._panel_win.winfo_exists()):
            return

        for widget in self._cards_frame.winfo_children():
            widget.destroy()

        notifications = self._mgr.get_notifications()[:self.MAX_CARDS]

        if not notifications:
            tk.Label(
                self._cards_frame,
                text="✅  Sin notificaciones pendientes",
                font=("Segoe UI", 10),
                fg="#6c757d",
                bg="white",
                pady=30,
            ).pack(fill=tk.X, padx=20)
            return

        for notif in notifications:
            self._build_card(notif)

        self._cards_frame.update_idletasks()
        if self._canvas_ref:
            self._canvas_ref.configure(scrollregion=self._canvas_ref.bbox("all"))

    def _build_card(self, notif):
        colors = PRIORITY_COLORS.get(notif.priority.value, DEFAULT_COLOR)

        card_bg = colors["bg"] if not notif.read else "#f8f9fa"
        fg_main = colors["fg"] if not notif.read else "#495057"

        card = tk.Frame(
            self._cards_frame,
            bg=card_bg,
            bd=1,
            relief="solid",
            highlightbackground="#dee2e6",
            highlightthickness=1,
        )
        card.pack(fill=tk.X, padx=6, pady=3)

        accent = tk.Frame(card, bg=colors["badge"], width=4)
        accent.pack(side=tk.LEFT, fill=tk.Y)

        content = tk.Frame(card, bg=card_bg, padx=8, pady=6)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        row1 = tk.Frame(content, bg=card_bg)
        row1.pack(fill=tk.X)

        tk.Label(
            row1,
            text=colors["icon"],
            font=("Segoe UI", 10),
            bg=card_bg,
        ).pack(side=tk.LEFT)

        tk.Label(
            row1,
            text=notif.title,
            font=("Segoe UI", 9, "bold"),
            fg=fg_main,
            bg=card_bg,
            anchor="w",
        ).pack(side=tk.LEFT, padx=(4, 0))

        tk.Label(
            row1,
            text=f"[{notif.module}]",
            font=("Segoe UI", 7),
            fg="#6c757d",
            bg=card_bg,
        ).pack(side=tk.LEFT, padx=(4, 0))

        tk.Label(
            row1,
            text=_fmt_timestamp(notif.timestamp),
            font=("Segoe UI", 7),
            fg="#adb5bd",
            bg=card_bg,
            anchor="e",
        ).pack(side=tk.RIGHT)

        msg = notif.message
        if len(msg) > 120:
            msg = msg[:117] + "…"
        tk.Label(
            content,
            text=msg,
            font=("Segoe UI", 8),
            fg=fg_main,
            bg=card_bg,
            anchor="w",
            justify="left",
            wraplength=self.PANEL_WIDTH - 60,
        ).pack(fill=tk.X, pady=(2, 4))

        if notif.treated:
            tk.Label(
                content,
                text="✔ Tratada",
                font=("Segoe UI", 7, "italic"),
                fg="#28a745",
                bg=card_bg,
            ).pack(anchor="w")

        btn_row = tk.Frame(content, bg=card_bg)
        btn_row.pack(fill=tk.X, pady=(0, 2))

        if notif.tiene_accion_tratar and not notif.treated:
            btn_label = notif.accion_etiqueta or "Tratar"
            tk.Button(
                btn_row,
                text=f"→ {btn_label}",
                font=("Segoe UI", 8, "bold"),
                bg=colors["badge"],
                fg="white",
                relief="flat",
                cursor="hand2",
                padx=8,
                pady=2,
                command=lambda n=notif: self._on_tratar(n),
            ).pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(
            btn_row,
            text="× Descartar",
            font=("Segoe UI", 8),
            bg="#e9ecef",
            fg="#6c757d",
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=2,
            command=lambda n=notif: self._on_dismiss(n),
        ).pack(side=tk.LEFT)

        ttk.Separator(self._cards_frame, orient="horizontal").pack(
            fill=tk.X, padx=6, pady=0
        )

    def _on_tratar(self, notif):
        try:
            self._mgr.mark_as_treated(notif.id, usuario=self._usuario)
        except Exception as e:
            print(f"[NotificationBell] Error marcando como tratada: {e}")

        self._close_panel()

        if self._navigate_fn and notif.modulo_ruta:
            try:
                self._navigate_fn(notif.modulo_ruta)
            except Exception as e:
                print(f"[NotificationBell] Error navegando a '{notif.modulo_ruta}': {e}")

    def _on_dismiss(self, notif):
        try:
            self._mgr.dismiss_notification(notif.id)
        except Exception as e:
            print(f"[NotificationBell] Error descartando: {e}")

    def _mark_all_read(self):
        try:
            self._mgr.mark_all_as_read()
        except Exception as e:
            print(f"[NotificationBell] Error marcando todas como leídas: {e}")

    def set_usuario(self, usuario: str):
        """Actualiza el usuario actual (llamar después del login)."""
        self._usuario = usuario


# ──────────────────────────────────────────────────────────────────────────────
# Estilos
# ──────────────────────────────────────────────────────────────────────────────

def setup_styles(app):
    """Configurar los estilos de la aplicación"""
    app.style = ttk.Style()
    app.style.theme_create("modern", parent="alt", settings={
        "TFrame": {"configure": {"background": "#F5F6F8"}},
        "TNotebook": {"configure": {"background": "#FFFFFF"}},
        "TButton": {"configure": {"padding": 6, "font": ("Segoe UI", 10)}},
        "TNotebook.Tab": {
            "configure": {"padding": (15, 5), "background": "#e9ecef"},
            "map": {"background": [("selected", "#004C97")], "foreground": [("selected", "white")]}
        }
    })
    app.style.theme_use("alt")
    
    # Configuraciones específicas
    app.style.configure("Header.TFrame", background="white")
    app.style.configure("Sidebar.TFrame", background="#e9ecef")
    app.style.configure("Nav.TButton", 
                    font=("Segoe UI", 11), 
                    anchor="w",
                    padding=(20, 10),
                    background="#e9ecef")
    app.style.map("Nav.TButton",
                background=[("active", "#004C97"), ("!active", "#e9ecef")],
                foreground=[("active", "white")])
    
    app.style.configure("Disabled.TButton", 
                foreground="#666666",
                background="#e0e0e0")
    
    # Estilos modernos para dashboard
    app.style.configure("Accent.TButton",
                font=("Segoe UI", 10),
                padding=(15, 8),
                relief="flat",
                borderwidth=1)
    app.style.map("Accent.TButton",
                background=[("active", "#003d7a"), ("!active", "#004C97")],
                foreground=[("active", "white"), ("!active", "white")],
                relief=[("pressed", "sunken")])
    
    app.style.configure("ModuleCard.TButton",
                font=("Segoe UI", 9),
                padding=(10, 5),
                relief="flat")
    app.style.map("ModuleCard.TButton",
                background=[("active", "#004C97"), ("!active", "#F3F4F6")],
                foreground=[("active", "white"), ("!active", "#004C97")])
    
    app.style.configure(
        "HeaderMenu.TMenubutton",
        background="#004C97",
        foreground="white",
        font=("Segoe UI", 12),
        relief="flat"
    )
    app.style.map("HeaderMenu.TMenubutton",
                background=[("active", "#0066CC")],
                foreground=[("active", "white")]
    )

# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────

def create_header(app):
    """Crear el header de la aplicación"""
    header_canvas = tk.Canvas(
        app.root, 
        bg="#004C97",
        height=80,
        highlightthickness=0
    )
    header_canvas.pack(fill=tk.X)

    # Generar degradado
    for i in range(80):
        intensity = i / 80
        r = int(0 * (1 - intensity) + 0 * intensity)
        g = int(76 * (1 - intensity) + 45 * intensity)
        b = int(151 * (1 - intensity) + 92 * intensity)
        color = f"#{r:02x}{g:02x}{b:02x}"
        header_canvas.create_line(0, i, 2000, i, fill=color)

    # Añadir texto
    text_y = 80 // 2
    header_canvas.create_text(
        20, 
        text_y,
        text="Gestión de Clientes",
        fill="white",
        font=("Segoe UI", 14, "bold"),
        anchor="w"
    )
    
    # Menú de usuario
    app.user_menu = ttk.Menubutton(header_canvas, text="☰", style="HeaderMenu.TMenubutton")
    menu = tk.Menu(app.user_menu, tearoff=0)
    menu.add_command(label="Configuración", command=app.show_settings)
    menu.add_command(label="Salir", command=app.root.quit)
    app.user_menu['menu'] = menu
    app.user_menu.pack(side=tk.RIGHT, padx=20, pady=10)

    # Widget de campana de notificaciones
    app.notification_bell = None
    if hasattr(app, "notification_manager") and app.notification_manager is not None:
        try:
            navigate_fn = getattr(app, "navigate_to_module", None)
            usuario = getattr(app, "current_user", None)
            if usuario and hasattr(usuario, "username"):
                usuario = usuario.username

            bell = NotificationBell(
                parent=header_canvas,
                notification_manager=app.notification_manager,
                navigate_fn=navigate_fn,
                usuario_actual=usuario,
            )
            bell.pack(side=tk.RIGHT, padx=4, pady=10)
            app.notification_bell = bell
        except Exception as e:
            print(f"[header] Error creando NotificationBell: {e}")
