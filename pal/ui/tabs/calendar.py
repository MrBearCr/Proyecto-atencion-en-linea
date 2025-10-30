"""
Módulo de configuración de pestaña de Calendario
"""
import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar
from datetime import datetime, timedelta

def setup_calendar_tab(app):
    """Configura la pestaña de Calendario en la aplicación"""
    frame = ttk.Frame(app.calendar_tab)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Calendario
    app.cal = Calendar(
        frame,
        selectmode='day',
        year=datetime.now().year,
        month=datetime.now().month,
        day=datetime.now().day,
        date_pattern='y-mm-dd',
        showothermonthdays=False  # Evita clics en días fuera del mes actual (p. ej., 31 en noviembre)
    )
    app.cal.pack(fill=tk.BOTH, expand=True, pady=10)

    # Botón para actualizar eventos
    ttk.Button(frame, text="Actualizar Eventos", 
               command=lambda: getattr(app, 'cargar_eventos_calendario', lambda: None)()).pack(pady=5)

    # Área de detalles
    app.eventos_text = tk.Text(frame, height=10, wrap=tk.WORD)
    app.eventos_text.pack(fill=tk.BOTH, expand=True)

    # Cargar eventos iniciales si la función existe
    if hasattr(app, 'cargar_eventos_calendario'):
        app.cargar_eventos_calendario()
    app.cal.bind("<<CalendarSelected>>", 
                 lambda e: getattr(app, 'mostrar_eventos_fecha', lambda x: 0)(e))
