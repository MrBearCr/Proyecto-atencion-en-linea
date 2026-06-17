"""
Módulo de gestión de sesión para la aplicación PAL
"""
import sys as _sys
import tkinter as tk
import time
from tkinter import messagebox

# --- Compatibilidad con ejecutables compilados (Nuitka / PyInstaller) ---
# Cuando la app corre como binario compilado, el mecanismo de auto-detección
# del backend de keyring falla. Se fuerza el backend de Windows explícitamente.
_is_compiled = getattr(_sys, 'frozen', False) or '__compiled__' in dir()
if _is_compiled:
    try:
        import keyring.backends.Windows
        import keyring
        keyring.set_keyring(keyring.backends.Windows.WinVaultKeyring())
    except Exception:
        import keyring  # Fallback: dejar que keyring intente auto-detectar
else:
    import keyring
from typing import Optional
from pal.core.log import get_logger

logger = get_logger("CORE")

class SessionManager:
    def __init__(self, root: tk.Tk)-> None:
        self.root: tk.Tk= root
        self.last_activity = time.time()
        self.timeout = 18000 # 5 horas (18000 segundos)
        self.session_active: bool = False
        self.enviando = False
        self.progress = None
        self.lbl_progreso = None
        self.after_id: Optional[str] = None

        #Monitorear actividad
        root.bind("<Key>", self.update_activity)
        root.bind("<Button>", self.update_activity)
        root.bind("<Motion>", self.update_activity)

    def update_activity(self, event=None):
        try:
            self.last_activity = time.time()
            if not self.session_active:
                self.start_session()
        except Exception:
            pass
        # Siempre retornar None para que Tkinter propague el evento correctamente
        # No retornar enteros explícitamente ya que puede causar problemas en Windows

    def start_session(self):
        self.session_active = True   
        self.check_activity()        

    def check_activity(self):
            if self.session_active and (time.time() - self.last_activity) > self.timeout:
                self.expire_session()
            elif self.session_active:
                self.after_id = self.root.after(1000, self.check_activity) 
                    
    def expire_session(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        try:
            if keyring.get_password("DBClientApp", "temp_pass"):
                keyring.delete_password("DBClientApp", "temp_pass")
        except Exception as e:
            logger.error(f"Error eliminando contraseña temporal: {str(e)}")
        
        messagebox.showinfo("Sesión Expirada", "La sesión ha expirado por inactividad")
        self.root.destroy()
