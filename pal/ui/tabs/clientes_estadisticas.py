"""
Módulo de Estadísticas de Clientes
Muestra gráficos de compras en el tiempo para uno o más clientes
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from collections import defaultdict

class ClientesEstadisticasTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.vad20_conn = None
        self.create_widgets()
    
    def create_widgets(self):
        # Frame principal con padding
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = ttk.Label(
            main_frame,
            text="📊 Estadísticas de Compras por Cliente",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Frame de controles
        controls_frame = ttk.LabelFrame(main_frame, text="Parámetros de Búsqueda", padding=15)
        controls_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Sede
        sede_frame = ttk.Frame(controls_frame)
        sede_frame.pack(fill=tk.X, pady=5)
        ttk.Label(sede_frame, text="Sede:", width=15).pack(side=tk.LEFT)
        self.sede_combo = ttk.Combobox(sede_frame, state='readonly', width=30)
        self.sede_combo.pack(side=tk.LEFT, padx=5)
        self.cargar_sedes()
        
        # IDs de clientes
        ids_frame = ttk.Frame(controls_frame)
        ids_frame.pack(fill=tk.X, pady=5)
        ttk.Label(ids_frame, text="ID(s) Cliente:", width=15).pack(side=tk.LEFT)
        self.ids_entry = ttk.Entry(ids_frame, width=50)
        self.ids_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(ids_frame, text="(separar con comas)", foreground="gray").pack(side=tk.LEFT)
        
        # Fechas
        dates_frame = ttk.Frame(controls_frame)
        dates_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dates_frame, text="Desde:", width=15).pack(side=tk.LEFT)
        # Por defecto: hace 1 año
        default_start = datetime.now() - timedelta(days=365)
        self.fecha_inicio_entry = DateEntry(
            dates_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yyyy',
            year=default_start.year,
            month=default_start.month,
            day=default_start.day
        )
        self.fecha_inicio_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(dates_frame, text="Hasta:", width=10).pack(side=tk.LEFT, padx=(20, 0))
        self.fecha_fin_entry = DateEntry(
            dates_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yyyy'
        )
        self.fecha_fin_entry.pack(side=tk.LEFT, padx=5)
        
        # Botón generar
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        self.btn_generar = ttk.Button(
            btn_frame,
            text="📈 Generar Gráfico",
            command=self.generar_grafico
        )
        self.btn_generar.pack(side=tk.RIGHT)
        
        # Frame para el gráfico
        self.chart_frame = ttk.Frame(main_frame)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # Mensaje inicial
        self.initial_label = ttk.Label(
            self.chart_frame,
            text="Ingrese los parámetros y presione 'Generar Gráfico'",
            font=("Segoe UI", 12),
            foreground="gray"
        )
        self.initial_label.pack(expand=True)
    
    def cargar_sedes(self):
        """Carga las sedes disponibles en el combobox"""
        try:
            sedes_data = self.controller.db_manager.get_sedes_config()
            if sedes_data:
                self.sedes_dict = {s['nombre_sede']: s for s in sedes_data}
                self.sede_combo['values'] = list(self.sedes_dict.keys())
                if self.sedes_dict:
                    self.sede_combo.current(0)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las sedes: {e}")
    
    def generar_grafico(self):
        """Genera el gráfico de compras en el tiempo"""
        try:
            # Validar sede
            sede_nombre = self.sede_combo.get()
            if not sede_nombre or sede_nombre not in self.sedes_dict:
                messagebox.showwarning("Advertencia", "Seleccione una sede válida")
                return
            
            # Validar IDs
            ids_text = self.ids_entry.get().strip()
            if not ids_text:
                messagebox.showwarning("Advertencia", "Ingrese al menos un ID de cliente")
                return
            
            # Parsear IDs (separados por comas)
            client_ids = [id.strip() for id in ids_text.split(',') if id.strip()]
            if not client_ids:
                messagebox.showwarning("Advertencia", "No se encontraron IDs válidos")
                return
            
            # Validar fechas
            fecha_inicio = self.fecha_inicio_entry.get_date()
            fecha_fin = self.fecha_fin_entry.get_date()
            
            # Validar rango mínimo de 1 año
            if (fecha_fin - fecha_inicio).days < 365:
                messagebox.showwarning(
                    "Advertencia",
                    "El rango de fechas debe ser de al menos 1 año"
                )
                return
            
            # Conectar a la sede
            selected_sede = self.sedes_dict[sede_nombre]
            self.vad20_conn = self.controller.db_manager.connect_to_vad20_sede(selected_sede)
            
            # Obtener datos
            data = self.controller.db_manager.get_client_purchase_history(
                self.vad20_conn,
                client_ids,
                fecha_inicio,
                fecha_fin
            )
            
            if not data:
                messagebox.showinfo("Sin Datos", "No se encontraron compras para los clientes especificados")
                return
            
            # Organizar datos por cliente
            clients_data = defaultdict(lambda: {'name': '', 'months': [], 'totals': []})
            for row in data:
                client_id, client_name, year_month, total = row
                clients_data[client_id]['name'] = client_name
                clients_data[client_id]['months'].append(year_month)
                clients_data[client_id]['totals'].append(float(total) if total else 0.0)
            
            # Crear gráfico
            self.mostrar_grafico(clients_data, fecha_inicio, fecha_fin)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el gráfico: {e}")
        finally:
            if self.vad20_conn:
                try:
                    self.vad20_conn.close()
                except:
                    pass
    
    def mostrar_grafico(self, clients_data, fecha_inicio, fecha_fin):
        """Muestra el gráfico de líneas con los datos de compras"""
        # Limpiar frame
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Crear figura
        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Plotear cada cliente
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        for idx, (client_id, data) in enumerate(clients_data.items()):
            # Convertir year-month a fechas
            dates = [datetime.strptime(ym + '-01', '%Y-%m-%d') for ym in data['months']]
            totals = data['totals']
            
            color = colors[idx % len(colors)]
            label = f"{data['name']} ({client_id})"
            ax.plot(dates, totals, marker='o', linestyle='-', linewidth=2, 
                   markersize=6, label=label, color=color)
        
        # Configurar ejes
        ax.set_xlabel('Mes', fontsize=12)
        ax.set_ylabel('Total Compras (Bs)', fontsize=12)
        ax.set_title('Historial de Compras por Cliente', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # Formato de fechas en eje X
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        fig.autofmt_xdate()
        
        # Integrar en tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
