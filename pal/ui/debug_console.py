"""
Consola de debug flotante para desarrolladores.
Se activa/desactiva con Ctrl+Shift+D
"""
import tkinter as tk
from tkinter import ttk
import threading
import time

class DebugConsole:
    def __init__(self, parent_app):
        self.app = parent_app
        self.window = None
        self.text_widget = None
        self.visible = False
        self.log_buffer = []
        self.max_buffer = 500
        self.log_counter = 0
        
    def toggle(self):
        """Mostrar/ocultar la consola de debug"""
        if self.visible:
            self.hide()
        else:
            self.show()
    
    def show(self):
        """Mostrar consola de debug"""
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.lift()
            self.visible = True
            return
        
        # Crear ventana flotante
        self.window = tk.Toplevel(self.app.root)
        self.window.title("🐛 Consola de Debug - Modo Desarrollador")
        self.window.geometry("900x400")
        
        # Hacer que siempre esté al frente
        self.window.attributes('-topmost', True)
        
        # Frame principal
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Header con botones
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(
            header_frame, 
            text="🐛 Consola de Debug", 
            font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            header_frame, 
            text="🗑️ Limpiar", 
            command=self.clear,
            width=10
        ).pack(side=tk.RIGHT, padx=2)
        
        ttk.Button(
            header_frame, 
            text="📋 Copiar Todo", 
            command=self.copy_all,
            width=12
        ).pack(side=tk.RIGHT, padx=2)
        
        # Área de texto con scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#ffffff"
        )
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_widget.yview)
        
        # Configurar colores para diferentes niveles
        self.text_widget.tag_config("DEBUG", foreground="#569cd6")
        self.text_widget.tag_config("INFO", foreground="#d4d4d4")
        self.text_widget.tag_config("WARNING", foreground="#dcdcaa")
        self.text_widget.tag_config("ERROR", foreground="#f48771")
        self.text_widget.tag_config("SUCCESS", foreground="#4ec9b0")
        
        # Footer con info
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.status_label = ttk.Label(
            footer_frame,
            text="Presiona Ctrl+Shift+D para ocultar",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Evento de cierre
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Escribir logs guardados en buffer
        self._flush_buffer()
        
        self.visible = True
    
    def hide(self):
        """Ocultar consola de debug"""
        if self.window and self.window.winfo_exists():
            self.window.withdraw()
        self.visible = False
    
    def write(self, message: str, level: str = "INFO"):
        """Escribir mensaje en la consola de debug"""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        
        # Guardar en buffer
        self.log_buffer.append((entry, level))
        if len(self.log_buffer) > self.max_buffer:
            self.log_buffer.pop(0)
        
        # Si la ventana está visible, escribir directamente
        if self.visible and self.text_widget:
            try:
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, entry, level)
                self.text_widget.see(tk.END)
                self.text_widget.configure(state='disabled')
                self.log_counter += 1
                
                # Actualizar contador en footer
                if hasattr(self, 'status_label'):
                    self.status_label.config(
                        text=f"Logs: {self.log_counter} | Presiona Ctrl+Shift+D para ocultar"
                    )
            except Exception:
                pass
    
    def _flush_buffer(self):
        """Escribir todos los logs guardados en buffer"""
        if not self.text_widget:
            return
        
        try:
            self.text_widget.configure(state='normal')
            for entry, level in self.log_buffer:
                self.text_widget.insert(tk.END, entry, level)
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
            self.log_counter = len(self.log_buffer)
        except Exception:
            pass
    
    def clear(self):
        """Limpiar consola"""
        if self.text_widget:
            try:
                self.text_widget.configure(state='normal')
                self.text_widget.delete('1.0', tk.END)
                self.text_widget.configure(state='disabled')
                self.log_counter = 0
                self.log_buffer.clear()
                if hasattr(self, 'status_label'):
                    self.status_label.config(text="Consola limpiada | Ctrl+Shift+D para ocultar")
            except Exception:
                pass
    
    def copy_all(self):
        """Copiar todo el contenido al portapapeles"""
        if self.text_widget:
            try:
                content = self.text_widget.get('1.0', tk.END)
                self.window.clipboard_clear()
                self.window.clipboard_append(content)
                if hasattr(self, 'status_label'):
                    self.status_label.config(text="✅ Copiado al portapapeles | Ctrl+Shift+D para ocultar")
                    # Restaurar mensaje después de 2 segundos
                    self.window.after(2000, lambda: self.status_label.config(
                        text=f"Logs: {self.log_counter} | Presiona Ctrl+Shift+D para ocultar"
                    ))
            except Exception:
                pass
