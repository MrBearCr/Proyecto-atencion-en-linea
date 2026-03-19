"""
Pantalla de splash para la aplicación PAL con login integrado.
"""
import tkinter as tk
from tkinter import ttk
from threading import Event, Thread
import sys
import os

class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Cargando...")
        # Reducir tamaño del splash para que sea más elegante
        self.splash_width = 750
        self.splash_height = 620
        self.geometry(f"{self.splash_width}x{self.splash_height}")
        self.minsize(self.splash_width, self.splash_height)
        
        # --- MODERN THEME COLORS (Light Mode) ---
        self.bg_color = "#FFFFFF"
        self.accent_color = "#10B981"  # Success Green
        self.brand_blue = "#004C97"    # Azul para textos importantes
        self.text_primary = "#1F2937"
        self.text_secondary = "#4B5563"
        self.input_bg = "#FFFFFF"      # Blanco como pidió el usuario
        self.border_color = "#E5E7EB"
        self.input_border = "#D1D5DB"  # Borde para los campos
        
        self.configure(bg=self.bg_color)
        self.overrideredirect(True)
        
        # Configurar estilos locales para el splash
        self._setup_local_styles()
        
        # Barra superior personalizada
        self.topbar = tk.Frame(self, bg=self.bg_color, height=32)
        self.topbar.pack(fill="x", side="top")
        
        self.close_btn = tk.Label(
            self.topbar, 
            text="✕", 
            fg=self.text_secondary, 
            bg=self.bg_color, 
            cursor="hand2", 
            font=("Segoe UI", 11)
        )
        self.close_btn.pack(side="right", padx=12, pady=5)
        self.close_btn.bind("<Button-1>", lambda e: self._on_close())
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.config(fg="#EF4444", bg="#FEE2E2"))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.config(fg=self.text_secondary, bg=self.bg_color))
        
        # Borde decorativo
        tk.Frame(self, bg=self.border_color).pack(fill="x", side="bottom", ipady=1)
        tk.Frame(self, bg=self.border_color).pack(fill="y", side="right", ipadx=1)
        tk.Frame(self, bg=self.border_color).pack(fill="y", side="left", ipadx=1)
        tk.Frame(self, bg=self.border_color).pack(fill="x", side="top", ipady=1)

        # Centrar en pantalla
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - self.splash_width) // 2
        y = (screen_height - self.splash_height) // 2
        self.geometry(f"+{x}+{y}")
        
        # Contenedor principal
        self.container = ttk.Frame(self, style="Splash.TFrame")
        self.container.pack(expand=True, fill="both", padx=50, pady=20)
        
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            image_path = os.path.join(base_path, "casapro-icono.png")
            self.logo = tk.PhotoImage(file=image_path).subsample(2, 2)
            tk.Label(self.container, image=self.logo, bg=self.bg_color).pack(pady=(5, 15))
        except Exception as e:
            tk.Label(self.container, text="NEXUS", bg=self.bg_color, fg=self.brand_blue, font=("Segoe UI", 22, "bold")).pack(pady=15)
        
        # Textos informativos
        tk.Label(self.container, 
                  text="Casapro Nexus", 
                  font=("Segoe UI", 20, "bold"),
                  bg=self.bg_color,
                  fg=self.text_primary).pack()
        
        tk.Label(self.container, 
                  text="Plataforma de Administración Local", 
                  font=("Segoe UI", 11),
                  bg=self.bg_color,
                  fg=self.text_secondary).pack(pady=(0, 20))
        
        # Barra de progreso VERDE
        self.progress = ttk.Progressbar(self.container, 
                                        orient="horizontal",
                                        length=400,
                                        mode="determinate",
                                        style="Splash.Horizontal.TProgressbar")
        self.progress.pack(pady=10)
        
        # Panel de login
        self.login_frame = tk.Frame(self.container, bg=self.bg_color)
        
        # Campos de login: Usamos 'font' y un color de fondo para que se distingan
        label_font = ("Segoe UI", 9, "bold")
        entry_font = ("Segoe UI", 11)
        
        tk.Label(self.login_frame, text="USUARIO", font=label_font, bg=self.bg_color, fg=self.text_secondary).grid(row=0, column=0, sticky="w", pady=(0, 2))
        
        # Un frame contenedor con borde para que el campo blanco se distinga
        user_container = tk.Frame(self.login_frame, bg=self.input_border, padx=1, pady=1)
        user_container.grid(row=1, column=0, pady=(0, 15), sticky="ew")
        self.username = tk.Entry(user_container, font=entry_font, bg=self.input_bg, relief="flat", borderwidth=0, insertbackground=self.text_primary)
        self.username.pack(fill="x", padx=1, pady=1) # Pequeño margen interno para simular borde
        # Inner padding real
        inner_user = tk.Frame(self.username, bg=self.input_bg)
        # Nota: tk.Entry no soporta widgets hijos fácilmente para padding, usamos relief y borderwidth estándar mejor
        self.username.configure(highlightthickness=1, highlightbackground=self.input_border, highlightcolor=self.brand_blue)
        self.username.pack(fill="x", ipady=8) 
        self.username.bind("<Return>", self._username_enter)
        
        tk.Label(self.login_frame, text="CONTRASEÑA", font=label_font, bg=self.bg_color, fg=self.text_secondary).grid(row=2, column=0, sticky="w", pady=(0, 2))
        
        self.password = tk.Entry(self.login_frame, show="•", font=entry_font, bg=self.input_bg, relief="flat", borderwidth=0, insertbackground=self.text_primary, 
                                highlightthickness=1, highlightbackground=self.input_border, highlightcolor=self.brand_blue)
        self.password.grid(row=3, column=0, pady=(0, 20), sticky="ew", ipady=8)
        self.password.bind("<Return>", self._password_enter)
        
        self.btn_login = tk.Button(
            self.login_frame, 
            text="ACCEDER AL SISTEMA", 
            command=self._on_login_click, 
            state=tk.DISABLED,
            bg=self.brand_blue,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            cursor="hand2",
            pady=10
        )
        self.btn_login.grid(row=4, column=0, sticky="ew")
        
        self.btn_login.bind("<Enter>", lambda e: self.btn_login.config(bg="#003d7a") if self.btn_login['state'] != 'disabled' else None)
        self.btn_login.bind("<Leave>", lambda e: self.btn_login.config(bg=self.brand_blue) if self.btn_login['state'] != 'disabled' else None)
        
        self.login_status = tk.Label(self.login_frame, text="Preparando entorno...", font=("Segoe UI", 9), bg=self.bg_color, fg=self.text_secondary)
        self.login_status.grid(row=5, column=0, pady=(15, 0))
        
        self.bind("<Return>", self._on_enter)
        
        # --- MOUSE DRAGGING SUPPORT ---
        self._drag_data = {"x": 0, "y": 0}
        def _start_drag(event):
            self._drag_data["x"] = event.x
            self._drag_data["y"] = event.y
        def _do_drag(event):
            x = self.winfo_x() - self._drag_data["x"] + event.x
            y = self.winfo_y() - self._drag_data["y"] + event.y
            self.geometry(f"+{x}+{y}")
            
        # Bind to topbar and container to allow dragging from most areas
        self.topbar.bind("<Button-1>", _start_drag)
        self.topbar.bind("<B1-Motion>", _do_drag)
        self.container.bind("<Button-1>", _start_drag)
        self.container.bind("<B1-Motion>", _do_drag)
        # Also bind to labels inside container so they don't block dragging
        for widget in self.container.winfo_children():
            if isinstance(widget, tk.Label):
                widget.bind("<Button-1>", _start_drag)
                widget.bind("<B1-Motion>", _do_drag)
        
        # Variables de control
        self.minimum_time_elapsed = Event()
        self.app_initialized = Event()
        self.login_success = Event()
        self.progress_value = 0
        self.real_progress = False 
        self._login_handler = None

    def _setup_local_styles(self):
        style = ttk.Style()
        style.theme_use('alt')
        style.configure("Splash.TFrame", background=self.bg_color)
        
        # Barra de progreso VERDE
        style.configure(
            "Splash.Horizontal.TProgressbar",
            troughcolor="#F3F4F6", # Fondo de la barra gris claro
            background=self.accent_color, # Verde
            thickness=8,
            borderwidth=0
        )

    def set_progress(self, value: float):
        """
        Actualiza la barra de progreso con un valor específico (0.0 a 1.0).
        Esto detiene la animación de progreso simulada.
        """
        self.real_progress = True 
        self.progress_value = int(value * 100)
        self.progress["value"] = self.progress_value
        if self.progress_value >= 100:
            self.progress_value = 100
            self.progress["value"] = 100

    def start_animation(self):
        self.after(1000, self.minimum_time_elapsed.set)
        self._update_progress()
        self._check_loading_status()
    
    def _force_timeout(self):
        try:
            if self.winfo_exists() and not self.login_success.is_set():
                print("[SPLASH] Timeout: Cerrando splash por timeout de 30s")
                self.destroy()
        except Exception:
            pass

    def _update_progress(self):
        if self.real_progress:
            return
            
        if self.progress_value < 90:
            self.progress_value += 1
            self.progress["value"] = self.progress_value
            self.after(30, self._update_progress)

    def _check_loading_status(self):
        if self.minimum_time_elapsed.is_set() and self.app_initialized.is_set() and self.login_success.is_set():
            try:
                self.progress.pack_forget()
                self.after(300, self._finalize_splash)
            except Exception:
                self.destroy()
        else:
            self.after(100, self._check_loading_status)
    
    def _finalize_splash(self):
        """Finaliza el splash y muestra la ventana principal"""
        try:
            if hasattr(self, 'master') and self.master:
                self.master.deiconify()
        except Exception:
            pass
        self.destroy()

    def _on_close(self):
        """Cierra el splash y termina la aplicación durante la fase de login."""
        try:
            if hasattr(self, 'master') and self.master:
                self.master.destroy()
            else:
                self.destroy()
        except Exception:
            try:
                self.destroy()
            except Exception:
                pass

    def _on_enter(self, event=None):
        try:
            w = self.focus_get()
        except Exception:
            w = None
        try:
            if w not in (self.username, self.password):
                self.username.focus_set()
                return "break"
        except Exception:
            return "break"

    def _username_enter(self, event=None):
        try:
            self.password.focus_set()
        except Exception:
            pass
        return "break"

    def _password_enter(self, event=None):
        try:
            if str(self.btn_login['state']) != str(tk.DISABLED):
                self._on_login_click()
        except Exception:
            try:
                self._on_login_click()
            except Exception:
                pass
        return "break"

    def enable_login(self, login_handler):
        """Habilita el panel de login y asigna el handler de verificación."""
        self._login_handler = login_handler
        try:
            self.login_frame.pack(pady=10, padx=20)
            self.btn_login.config(state=tk.NORMAL)
            self.username.focus_set()
            self.login_status.config(text="Ingrese sus credenciales de acceso", fg=self.accent_color)
        except Exception:
            pass

    def _on_login_click(self):
        if not self._login_handler:
            return
        user = self.username.get().strip()
        pwd = self.password.get().strip()
        if not user or not pwd:
            self.login_status.config(text="Por favor complete todos los campos", fg="red")
            return
            
        self.btn_login.config(state=tk.DISABLED, bg="#9CA3AF")
        self.login_status.config(text="Verificando credenciales...", fg=self.accent_color)
        
        def _run():
            try:
                ok, msg = self._login_handler(user, pwd)
                def _done():
                    if ok:
                        self.login_status.config(text="¡Bienvenido!", fg="#10B981") # Use accent_color
                        self.login_success.set()
                    else:
                        # Clear password for security and feedback
                        self.password.delete(0, tk.END)
                        
                        # Visual error feedback
                        self.login_status.config(text=msg or "Credenciales inválidas", fg="#EF4444") # Red
                        self.username.config(highlightbackground="#EF4444")
                        self.password.config(highlightbackground="#EF4444")
                        
                        self.btn_login.config(state=tk.NORMAL, bg=self.brand_blue)
                        
                        # Reset border color after 2 seconds
                        def reset_borders():
                            if self.winfo_exists():
                                self.username.config(highlightbackground=self.input_border)
                                self.password.config(highlightbackground=self.input_border)
                        self.after(2000, reset_borders)
                self.after(0, _done)
            except Exception as e:
                def _err():
                    self.login_status.config(text=f"Error de sistema: {e}", fg="#EF4444")
                    self.btn_login.config(state=tk.NORMAL, bg=self.brand_blue)
                self.after(0, _err)
        Thread(target=_run, daemon=True).start()

