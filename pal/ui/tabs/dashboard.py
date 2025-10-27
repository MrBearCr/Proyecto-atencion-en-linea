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
    
    ttk.Label(
        header_frame, 
        text="🏠 Centro de Control", 
        font=("Segoe UI", 20, "bold"),
        foreground="#004C97"
    ).pack(side=tk.LEFT)
    
    ttk.Label(
        header_frame,
        text=datetime.now().strftime("%d/%m/%Y  •  %H:%M"),
        font=("Segoe UI", 10),
        foreground="#6B7280"
    ).pack(side=tk.RIGHT, pady=5)
    
    # Cards de información del sistema - diseño moderno
    info_container = ttk.Frame(main_frame)
    info_container.pack(fill=tk.X, pady=(10, 20))
    
    # Card 1: Estado de conexión
    connection_card = tk.Frame(
        info_container, 
        bg="#FFFFFF", 
        relief=tk.FLAT, 
        borderwidth=1,
        highlightthickness=1,
        highlightbackground="#E5E7EB"
    )
    connection_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), ipadx=20, ipady=15)
    
    tk.Label(
        connection_card,
        text="🔌",
        font=("Segoe UI", 20),
        bg="#FFFFFF"
    ).pack(pady=(5, 5))
    
    tk.Label(
        connection_card, 
        text="Base de Datos", 
        font=("Segoe UI", 10),
        foreground="#6B7280",
        bg="#FFFFFF"
    ).pack()
    
    app.dashboard_connection_status = tk.Label(
        connection_card, 
        text="Desconectado",
        foreground="#EF4444",
        font=("Segoe UI", 11, "bold"),
        bg="#FFFFFF"
    )
    app.dashboard_connection_status.pack(pady=(5, 5))
    
    # Card 2: Tiempo de sesión
    session_card = tk.Frame(
        info_container, 
        bg="#FFFFFF", 
        relief=tk.FLAT, 
        borderwidth=1,
        highlightthickness=1,
        highlightbackground="#E5E7EB"
    )
    session_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), ipadx=20, ipady=15)
    
    tk.Label(
        session_card,
        text="⏱️",
        font=("Segoe UI", 20),
        bg="#FFFFFF"
    ).pack(pady=(5, 5))
    
    tk.Label(
        session_card, 
        text="Tiempo de Sesión", 
        font=("Segoe UI", 10),
        foreground="#6B7280",
        bg="#FFFFFF"
    ).pack()
    
    app.dashboard_session_time = tk.Label(
        session_card,
        text="00:00",
        foreground="#004C97",
        font=("Segoe UI", 11, "bold"),
        bg="#FFFFFF"
    )
    app.dashboard_session_time.pack(pady=(5, 5))
    
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
    
    # Grid de tarjetas de módulos
    cards_container = ttk.Frame(modules_frame)
    cards_container.pack(fill=tk.BOTH, expand=True)
    
    # Definir módulos disponibles con íconos y descripciones
    modules_info = {
        'envio_mensajes': {
            'icon': '📨',
            'name': 'Mensajería',
            'description': 'Envío de mensajes programados',
            'action': lambda: app.main_notebook.select(app.records_tab)
        },
        'stock': {
            'icon': '📦',
            'name': 'Stock',
            'description': 'Control de inventario y alertas',
            'action': lambda: _switch_to_tab(app, 'Stock')
        },
        'tra': {
            'icon': '📈',
            'name': 'T.R.A',
            'description': 'Tasa de Rotación de Artículos',
            'action': lambda: _switch_to_tab(app, 'T.R.A')
        },
        'mbrp': {
            'icon': '📉',
            'name': 'MBRP',
            'description': 'Movimiento de Baja Rotación',
            'action': lambda: _switch_to_tab(app, 'MBRP')
        },
        'estadisticas': {
            'icon': '📊',
            'name': 'Estadísticas',
            'description': 'Análisis y reportes',
            'action': lambda: _switch_to_tab(app, 'Estadísticas')
        },
        'calendario': {
            'icon': '📅',
            'name': 'Calendario',
            'description': 'Programación de eventos',
            'action': lambda: _switch_to_tab(app, 'Calendario')
        }
    }
    
    # Crear tarjetas para cada módulo habilitado
    row = 0
    col = 0
    max_cols = 3
    
    for module_key, module_data in modules_info.items():
        if app.modules_enabled.get(module_key, False):
            card = _create_module_card(
                cards_container,
                module_data['icon'],
                module_data['name'],
                module_data['description'],
                module_data['action']
            )
            card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    # Configurar grid para que las tarjetas se expandan
    for i in range(max_cols):
        cards_container.columnconfigure(i, weight=1)
    
    # Sección de acciones rápidas - diseño moderno
    actions_header = ttk.Frame(main_frame)
    actions_header.pack(fill=tk.X, pady=(10, 15))
    
    ttk.Label(
        actions_header,
        text="Acciones Rápidas",
        font=("Segoe UI", 14, "bold"),
        foreground="#1F2937"
    ).pack(side=tk.LEFT)
    
    actions_container = ttk.Frame(main_frame)
    actions_container.pack(fill=tk.X, pady=(0, 10))
    
    # Botón de Configuración
    config_btn = ttk.Button(
        actions_container,
        text="⚙️  Configuración del Sistema",
        command=app.show_settings,
        style="Accent.TButton",
        width=25
    )
    config_btn.pack(side=tk.LEFT, padx=(0, 15))
    
    # Botón de Reconectar
    reconnect_btn = ttk.Button(
        actions_container,
        text="🔄  Reconectar Base de Datos",
        command=app.connect_to_database,
        style="Accent.TButton",
        width=25
    )
    reconnect_btn.pack(side=tk.LEFT)
    
    # Botón flotante de configuración (FAB - Floating Action Button)
    # Siempre visible independiente del scroll
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
            text="Configuración",
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

