"""
Módulo de barra lateral de navegación para la aplicación PAL
"""
import tkinter as tk
from tkinter import ttk

def create_sidebar(app):
    """Crear la barra lateral de navegación"""
    sidebar = ttk.Frame(app.root, width=250, style="Sidebar.TFrame")
    sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
    
    nav_items = [
        ('📋 Registros', app.show_records_view),
        ('📨 Mensajería', app.show_messaging_view),
        ('⚙ Configuración', app.show_settings)
    ]
    
    for text, cmd in nav_items:
        btn = ttk.Button(sidebar, text=text, style="Nav.TButton", command=cmd)
        btn.pack(fill=tk.X, pady=2)