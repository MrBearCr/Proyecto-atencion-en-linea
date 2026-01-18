"""
Módulo de Dashboard Principal para la aplicación PAL
Pantalla de inicio con resumen de módulos y estadísticas generales
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime

def setup_dashboard_tab(app):
    """Configurar el tab de dashboard principal"""
    
    # Contenedor principal con canvas para scroll
    container = ttk.Frame(app.dashboard_tab, style="Dashboard.TFrame")
    container.pack(fill=tk.BOTH, expand=True)
    
    # Canvas y scrollbar
    canvas = tk.Canvas(container, bg="#F5F6F8", highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas, style="Dashboard.TFrame")
    
    # Configurar el canvas para que el frame interno se expanda
    canvas_frame_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    
    def _configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    def _configure_canvas_width(event):
        # Hacer que el frame interno ocupe todo el ancho del canvas
        canvas_width = event.width
        canvas.itemconfig(canvas_frame_id, width=canvas_width)
    
    scrollable_frame.bind("<Configure>", _configure_scroll_region)
    canvas.bind("<Configure>", _configure_canvas_width)
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Scroll con rueda del mouse
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _bind_mousewheel(event):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def _unbind_mousewheel(event):
        canvas.unbind_all("<MouseWheel>")
    
    canvas.bind("<Enter>", _bind_mousewheel)
    canvas.bind("<Leave>", _unbind_mousewheel)
    
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Frame principal con padding
    main_frame = ttk.Frame(scrollable_frame, style="Dashboard.TFrame")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
    
    # Header compacto y moderno
    header_frame = ttk.Frame(main_frame)
    header_frame.pack(fill=tk.X, pady=(0, 15))
    
    # Obtener nombre del usuario actual
    username = "Usuario"
    if app.current_user and app.current_user.get('username'):
        username = app.current_user.get('username')
    
    ttk.Label(
        header_frame, 
        text=f"👋 Bienvenido, {username}", 
        font=("Segoe UI", 20, "bold"),
        foreground="#004C97"
    ).pack(side=tk.LEFT)
    
    ttk.Label(
        header_frame,
        text=datetime.now().strftime("%d/%m/%Y  •  %H:%M"),
        font=("Segoe UI", 10),
        foreground="#6B7280"
    ).pack(side=tk.RIGHT, pady=5)
    
    # Se eliminaron las tarjetas de estado de conexión y tiempo de sesión para ahorrar espacio
    
    # Sección de módulos - más espacio y mejor diseño
    modules_header = ttk.Frame(main_frame)
    modules_header.pack(fill=tk.X, pady=(10, 15))
    
    ttk.Label(
        modules_header,
        text="Módulos Disponibles",
        font=("Segoe UI", 14, "bold"),
        foreground="#1F2937"
    ).pack(side=tk.LEFT)
    
    modules_frame = ttk.Frame(main_frame)
    modules_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
    
    # Grid de tarjetas de módulos (diseño intermedio)
    cards_container = ttk.Frame(modules_frame)
    cards_container.pack(fill=tk.X, pady=(0, 10), expand=False)
    
    # Definir módulos disponibles con íconos
    # Los tab_text deben coincidir exactamente con los textos en create_main_workspace
    modules_info = {
        'envio_mensajes': {
            'icon': '📨',
            'name': 'Mensajería',
            'tab_text': 'Mensajería',  # Tab exacto
            'tab_attr': 'messaging_tab',
        },
        'clientes': {
            'icon': '👥',
            'name': 'Clientes',
            'tab_text': '👥 Clientes',
            'tab_attr': 'clientes_tab',
        },
        'stock': {
            'icon': '📎',
            'name': 'Stock',
            'tab_text': '🚨 Alertas Stock',  # Tab exacto con emoji
            'tab_attr': 'stock_tab',
        },
'tra': {
            'icon': '📈',
            'name': 'RI',
            'tab_text': '📈 RI',  # Tab exacto con emoji
            'tab_attr': 'tra_tab',
        },
        'mbrp': {
            'icon': '📉',
            'name': 'MBRP',
            'tab_text': '📉 MBRP',  # Tab exacto con emoji
            'tab_attr': 'mbrp_tab',
        },
        'estadisticas': {
            'icon': '📊',
            'name': 'Estadísticas',
            'tab_text': '📊 Estadísticas',  # Tab exacto con emoji
            'tab_attr': 'stats_tab',
        },
        'calendario': {
            'icon': '📅',
            'name': 'Calendario',
            'tab_text': '📅 Calendario',  # Tab exacto con emoji
            'tab_attr': 'calendar_tab',
        },
        'admin': {
            'icon': '🔓',
            'name': 'Configuracion',
            'tab_text': '🔓 Administración',  # Tab exacto con emoji
            'tab_attr': 'admin_tab',
        }
    }
    
    # Crear tarjetas medianas para cada módulo habilitado (diseño grid)
    col = 0
    max_cols = 4  # 4 tarjetas por fila
    
    for module_key, module_data in modules_info.items():
        if app.modules_enabled.get(module_key, False):
            # Frame para cada tarjeta
            card_frame = tk.Frame(
                cards_container,
                bg="#FFFFFF",
                relief=tk.RAISED,
                bd=1,
                cursor="hand2"
            )
            card_frame.pack(side=tk.LEFT, padx=8, pady=8, fill=tk.BOTH, expand=True)
            
            # Contenedor interno
            inner = tk.Frame(card_frame, bg="#FFFFFF")
            inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
            
            # Ícono mediano
            tk.Label(
                inner,
                text=module_data['icon'],
                font=("Segoe UI", 24),
                bg="#FFFFFF"
            ).pack(pady=(5, 8))
            
            # Nombre del módulo
            tk.Label(
                inner,
                text=module_data['name'],
                font=("Segoe UI", 11, "bold"),
                foreground="#1F2937",
                bg="#FFFFFF"
            ).pack()
            
            # Efecto hover en toda la tarjeta
            def on_enter(e, cf=card_frame):
                cf.configure(relief=tk.SUNKEN, bd=2, bg="#F3F4F6")
            
            def on_leave(e, cf=card_frame):
                cf.configure(relief=tk.RAISED, bd=1, bg="#FFFFFF")
            
            def on_click(tab_attr=module_data.get('tab_attr'), tab_text=module_data['tab_text']):
                _select_tab_by_attr(app, tab_attr, fallback_text=tab_text)
            
            card_frame.bind("<Enter>", on_enter)
            card_frame.bind("<Leave>", on_leave)
            # Importante: fijar la referencia del handler por iteración (evitar que todas apunten al último)
            card_frame.bind("<Button-1>", lambda e, f=on_click: f())
            inner.bind("<Button-1>", lambda e, f=on_click: f())
            inner.bind("<Enter>", on_enter)
            inner.bind("<Leave>", on_leave)
            
            col += 1
    
    # Sección de acciones rápidas eliminada para ahorrar espacio
    
    # Botón flotante de configuración (FAB - Floating Action Button)
    # Solo visible para admin
    is_admin = app.current_user and app.current_user.get('username', '').lower() == 'admin'
    
    if is_admin:
        fab_button = tk.Button(
            app.dashboard_tab,
            text="⚙️",
            font=("Segoe UI", 24),
            bg="#004C97",
            fg="white",
            activebackground="#0066CC",
            activeforeground="white",
            relief=tk.RAISED,
            cursor="hand2",
            width=2,
            height=1,
            command=app.show_settings,
            borderwidth=2,
            bd=2
        )
        fab_button.place(relx=1.0, rely=1.0, x=-80, y=-80, anchor="se")
        
        # Tooltip para el FAB
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root-80}+{event.y_root-10}")
            label = tk.Label(
                tooltip,
                text="Configuración Avanzada",
                bg="#1F2937",
                fg="white",
                font=("Segoe UI", 9),
                padx=8,
                pady=4
            )
            label.pack()
            fab_button.tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(fab_button, 'tooltip'):
                fab_button.tooltip.destroy()
                delattr(fab_button, 'tooltip')
        
        fab_button.bind("<Enter>", show_tooltip)
        fab_button.bind("<Leave>", hide_tooltip)
    
    # Actualizar información periódicamente
    _update_dashboard_info(app)


def _select_tab_by_attr(app, tab_attr, fallback_text=None):
    """Selecciona el tab usando directamente el atributo (sin búsquedas).
    Si falla o no existe, usa fallback_text con búsqueda clásica.
    """
    try:
        tab = getattr(app, tab_attr, None)
        if tab:
            app.main_notebook.select(tab)
            return
    except Exception as e:
        print(f"Error seleccionando tab por atributo {tab_attr}: {e}")
    if fallback_text:
        _switch_to_tab(app, fallback_text)

def _switch_to_tab(app, tab_name):
    """Cambiar a un tab por coincidencia exacta primero; sin substring amplia para evitar falsos positivos."""
    try:
        # Intento 1: coincidencia exacta del texto mostrado
        for i in range(app.main_notebook.index('end')):
            if tab_name == app.main_notebook.tab(i, 'text'):
                app.main_notebook.select(i)
                return
        # Intento 2: coincidencia case-insensitive sin eliminar acentos
        tgt = (tab_name or '').strip().lower()
        for i in range(app.main_notebook.index('end')):
            cur = (app.main_notebook.tab(i, 'text') or '').strip().lower()
            if tgt == cur:
                app.main_notebook.select(i)
                return
    except Exception as e:
        print(f"Error cambiando a tab {tab_name}: {e}")

def _update_dashboard_info(app):
    """Actualizar información del dashboard periódicamente"""
    try:
        # Actualizar estado de conexión - sincronizado con el estado global
        # NO verificar directamente db_manager.conn para evitar inconsistencias
        # El estado se actualiza a través de update_status() que sincroniza ambos labels
        
        # Solo actualizar tiempo de sesión (el estado de conexión ya se maneja en update_status)
        if hasattr(app, 'session') and hasattr(app.session, 'start_time'):
            elapsed = datetime.now() - app.session.start_time
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            app.dashboard_session_time.config(
                text=f"{hours:02d}:{minutes:02d}",
                foreground="#004C97"
            )
    except Exception as e:
        print(f"Error actualizando dashboard: {e}")
    
    # Programar siguiente actualización (cada 30 segundos)
    if hasattr(app, 'root'):
        app.root.after(30000, lambda: _update_dashboard_info(app))
