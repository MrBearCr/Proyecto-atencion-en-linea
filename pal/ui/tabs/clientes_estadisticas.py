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
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        # Header con Título y botón Volver
        header_content = ttk.Frame(main_frame)
        header_content.pack(fill=tk.X, pady=(0, 20))
        
        back_btn = tk.Button(
            header_content,
            text="↩ VOLVER",
            command=lambda: self.controller.show_clientes_sub_view('menu'),
            bg="#F3F4F6",
            fg="#4B5563",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2"
        )
        back_btn.pack(side=tk.LEFT)
        back_btn.bind("<Enter>", lambda e: back_btn.config(bg="#E5E7EB"))
        back_btn.bind("<Leave>", lambda e: back_btn.config(bg="#F3F4F6"))

        title_label = ttk.Label(
            header_content,
            text="📊 Estadísticas de Compras (USD)",
            font=("Segoe UI", 18, "bold"),
            foreground="#004C97"
        )
        title_label.pack(side=tk.LEFT, padx=20)
        
        # Frame de controles
        controls_frame = tk.Frame(main_frame, bg="#FFFFFF", highlightthickness=1, highlightbackground="#E5E7EB", pady=20, padx=20)
        controls_frame.pack(fill=tk.X, pady=(0, 25))
        
        # Sede y Período
        row1 = ttk.Frame(controls_frame, style="TFrame")
        row1.pack(fill=tk.X, pady=5)
        
        ttk.Label(row1, text="Sede:", width=10, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.sede_combo = ttk.Combobox(row1, state='readonly', width=25, font=("Segoe UI", 10))
        self.sede_combo.pack(side=tk.LEFT, padx=(5, 20))
        self.cargar_sedes()
        
        ttk.Label(row1, text="Período:", width=10, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.periodo_combo = ttk.Combobox(row1, state='readonly', width=18, font=("Segoe UI", 10))
        self.periodo_combo['values'] = ("7 días", "15 días", "30 días", "60 días", "90 días", "180 días", "365 días", "Personalizado")
        self.periodo_combo.current(2) # 30 días por defecto
        self.periodo_combo.pack(side=tk.LEFT, padx=5)
        self.periodo_combo.bind("<<ComboboxSelected>>", self._on_period_change)
        
        # IDs de clientes
        ids_frame = ttk.Frame(controls_frame)
        ids_frame.pack(fill=tk.X, pady=10)
        ttk.Label(ids_frame, text="IDs Clientes:", width=10, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.ids_entry = tk.Entry(ids_frame, width=50, font=("Segoe UI", 10), bg="#F9FAFB", relief="flat", highlightthickness=1, highlightbackground="#D1D5DB")
        self.ids_entry.pack(side=tk.LEFT, padx=5, ipady=4)
        ttk.Label(ids_frame, text="(RIFs separados por comas)", foreground="#6B7280", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=10)
        
        # Fechas
        dates_frame = ttk.Frame(controls_frame)
        dates_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dates_frame, text="Desde:", width=10, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        
        default_start = datetime.now() - timedelta(days=365)
        self.fecha_inicio_entry = DateEntry(
            dates_frame, width=12, background='#004C97', foreground='white', borderwidth=0, 
            date_pattern='dd/mm/yyyy', year=default_start.year, month=default_start.month, day=default_start.day,
            font=("Segoe UI", 10)
        )
        self.fecha_inicio_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(dates_frame, text="Hasta:", width=8, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(20, 0))
        self.fecha_fin_entry = DateEntry(
            dates_frame, width=12, background='#004C97', foreground='white', borderwidth=0, 
            date_pattern='dd/mm/yyyy', font=("Segoe UI", 10)
        )
        self.fecha_fin_entry.pack(side=tk.LEFT, padx=5)
        
        # Barra de progreso y estado
        self.progress_frame = tk.Frame(controls_frame, bg="#FFFFFF")
        self.progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 20))
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, mode='determinate', length=200)
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(self.progress_frame, text="", font=("Segoe UI", 9), fg="#6B7280", bg="#FFFFFF")
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Botón generar moderno
        self.btn_generar = tk.Button(
            controls_frame, text="📈 GENERAR GRÁFICO EN USD", command=self.generar_grafico,
            bg="#004C97", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=25, pady=8, cursor="hand2"
        )
        self.btn_generar.pack(side=tk.RIGHT, pady=(10, 0))
        self.btn_generar.bind("<Enter>", lambda e: self.btn_generar.config(bg="#003d7a"))
        self.btn_generar.bind("<Leave>", lambda e: self.btn_generar.config(bg="#004C97"))
        
        # Frame para el gráfico
        self.chart_frame = tk.Frame(main_frame, bg="#FFFFFF", highlightthickness=1, highlightbackground="#E5E7EB")
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # Mensaje inicial
        self.initial_label = ttk.Label(
            self.chart_frame, text="Configure los filtros y presione 'Generar Gráfico'",
            font=("Segoe UI", 11), foreground="#9CA3AF", background="#FFFFFF"
        )
        self.initial_label.pack(expand=True)

    def _on_period_change(self, event=None):
        """Actualiza los DateEntry según el período seleccionado"""
        rango = self.periodo_combo.get()
        hoy = datetime.now()
        
        if rango == "Personalizado":
            return
            
        # Extraer número de días
        try:
            dias = int(rango.split()[0])
            inicio = hoy - timedelta(days=dias-1)
            self.fecha_inicio_entry.set_date(inicio)
            self.fecha_fin_entry.set_date(hoy)
        except Exception:
            pass

    def generar_grafico(self):
        """Inicia el proceso de generación del gráfico en segundo plano"""
        ids_raw = self.ids_entry.get().strip()
        if not ids_raw:
            messagebox.showwarning("Faltan Datos", "Debe ingresar al menos un RIF de cliente.")
            return

        client_ids = [rif.strip() for rif in ids_raw.split(',') if rif.strip()]
        fecha_inicio = self.fecha_inicio_entry.get_date()
        fecha_fin = self.fecha_fin_entry.get_date()
        
        # Deshabilitar interfaz
        self.btn_generar.config(state=tk.DISABLED)
        self.status_label.config(text="Consultando base de datos...", fg="#004C97")
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start()
        
        # Ejecutar en hilo
        import threading
        thread = threading.Thread(
            target=self._background_generar_grafico,
            args=(client_ids, fecha_inicio, fecha_fin),
            daemon=True
        )
        thread.start()

    def _background_generar_grafico(self, client_ids, fecha_inicio, fecha_fin):
        """Procesamiento en segundo plano"""
        try:
            # Seleccionar sede y obtener conexión
            selected_sede = self.sede_combo.get()
            sede_info = next((s for s in self.sedes_config if s['nombre_sede'] == selected_sede), None)
            
            if not sede_info:
                raise Exception("Sede no encontrada")

            conn_sede = self.controller.db_manager.connect_to_vad20_sede(sede_info)
            if not conn_sede:
                raise Exception("No se pudo conectar a la base de datos de la sede")

            # Callback para actualizar barra de progreso
            def update_progress(current, total):
                if total > 0:
                    percent = (current / total) * 100
                    self.after(0, lambda: self.progress_bar.config(value=percent))
                    self.after(0, lambda: self.status_label.config(text=f"Procesando: {int(percent)}%"))

            # Obtener datos
            data = self.controller.db_manager.get_client_purchase_history(
                conn_sede, client_ids, fecha_inicio, fecha_fin, progress_callback=update_progress
            )
            conn_sede.close()
            
            # Actualizar UI con el resultado
            self.after(0, lambda: self._on_data_loaded(data))
            
        except Exception as e:
            self.after(0, lambda: self._on_load_error(str(e)))

    def _on_data_loaded(self, rows):
        """Maneja la carga exitosa de datos"""
        self.btn_generar.config(state=tk.NORMAL)
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=100)
        self.status_label.config(text="✓ Completado", fg="#10B981")
        
        if not rows:
            messagebox.showinfo("Sin Datos", "No se encontraron compras en el período seleccionado.")
            return
            
        self._mostrar_grafico(rows)

    def _on_load_error(self, message):
        """Maneja errores durante la carga"""
        self.btn_generar.config(state=tk.NORMAL)
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=0)
        self.status_label.config(text="⚠ Error", fg="#EF4444")
        messagebox.showerror("Error", f"Fallo al cargar estadísticas: {message}")

    def _mostrar_grafico(self, rows):
        """Muestra el gráfico de líneas con los datos de compras"""
        # Limpiar frame anterior
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Organizar datos por cliente
        clients_data = defaultdict(lambda: {'name': '', 'months': [], 'totals': [], 'invoices': []})
        for row in rows:
            # row: (client_id, client_name, year_month, total_usd, invoices_summary)
            client_id, client_name, year_month, total_usd, invoices_summary = row
            clients_data[client_id]['name'] = client_name
            clients_data[client_id]['months'].append(year_month)
            clients_data[client_id]['totals'].append(float(total_usd) if total_usd else 0.0)
            clients_data[client_id]['invoices'].append(invoices_summary)

        # Crear figura
        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Plotear cada cliente
        colors = ['#004C97', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']
        lines = []
        for idx, (client_id, data) in enumerate(clients_data.items()):
            # Convertir year-month a fechas
            dates = []
            for ym in data['months']:
                try:
                    dates.append(datetime.strptime(ym + '-01', '%Y-%m-%d'))
                except:
                    continue
            
            totals = data['totals']
            if not dates: continue
            
            color = colors[idx % len(colors)]
            label = f"{data['name']} ({client_id})"
            line, = ax.plot(dates, totals, marker='o', linestyle='-', linewidth=2.5, 
                   markersize=8, label=label, color=color, picker=True, pickradius=5)
            lines.append((line, data))
        
        # --- Lógica de Interactividad (Tooltip) ---
        annot = ax.annotate("", xy=(0,0), xytext=(20,20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="white", ec="#D1D5DB", alpha=0.9),
                            arrowprops=dict(arrowstyle="->", connectionstyle="angle,angleA=0,angleB=90,rad=10"))
        annot.set_visible(False)

        def update_annot(line, ind, data):
            # ind['ind'] es una lista de índices de los puntos cercanos
            idx = ind["ind"][0]
            x, y = line.get_data()
            annot.xy = (x[idx], y[idx])
            
            # Obtener info del punto
            month_str = x[idx].strftime('%B %Y')
            total_val = y[idx]
            invoices_txt = data['invoices'][idx]
            client_name = data['name']
            
            text = f"Cliente: {client_name}\nMes: {month_str}\nTotal: ${total_val:,.2f}\n------------------\n{invoices_txt}"
            annot.set_text(text)
            annot.get_bbox_patch().set_alpha(0.9)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                found = False
                for line, data in lines:
                    cont, ind = line.contains(event)
                    if cont:
                        update_annot(line, ind, data)
                        annot.set_visible(True)
                        fig.canvas.draw_idle()
                        found = True
                        break
                if not found and vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", hover)
        
        # Configurar ejes
        ax.set_xlabel('Mes', fontsize=10, color='#6B7280', labelpad=10)
        ax.set_ylabel('Total Compras (USD)', fontsize=10, color='#6B7280', labelpad=10)
        ax.set_title('Tendencia de Compras Mensuales (USD)', fontsize=14, fontweight='bold', color='#111827', pad=20)
        
        # Rejilla sutil
        ax.grid(True, linestyle='--', alpha=0.9, color='#F3F4F6')
        ax.set_facecolor('#F9FAFB')
        fig.patch.set_facecolor('#FFFFFF')
        
        # Leyenda moderna
        if clients_data:
            ax.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='#E5E7EB', fontsize=9)
        
        # Formato de fechas en eje X
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate()
        
        # Ajustar margen
        fig.tight_layout()
        
        # Integrar en tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def cargar_sedes(self):
        """Carga las sedes disponibles en el combobox"""
        try:
            self.sedes_config = self.controller.db_manager.get_sedes_config()
            sede_nombres = [s['nombre_sede'] for s in self.sedes_config]
            self.sede_combo['values'] = sede_nombres
            if sede_nombres:
                self.sede_combo.current(0)
        except Exception as e:
            self.controller.log(f"Error cargando sedes en estadísticas: {e}", "ERROR")
