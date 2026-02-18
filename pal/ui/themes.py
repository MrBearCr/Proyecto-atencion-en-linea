import tkinter as tk
from tkinter import ttk
import json
import os

THEMES = {
    "retro": {
        "name": "Retro",
        "description": "Estilo clásico de Windows",
        "colors": {
            "bg_main": "#F5F6F8",
            "bg_card": "#FFFFFF",
            "accent": "#004C97",
            "text": "#000000",
            "text_secondary": "#666666",
        }
    },
    "moderno": {
        "name": "Moderno",
        "description": "Interfaz moderna con colores vibrantes",
        "colors": {
            "bg_main": "#1E1E2E",
            "bg_card": "#2D2D3F",
            "accent": "#7C3AED",
            "text": "#FFFFFF",
            "text_secondary": "#A0A0B0",
        }
    },
    "oscuro": {
        "name": "Oscuro",
        "description": "Modo oscuro elegante",
        "colors": {
            "bg_main": "#121212",
            "bg_card": "#1E1E1E",
            "accent": "#BB86FC",
            "text": "#E0E0E0",
            "text_secondary": "#9E9E9E",
        }
    },
    "azul": {
        "name": "Azul",
        "description": "Tema azul profesional",
        "colors": {
            "bg_main": "#E3F2FD",
            "bg_card": "#FFFFFF",
            "accent": "#1976D2",
            "text": "#0D47A1",
            "text_secondary": "#546E7A",
        }
    },
    "verde": {
        "name": "Verde",
        "description": "Tema verde inspirador",
        "colors": {
            "bg_main": "#E8F5E9",
            "bg_card": "#FFFFFF",
            "accent": "#2E7D32",
            "text": "#1B5E20",
            "text_secondary": "#558B2F",
        }
    },
}

THEME_CONFIG_FILE = "theme_config.json"

def _get_theme_config_path():
    """Obtiene la ruta del archivo de configuración de temas."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), THEME_CONFIG_FILE)

def save_theme_preference(theme_key):
    """Guarda la preferencia de tema en un archivo local."""
    try:
        config_path = _get_theme_config_path()
        with open(config_path, 'w') as f:
            json.dump({"theme": theme_key}, f)
    except Exception as e:
        print(f"Error guardando preferencia de tema: {e}")

def get_current_theme_key():
    """Obtiene el tema actual desde archivo local o BD."""
    try:
        config_path = _get_theme_config_path()
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                return data.get("theme", "retro")
    except Exception as e:
        print(f"Error leyendo preferencia de tema: {e}")
    
    # Intentar desde config_manager si está disponible
    return "retro"

def apply_theme(app, theme_key):
    """
    Aplica un tema a la aplicación.
    """
    if theme_key not in THEMES:
        return
    
    theme = THEMES[theme_key]
    colors = theme["colors"]
    
    app.current_theme = theme_key
    
    # Guardar preferencia
    save_theme_preference(theme_key)
    
    # Guardar en BD si hay config_manager
    try:
        if hasattr(app, 'config_manager') and app.config_manager:
            app.config_manager.set_setting("ui_theme", theme_key, description="Tema de UI")
    except Exception as e:
        print(f"Nota: No se pudo guardar tema en BD: {e}")
    
    try:
        app.style.theme_use("alt")
    except:
        pass
    
    try:
        app.style.configure("TFrame", background=colors["bg_main"])
        app.style.configure("TLabel", background=colors["bg_main"], foreground=colors["text"])
        app.style.configure("TButton", background=colors["accent"])
        app.style.configure("TNotebook", background=colors["bg_card"])
        app.style.configure("TNotebook.Tab", background=colors["bg_card"], foreground=colors["text"])
    except Exception as e:
        print(f"Error aplicando estilos: {e}")
    
    try:
        for widget in app.root.winfo_children():
            _apply_theme_to_widget(widget, colors)
    except Exception as e:
        print(f"Error en widget tree: {e}")

def _apply_theme_to_widget(widget, colors):
    """Aplica recursivamente los colores a un widget y sus hijos."""
    try:
        widget_class = widget.winfo_class()
        
        if widget_class in ['TFrame', 'Frame']:
            try:
                widget.configure(background=colors["bg_main"])
            except:
                pass
        elif widget_class in ['TLabel', 'Label']:
            try:
                widget.configure(background=colors["bg_main"], foreground=colors["text"])
            except:
                pass
        elif widget_class in ['TButton', 'Button']:
            try:
                widget.configure(background=colors["accent"])
            except:
                pass
        elif widget_class in ['TEntry', 'Entry']:
            try:
                widget.configure(background=colors["bg_card"], foreground=colors["text"])
            except:
                pass
        elif widget_class in ['TCombobox', 'Combobox']:
            try:
                widget.configure(background=colors["bg_card"], foreground=colors["text"])
            except:
                pass
    except:
        pass
    
    try:
        for child in widget.winfo_children():
            _apply_theme_to_widget(child, colors)
    except:
        pass

def get_current_theme(app):
    """Obtiene el tema actual configurado."""
    theme = get_current_theme_key()
    
    # Intentar sobrescribir desde config_manager si está disponible
    try:
        if hasattr(app, 'config_manager') and app.config_manager:
            db_theme = app.config_manager.get_setting("ui_theme")
            if db_theme and db_theme in THEMES:
                theme = db_theme
    except:
        pass
    
    return theme

def load_saved_theme(app):
    """Carga y aplica el tema guardado en la configuración."""
    theme_key = get_current_theme(app)
    if theme_key != "retro":
        apply_theme(app, theme_key)
