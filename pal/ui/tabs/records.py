"""
Módulo de configuración de pestaña de Registros
"""
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

def setup_records_tab(app):
    """Configura la pestaña de Registros en la aplicación"""
    # Panel principal
    main_frame = ttk.Frame(app.records_tab)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Panel izquierdo (Formulario)
    form_frame = ttk.Frame(main_frame, width=300)
    form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
    
    # Campo Número Cliente
    input_frame = ttk.Frame(form_frame)
    input_frame.pack(fill=tk.X, pady=5)
    ttk.Label(input_frame, text="Número Cliente:").pack(side=tk.LEFT)
    app.num_cliente = ttk.Entry(input_frame)
    app.num_cliente.pack(side=tk.RIGHT, expand=True, fill=tk.X)
    
    # Campo Código Producto
    input_frame = ttk.Frame(form_frame)
    input_frame.pack(fill=tk.X, pady=5)
    ttk.Label(input_frame, text="Código Producto:").pack(side=tk.LEFT)
    app.cod_producto = ttk.Entry(input_frame)
    app.cod_producto.pack(side=tk.RIGHT, expand=True, fill=tk.X)
    
    # Descripción
    app.descripcion = ttk.Entry(form_frame, state="readonly")
    app.descripcion.pack(fill=tk.X, pady=5)
    
    # Botones de acción
    btn_frame = ttk.Frame(form_frame)
    btn_frame.pack(fill=tk.X, pady=10)
    
    actions = [
        # (Texto, Comando, Clave)
        ('🔍 Buscar', lambda: getattr(app, 'search_records', lambda: None)(), 'btn_buscar'),
        ('💾 Guardar', lambda: getattr(app, 'save_record', lambda: None)(), 'btn_guardar'),
        ('🔄 Actualizar', lambda: getattr(app, 'update_record', lambda: None)(), 'btn_actualizar'),
        ('🗑 Eliminar', lambda: getattr(app, 'delete_record', lambda: None)(), 'btn_eliminar')
    ]
    
    for text, cmd, key in actions:
        btn = ttk.Button(btn_frame, text=text, command=cmd)
        btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        if hasattr(app, 'buttons'):
            app.buttons[key] = btn

    # Filtro por fecha
    fecha_frame = ttk.Frame(form_frame)
    fecha_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(fecha_frame, text="Desde:").pack(side=tk.LEFT)
    app.fecha_inicio = DateEntry(fecha_frame)
    app.fecha_inicio.pack(side=tk.LEFT, padx=5)
    
    ttk.Label(fecha_frame, text="Hasta:").pack(side=tk.LEFT)
    app.fecha_fin = DateEntry(fecha_frame)
    app.fecha_fin.pack(side=tk.LEFT, padx=5)
    
    ttk.Button(fecha_frame, text="Filtrar por Fecha", 
               command=lambda: getattr(app, 'buscar_por_fecha', lambda: None)()).pack(side=tk.RIGHT)

    # Panel derecho (Lista)
    list_frame = ttk.Frame(main_frame)
    list_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
    
    # Treeview
    tree_frame = ttk.Frame(list_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)
    
    app.tree = ttk.Treeview(tree_frame, columns=("ID", "Número", "Código"), show="headings")
    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=app.tree.yview)
    app.tree.configure(yscrollcommand=vsb.set)
    
    # Configurar columnas
    app.tree.heading("ID", text="ID")
    app.tree.heading("Número", text="Número Cliente")
    app.tree.heading("Código", text="Código Producto")
    
    app.tree.column("ID", width=80, anchor=tk.CENTER)
    app.tree.column("Número", width=150)
    app.tree.column("Código", width=200)
    
    # Layout
    app.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
