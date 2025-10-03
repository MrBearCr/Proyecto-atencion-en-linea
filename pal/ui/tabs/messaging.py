"""
Módulo de configuración de pestaña de Mensajería
"""
import tkinter as tk
from tkinter import ttk

def setup_messaging_tab(app):
    """Configura la pestaña de Mensajería en la aplicación"""
    frame = ttk.Frame(app.messaging_tab)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Botones superiores
    top_frame = ttk.Frame(frame)
    top_frame.pack(fill=tk.X)
    
    btn_masivo = ttk.Button(top_frame, 
                    text="▶ Iniciar envío masivo", 
                    command=lambda: getattr(app, 'enviar_a_todos', lambda: None)())
    btn_masivo.pack(side=tk.LEFT)
    if hasattr(app, 'buttons'):
        app.buttons['btn_envio_masivo'] = btn_masivo
    
    ttk.Button(top_frame,
            text="🔄 Limpiar Logs",
            command=lambda: getattr(app, 'limpiar_logs', lambda: None)()).pack(side=tk.RIGHT)
    
    # Panel de logs con scroll
    log_frame = ttk.Frame(frame)
    log_frame.pack(fill=tk.BOTH, expand=True)
    
    app.logs_text = tk.Text(log_frame, wrap=tk.WORD, state='normal')
    vsb = ttk.Scrollbar(log_frame, command=app.logs_text.yview)
    app.logs_text.configure(yscrollcommand=vsb.set)
    
    # Configurar tags para colores
    app.logs_text.tag_config('DEBUG', foreground='gray')
    app.logs_text.tag_config('INFO', foreground='black')
    app.logs_text.tag_config('WARNING', foreground='orange')
    app.logs_text.tag_config('ERROR', foreground='red')
    app.logs_text.tag_config('SUCCESS', foreground='green')
    
    # Layout
    app.logs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Contador de mensajes
    app.log_counter = 0
    app.max_logs = 200  # Máximo de líneas antes de limpiar

    programar_frame = ttk.Frame(frame)
    programar_frame.pack(fill=tk.X, pady=10)

    ttk.Button(programar_frame, 
                text="⏰ Programar Envío", 
                command=lambda: getattr(app, 'mostrar_ventana_programacion', lambda: None)()).pack(side=tk.LEFT)
