"""
Módulo de configuración de pestaña de Estadísticas
"""
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def setup_stats_tab(app):
    """Configura la pestaña de Estadísticas en la aplicación"""
    app.stats_frame = ttk.Frame(app.stats_tab)
    app.stats_frame.pack(fill=tk.BOTH, expand=True)
    
    # Botón para actualizar gráficos
    ttk.Button(
        app.stats_frame, 
        text="Actualizar Gráficos", 
        command=lambda: getattr(app, 'mostrar_estadisticas', lambda: None)()
    ).pack(pady=10)
    
    # Contenedor para gráficos
    app.graph_container = ttk.Frame(app.stats_frame)
    app.graph_container.pack(fill=tk.BOTH, expand=True)
