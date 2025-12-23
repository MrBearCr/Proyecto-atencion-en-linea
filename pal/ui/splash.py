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
        # Tamaño del splash ampliado para acomodar el login cómodamente
        self.splash_width = 900
        self.splash_height = 520
        self.geometry(f"{self.splash_width}x{self.splash_height}")
        self.minsize(self.splash_width, self.splash_height)
        self.configure(bg="#000000")
        self.overrideredirect(True)
        
        # Barra superior personalizada con botón de cierre
        self.topbar = tk.Frame(self, bg="#111111", height=32)
        self.topbar.pack(fill="x", side="top")
        self.close_btn = tk.Label(self.topbar, text="✕", fg="white", bg="#111111", cursor="hand2", font=("Segoe UI", 12, "bold"))
        self.close_btn.pack(side="right", padx=8, pady=4)
        self.close_btn.bind("<Button-1>", lambda e: self._on_close())
        
        # Centrar en pantalla
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - self.splash_width) // 2
        y = (screen_height - self.splash_height) // 2
        self.geometry(f"+{x}+{y}")
        
        # Contenedor principal
        self.container = ttk.Frame(self)
        self.container.pack(expand=True, fill="both", padx=24, pady=24)
        
        try:
            # Handle PyInstaller bundled resources
            if getattr(sys, 'frozen', False):
                # Running as compiled exe
                base_path = sys._MEIPASS
            else:
                # Running as script
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            image_path = os.path.join(base_path, "casapro-icono.png")
            self.logo = tk.PhotoImage(file=image_path).subsample(2, 2)
            ttk.Label(self.container, image=self.logo).pack(pady=16)
        except Exception as e:
            print(f"Error loading splash image: {e}")
            tk.Label(self, text="[Imagen no disponible]", bg='black', fg='white').pack(pady=10)
        
        # Texto de carga
        ttk.Label(self.container, 
                  text="Casapro Nexus - Plataforma de Administracion local", 
                  font=("Segoe UI", 13)).pack(pady=4)
        
        # Barra de progreso
        self.progress = ttk.Progressbar(self.container, 
                                        orient="horizontal",
                                        length=420,
                                        mode="determinate")
        self.progress.pack(pady=10)
        
        # Panel de login (inicialmente oculto hasta que la app habilite)
        self.login_frame = ttk.Frame(self.container)
        # Configurar grid para que las entradas se expandan
        self.login_frame.columnconfigure(0, weight=0)
        self.login_frame.columnconfigure(1, weight=1)
        # Campos
        row = 0
        ttk.Label(self.login_frame, text="Usuario:").grid(row=row, column=0, sticky="e", padx=8, pady=6)
        self.username = ttk.Entry(self.login_frame)
        self.username.grid(row=row, column=1, sticky="ew", pady=6)
        # Enter en usuario -> pasa a contraseña
        self.username.bind("<Return>", self._username_enter)
        row += 1
        ttk.Label(self.login_frame, text="Contraseña:").grid(row=row, column=0, sticky="e", padx=8, pady=6)
        self.password = ttk.Entry(self.login_frame, show="*")
        self.password.grid(row=row, column=1, sticky="ew", pady=6)
        # Enter en contraseña -> invoca login
        self.password.bind("<Return>", self._password_enter)
        row += 1
        self.btn_login = ttk.Button(self.login_frame, text="Entrar", command=self._on_login_click, state=tk.DISABLED)
        self.btn_login.grid(row=row, column=1, sticky="e", pady=10)
        row += 1
        self.login_status = ttk.Label(self.login_frame, text="Esperando conexión...", foreground="#888")
        self.login_status.grid(row=row, column=0, columnspan=2, sticky="w", padx=8)
        # Enter global -> si el foco no está en usuario/clave, enfocar usuario
        self.bind("<Return>", self._on_enter)
        
        # Variables de control
        self.minimum_time_elapsed = Event()
        self.app_initialized = Event()
        self.login_success = Event()
        self.progress_value = 0
        self.real_progress = False  # Flag to indicate real progress reporting
        self._login_handler = None
        
        # Asegurar buen layout del panel de login dentro del contenedor
        # (se mostrará con enable_login)

    def set_progress(self, value: float):
        """
        Actualiza la barra de progreso con un valor específico (0.0 a 1.0).
        Esto detiene la animación de progreso simulada.
        """
        self.real_progress = True  # Marcar que estamos usando progreso real
        self.progress_value = int(value * 100)
        self.progress["value"] = self.progress_value
        # Si la descarga se completa, asegurarse de que la barra llegue al 100%
        if self.progress_value >= 100:
            self.progress_value = 100
            self.progress["value"] = 100

    def start_animation(self):
        # Temporizador mínimo de 3 segundos
        self.after(3000, self.minimum_time_elapsed.set)
        # Animación de progreso
        self._update_progress()
        # Verificación periódica
        self._check_loading_status()
    
    def _force_timeout(self):
        """Fuerza el cierre del splash si se queda colgado."""
        try:
            if self.winfo_exists() and not self.login_success.is_set():
                print("[SPLASH] Timeout: Cerrando splash por timeout de 30s")
                self.destroy()
        except Exception:
            pass

    def _update_progress(self):
        # No animar si estamos recibiendo progreso real
        if self.real_progress:
            return
            
        if self.progress_value < 90: # Simular hasta el 90%
            self.progress_value += 1
            self.progress["value"] = self.progress_value
            self.after(30, self._update_progress)

    def _check_loading_status(self):
        # Cerrar solo cuando: tiempo mínimo + app inicializada + login OK
        if self.minimum_time_elapsed.is_set() and self.app_initialized.is_set() and self.login_success.is_set():
            try:
                # Ocultar barra de progreso antes de cerrar
                self.progress.pack_forget()
                # Pequeña pausa para suavizar transición
                self.after(300, self._finalize_splash)
            except Exception:
                self.destroy()
        else:
            self.after(100, self._check_loading_status)
    
    def _finalize_splash(self):
        """Finaliza el splash y muestra la ventana principal"""
        try:
            # Mostrar la ventana principal al cerrar el splash
            if hasattr(self, 'master') and self.master:
                self.master.deiconify()
        except Exception:
            pass
        self.destroy()

    def _on_close(self):
        """Cierra el splash y termina la aplicación durante la fase de login."""
        try:
            if hasattr(self, 'master') and self.master:
                # Destruir aplicación completa si se cierra desde el splash
                self.master.destroy()
            else:
                self.destroy()
        except Exception:
            try:
                self.destroy()
            except Exception:
                pass

    def _on_enter(self, event=None):
        """Manejo global de Enter durante el login: enfoca el campo correcto."""
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
        """Enter en usuario -> pasar a contraseña"""
        try:
            self.password.focus_set()
        except Exception:
            pass
        return "break"

    def _password_enter(self, event=None):
        """Enter en contraseña -> intentar login"""
        try:
            # Solo si el botón está habilitado, para evitar dobles envíos
            if str(self.btn_login['state']) != str(tk.DISABLED):
                self._on_login_click()
            else:
                # Si está deshabilitado, no hacer nada
                pass
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
            # Asegurar que el frame ocupe buen ancho
            self.login_frame.pack(pady=12, padx=24, fill="x")
            self.btn_login.config(state=tk.NORMAL)
            self.username.focus_set()
            self.login_status.config(text="Ingrese sus credenciales", foreground="#004C97")
        except Exception:
            pass

    def _on_login_click(self):
        if not self._login_handler:
            return
        user = self.username.get().strip()
        pwd = self.password.get().strip()
        if not user or not pwd:
            self.login_status.config(text="Complete usuario y contraseña", foreground="red")
            return
        # Deshabilitar botón y mostrar estado
        self.btn_login.config(state=tk.DISABLED)
        self.login_status.config(text="Verificando...", foreground="#004C97")
        
        def _run():
            try:
                ok, msg = self._login_handler(user, pwd)
                def _done():
                    if ok:
                        self.login_status.config(text="Login exitoso", foreground="green")
                        self.login_success.set()
                    else:
                        self.login_status.config(text=msg or "Credenciales inválidas", foreground="red")
                        self.btn_login.config(state=tk.NORMAL)
                self.after(0, _done)
            except Exception as e:
                def _err():
                    self.login_status.config(text=f"Error: {e}", foreground="red")
                    self.btn_login.config(state=tk.NORMAL)
                self.after(0, _err)
        Thread(target=_run, daemon=True).start()
