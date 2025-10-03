"""
Pantalla de splash para la aplicación PAL
"""
import tkinter as tk
from tkinter import ttk
from threading import Event

class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Cargando...")
        self.geometry("715x315")
        self.configure(bg="#000000")
        self.overrideredirect(True)
        
        # Centrar en pantalla
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 715) // 2
        y = (screen_height - 315) // 2
        self.geometry(f"+{x}+{y}")
        
        # Contenedor principal
        self.container = ttk.Frame(self)
        self.container.pack(expand=True, fill="both", padx=20, pady=20)
        
        try:
            self.logo = tk.PhotoImage(file="casapro-icono.png").subsample(2, 2)
            ttk.Label(self.container, image=self.logo).pack(pady=30)
        except Exception as e:
            tk.Label(self, text="[Imagen no disponible]", bg='black').pack(pady=10)
        
        # Texto de carga
        ttk.Label(self.container, 
                text="CPCapp 1.0BETA", 
                font=("Segoe UI", 12)).pack(pady=5)
        
        # Barra de progreso
        self.progress = ttk.Progressbar(self.container, 
                                      orient="horizontal",
                                      length=300,
                                      mode="determinate")
        self.progress.pack(pady=10)
        
        # Variables de control
        self.minimum_time_elapsed = Event()
        self.app_initialized = Event()
        self.progress_value = 0

    def start_animation(self):
        # Iniciar temporizador mínimo de 3 segundos
        self.after(3000, self.minimum_time_elapsed.set)
        
        # Iniciar animación de progreso
        self._update_progress()
        
        # Verificar estado combinado
        self._check_loading_status()

    def _update_progress(self):
        if self.progress_value < 100:
            self.progress_value += 1
            self.progress["value"] = self.progress_value
            self.after(30, self._update_progress)

    def _check_loading_status(self):
        if self.minimum_time_elapsed.is_set() and self.app_initialized.is_set():
            self.destroy()
        else:
            self.after(100, self._check_loading_status)