def _create_module_card(parent, icon, name, description, action):
    """Crear una tarjeta visual moderna para un módulo"""
    # Card con sombra simulada y bordes redondeados
    card = tk.Frame(
        parent, 
        bg="#FFFFFF", 
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground="#E5E7EB",
        cursor="hand2"
    )
    
    # Frame interno con padding
    inner = tk.Frame(card, bg="#FFFFFF")
    inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Ícono grande
    tk.Label(
        inner,
        text=icon,
        font=("Segoe UI", 36),
        bg="#FFFFFF"
    ).pack(pady=(5, 15))
    
    # Nombre del módulo
    tk.Label(
        inner,
        text=name,
        font=("Segoe UI", 13, "bold"),
        foreground="#1F2937",
        bg="#FFFFFF"
    ).pack()
    
    # Descripción
    tk.Label(
        inner,
        text=description,
        font=("Segoe UI", 9),
        foreground="#6B7280",
        bg="#FFFFFF",
        wraplength=180
    ).pack(pady=(8, 15))
    
    # Botón de acceso moderno
    btn = ttk.Button(
        inner,
        text="Abrir →",
        command=action,
        style="ModuleCard.TButton",
        width=12
    )
    btn.pack()
    
    # Efecto hover en toda la card
    def on_enter(e):
        card.configure(highlightbackground="#004C97", highlightthickness=2)
    
    def on_leave(e):
        card.configure(highlightbackground="#E5E7EB", highlightthickness=1)
    
    card.bind("<Enter>", on_enter)
    card.bind("<Leave>", on_leave)
    inner.bind("<Button-1>", lambda e: action())
    
    return card

def _switch_to_tab(app, tab_name):
    """Cambiar a un tab específico del notebook"""
    try:
        # Buscar el tab por su texto
        for i in range(app.main_notebook.index('end')):
            tab_text = app.main_notebook.tab(i, 'text')
            if tab_name in tab_text:
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
