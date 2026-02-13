"""
Módulo de barra lateral de navegación para la aplicación PAL
"""
import tkinter as tk
from tkinter import ttk

def create_sidebar(app):
    """Crear la barra lateral de navegación"""
    sidebar = ttk.Frame(app.root, width=250, style="Sidebar.TFrame")
    sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
    
    # Construcción dinámica según módulos habilitados
    nav_items = [
        ('📊 Quiebre de Stock', app.show_stock_tab),
        ('📋 Registros', app.show_records_view),
    ]
    
    # Solo agregar Mensajería si el módulo está habilitado
    if app.modules_enabled.get('envio_mensajes', False):
        nav_items.append(('📨 Mensajería', app.show_messaging_view))
    
    # Configuración siempre visible
    nav_items.append(('⚙ Configuración', app.show_settings))
    
    
    # Administración (solo si es admin o tiene permiso)
    # Se valida contra módulo 'admin' que se habilita en app.py si el usuario es admin
    if app.modules_enabled.get('admin', False):
         nav_items.append(('🔓 Administración', app.show_admin_view))

    for text, cmd in nav_items:
        btn = ttk.Button(sidebar, text=text, style="Nav.TButton", command=cmd)
        btn.pack(fill=tk.X, pady=2)
