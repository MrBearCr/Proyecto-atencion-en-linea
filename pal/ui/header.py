"""
Módulo de header y configuración de estilos para la aplicación PAL
"""
import tkinter as tk
from tkinter import ttk

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
                    padding=(20, 10),      #e9ecef
                    background="#e9ecef")    #004C97
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
        background=[("active", "#0066CC")],  # Color al hacer hover
        foreground=[("active", "white")]
    )

def create_header(app):
    """Crear el header de la aplicación"""
    # Crear canvas para efectos avanzados
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
