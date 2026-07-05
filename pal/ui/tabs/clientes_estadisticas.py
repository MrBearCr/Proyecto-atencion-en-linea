"""
Módulo de Estadísticas de Clientes
Muestra gráficos de compras en el tiempo para uno o más clientes
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from collections import defaultdict
import threading

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

        # Selector de Tipo de Estadística
        type_frame = ttk.Frame(controls_frame)
        type_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(type_frame, text="Ver:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.tipo_stats_combo = ttk.Combobox(type_frame, state='readonly', width=22, font=("Segoe UI", 10))
        self.tipo_stats_combo['values'] = ("Compras (USD)", "Atención por Cajera", "Mapa de Calor (Horas)")
        self.tipo_stats_combo.current(0)
        self.tipo_stats_combo.pack(side=tk.LEFT)

        # Botón Agrandar
        self.btn_agrandar = tk.Button(
            controls_frame, text="🗗 AGRANDAR", command=self.abrir_ventana_agrandada,
            bg="#F3F4F6", fg="#4B5563", font=("Segoe UI", 9, "bold"), relief="flat", padx=15, pady=8, cursor="hand2"
        )
        self.btn_agrandar.pack(side=tk.RIGHT, padx=5, pady=(10, 0))
        self.btn_agrandar.bind("<Enter>", lambda e: self.btn_agrandar.config(bg="#E5E7EB"))
        self.btn_agrandar.bind("<Leave>", lambda e: self.btn_agrandar.config(bg="#F3F4F6"))

        # Fila 2 de controles: Métrica y Estilo
        row_ext = ttk.Frame(controls_frame)
        row_ext.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(row_ext, text="Métrica:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.metrica_combo = ttk.Combobox(row_ext, state='readonly', width=18, font=("Segoe UI", 10))
        self.metrica_combo['values'] = ("Monto (USD)", "Conteo (Facturas)")
        self.metrica_combo.current(0)
        self.metrica_combo.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row_ext, text="Estilo:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.estilo_combo = ttk.Combobox(row_ext, state='readonly', width=15, font=("Segoe UI", 10))
        self.estilo_combo['values'] = ("Líneas", "Barras", "Pastel")
        self.estilo_combo.current(0)
        self.estilo_combo.pack(side=tk.LEFT)

        # Botón generar moderno
        self.btn_generar = tk.Button(
            controls_frame, text="GENERAR GRÁFICO", command=self.generar_grafico,
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
        tipo_stats = self.tipo_stats_combo.get()
        
        # El RIF solo es obligatorio para estadísticas de clientes
        if not ids_raw and tipo_stats not in ["Atención por Cajera", "Mapa de Calor (Horas)"]:
            messagebox.showwarning("Faltan Datos", "Debe ingresar al menos un RIF de cliente.")
            return

        client_ids = [rif.strip() for rif in ids_raw.split(',') if rif.strip()]
        fecha_inicio = self.fecha_inicio_entry.get_date()
        fecha_fin = self.fecha_fin_entry.get_date()
        
        metrica = self.metrica_combo.get()
        estilo = self.estilo_combo.get()
        
        # Limpiar gráfico anterior y datos previos
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        if hasattr(self, 'last_chart_data'):
            del self.last_chart_data
        
        # Deshabilitar interfaz
        self.btn_generar.config(state=tk.DISABLED)
        self.status_label.config(text="Consultando base de datos...", fg="#004C97")
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start()
        
        # Ejecutar en hilo
        thread = threading.Thread(
            target=self._background_generar_grafico,
            args=(client_ids, fecha_inicio, fecha_fin, tipo_stats, metrica, estilo),
            daemon=True
        )
        thread.start()

    def _background_generar_grafico(self, client_ids, fecha_inicio, fecha_fin, tipo_stats="Compras (USD)", metrica="Monto (USD)", estilo="Líneas"):
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

            # Obtener datos según el tipo
            if tipo_stats == "Atención por Cajera":
                # Conectar a VAD10 de la misma sede para obtener usuarios/cajeras (Estricto)
                conn_vad10 = None
                usuarios_map = {} # Iniciar vacío para evitar fallbacks globales
                
                try:
                    conn_vad10 = self.controller.db_manager.connect_to_vad10_sede(sede_info)
                    usuarios_map = self.controller.db_manager.get_ma_usuarios_map(conn_vad10)
                    self.controller.log(f"Mapa de usuarios obtenido exitosamente de VAD10 de {selected_sede}", "SUCCESS")
                except Exception as e:
                    self.controller.log(f"No se pudo conectar a VAD10 de la sede ({selected_sede}). Buscando en VAD20...", "WARNING")
                    # Fallback a la misma conexión VAD20 de la sede (por si acaso)
                    try:
                        usuarios_map = self.controller.db_manager.get_ma_usuarios_map(conn_sede)
                    except:
                        self.controller.log(f"Tampoco se pudo obtener usuarios de VAD20 de {selected_sede}.", "ERROR")
                finally:
                    if conn_vad10:
                        try:
                            conn_vad10.close()
                        except Exception:
                            pass
                
                data = self.controller.db_manager.get_client_cajera_history(
                    conn_sede, client_ids, fecha_inicio, fecha_fin, progress_callback=update_progress,
                    usuarios_map=usuarios_map
                )
            elif tipo_stats == "Mapa de Calor (Horas)":
                data = self.controller.db_manager.get_client_heatmap_history(
                    conn_sede, client_ids, fecha_inicio, fecha_fin, progress_callback=update_progress
                )
            else:
                data = self.controller.db_manager.get_client_purchase_history(
                    conn_sede, client_ids, fecha_inicio, fecha_fin, progress_callback=update_progress
                )
            
            conn_sede.close()
            
            # Actualizar UI con el resultado
            self.after(0, lambda: self._on_data_loaded(data, tipo_stats, metrica, estilo))
            
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: self._on_load_error(msg))

    def _on_data_loaded(self, rows, tipo_stats, metrica, estilo):
        """Maneja la carga exitosa de datos"""
        self.btn_generar.config(state=tk.NORMAL)
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=100)
        self.status_label.config(text="✓ Completado", fg="#10B981")
        
        if not rows:
            messagebox.showinfo("Sin Datos", "No se encontraron datos en el período seleccionado.")
            return
            
        self.last_chart_data = (rows, tipo_stats, metrica, estilo)
        self._mostrar_grafico(rows, tipo_stats, metrica, estilo)

    def _on_load_error(self, message):
        """Maneja errores durante la carga"""
        self.btn_generar.config(state=tk.NORMAL)
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=0)
        self.status_label.config(text="⚠ Error", fg="#EF4444")
        messagebox.showerror("Error", f"Fallo al cargar estadísticas: {message}")

    def _mostrar_grafico(self, rows, tipo_stats, metrica="Monto (USD)", estilo="Líneas", target_frame=None):
        """Muestra el gráfico configurado con los datos cargados"""
        display_frame = target_frame if target_frame else self.chart_frame
        
        for widget in display_frame.winfo_children():
            widget.destroy()
            
        # Crear contenedor dividido (Gráfico Izq, Resumen Der)
        main_container = tk.PanedWindow(display_frame, orient=tk.HORIZONTAL, bg="white", sashwidth=4)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        left_panel = tk.Frame(main_container, bg="white")
        main_container.add(left_panel, stretch="always")
        
        right_panel = tk.Frame(main_container, bg="#F9FAFB", width=280, highlightthickness=1, highlightbackground="#E5E7EB")
        main_container.add(right_panel, stretch="never")
        
        use_count = (metrica == "Conteo (Facturas)")

        if tipo_stats == "Mapa de Calor (Horas)":
            import numpy as np
            
            heatmap_data = np.zeros((7, 24)) # 7 días, 24 horas
            day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            
            total_valor = 0
            
            for row in rows:
                rif, name, fecha, hora, total_usd = row
                if isinstance(fecha, str):
                    try:
                        fecha = datetime.strptime(fecha.split(' ')[0], '%Y-%m-%d')
                    except:
                        pass
                if hasattr(fecha, 'weekday'):
                    day_idx = fecha.weekday()
                    if 0 <= hora < 24:
                        valor_a_sumar = 1 if use_count else total_usd
                        heatmap_data[day_idx, hora] += valor_a_sumar
                        total_valor += valor_a_sumar
            
            fig = Figure(figsize=(8, 6), dpi=100)
            ax = fig.add_subplot(111)
            
            im = ax.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')
            
            ax.set_xticks(np.arange(24))
            ax.set_yticks(np.arange(7))
            ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha="right", fontsize=8)
            ax.set_yticklabels(day_names)
            
            ax.set_title("Mapa de Calor de Facturación (Por Día y Hora)", pad=20, fontsize=12, fontweight='bold')
            ax.set_xlabel("Hora del Día", fontsize=10)
            ax.set_ylabel("Día de la Semana", fontsize=10)
            
            label_color = "Cantidad de Facturas" if use_count else "Monto Facturado (USD)"
            fig.colorbar(im, ax=ax, label=label_color)
            
            canvas = FigureCanvasTkAgg(fig, master=left_panel)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            toolbar_frame = tk.Frame(left_panel, bg="white")
            toolbar_frame.pack(fill=tk.X)
            NavigationToolbar2Tk(canvas, toolbar_frame)
            
            ttk.Label(right_panel, text="Resumen del Mapa", font=("Segoe UI", 12, "bold"), background="#F9FAFB").pack(pady=(15, 10), padx=10, anchor=tk.W)
            
            if use_count:
                ttk.Label(right_panel, text=f"Total Registros: {int(total_valor)}", font=("Segoe UI", 10), background="#F9FAFB").pack(pady=5, padx=10, anchor=tk.W)
            else:
                ttk.Label(right_panel, text=f"Total USD: ${total_valor:,.2f}", font=("Segoe UI", 10), background="#F9FAFB").pack(pady=5, padx=10, anchor=tk.W)
            
            if total_valor > 0:
                max_val = np.max(heatmap_data)
                max_pos = np.unravel_index(np.argmax(heatmap_data), heatmap_data.shape)
                ttk.Label(right_panel, text=f"Pico: {day_names[max_pos[0]]} a las {max_pos[1]:02d}:00", font=("Segoe UI", 10), background="#F9FAFB", foreground="#EF4444").pack(pady=5, padx=10, anchor=tk.W)
                if use_count:
                    ttk.Label(right_panel, text=f"Max Facturas/Hora: {int(max_val)}", font=("Segoe UI", 10), background="#F9FAFB").pack(pady=5, padx=10, anchor=tk.W)
                else:
                    ttk.Label(right_panel, text=f"Max USD/Hora: ${max_val:,.2f}", font=("Segoe UI", 10), background="#F9FAFB").pack(pady=5, padx=10, anchor=tk.W)
            return

        # Organizar datos por entidad
        entities_data = defaultdict(lambda: {'name': '', 'dates': [], 'values': [], 'invoices': []})
        totals_metadata = defaultdict(float) 
        
        for row in rows:
            # row: (id, name, date_str, value, summary)
            entity_id, entity_name, date_str, val_raw, invoices_summary = row
            
            val = float(val_raw)
            if use_count:
                try:
                    import re
                    match = re.search(r'en (\d+) tickets', invoices_summary)
                    val = float(match.group(1)) if match else 1.0
                except: val = 1.0
            
            entities_data[entity_id]['name'] = entity_name
            entities_data[entity_id]['dates'].append(datetime.strptime(date_str, '%Y-%m-%d'))
            entities_data[entity_id]['values'].append(val)
            entities_data[entity_id]['invoices'].append(invoices_summary)
            totals_metadata[entity_id] += val

        # --- Lógica de Top 10 + Otros ---
        sorted_ids = sorted(totals_metadata.keys(), key=lambda k: totals_metadata[k], reverse=True)
        top_ids = sorted_ids[:10]
        others_ids = sorted_ids[10:]
        
        final_entities = {}
        others_breakdown = []
        
        for eid in top_ids:
            final_entities[eid] = entities_data[eid]
            
        if others_ids:
            others_dates_map = defaultdict(float)
            for eid in others_ids:
                data = entities_data[eid]
                others_breakdown.append((data['name'], totals_metadata[eid]))
                for d, v in zip(data['dates'], data['values']):
                    others_dates_map[d] += v
            
            sorted_others_dates = sorted(others_dates_map.keys())
            final_entities['OTROS_ID'] = {
                'name': 'Otros (Click para detalle)',
                'dates': sorted_others_dates,
                'values': [others_dates_map[d] for d in sorted_others_dates],
                'invoices': [f"Agrupación de {len(others_ids)} elementos."] * len(sorted_others_dates)
            }

        # Crear figura
        fig = Figure(figsize=(8, 6), dpi=100)
        ax = fig.add_subplot(111)
        colors = ['#004C97', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316', 
                  '#6366F1', '#14B8A6', '#FACC15']
        
        if estilo == "Pastel":
            labels = [final_entities[eid]['name'] for eid in final_entities]
            values = [sum(final_entities[eid]['values']) for eid in final_entities]
            ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors[:len(labels)], picker=True)
            ax.axis('equal')
            
        elif estilo == "Barras":
            all_dates = sorted(list(set(d for eid in final_entities for d in final_entities[eid]['dates'])))
            x = range(len(all_dates))
            width = 0.8 / max(1, len(final_entities))
            
            for idx, (eid, data) in enumerate(final_entities.items()):
                color = colors[idx % len(colors)]
                m_vals = [0.0] * len(all_dates)
                for d, v in zip(data['dates'], data['values']):
                    if d in all_dates: m_vals[all_dates.index(d)] = v
                
                offset = (idx - (len(final_entities)-1)/2) * width
                ax.bar([p + offset for p in x], m_vals, width, label=data['name'], color=color, picker=True)
            
            ax.set_xticks(x)
            ax.set_xticklabels([d.strftime('%d/%m') for d in all_dates], rotation=45, fontsize=8)
            
            annot = ax.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points", bbox=dict(boxstyle="round", fc="white", ec="#D1D5DB", alpha=0.9), arrowprops=dict(arrowstyle="->"))
            annot.set_visible(False)
            def hover_bar(event):
                if event.inaxes == ax:
                    for patch in ax.patches:
                        cont, ind = patch.contains(event)
                        if cont:
                            annot.xy = (patch.get_x() + patch.get_width()/2, patch.get_height())
                            annot.set_text(f"{patch.get_label()}\nValor: {patch.get_height():,.2f}")
                            annot.set_visible(True)
                            fig.canvas.draw_idle()
                            return
                    if annot.get_visible():
                        annot.set_visible(False); fig.canvas.draw_idle()
            fig.canvas.mpl_connect("motion_notify_event", hover_bar)
            
        else: # Líneas
            lines = []
            for idx, (eid, data) in enumerate(final_entities.items()):
                color = colors[idx % len(colors)]
                line, = ax.plot(data['dates'], data['values'], marker='o', linestyle='-', linewidth=2.0, markersize=6, label=data['name'], color=color, picker=True, pickradius=5)
                lines.append((line, data))

            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            fig.autofmt_xdate()

            annot = ax.annotate("", xy=(0,0), xytext=(20,20), textcoords="offset points", bbox=dict(boxstyle="round", fc="white", ec="#D1D5DB", alpha=0.9), arrowprops=dict(arrowstyle="->"))
            annot.set_visible(False)
            def update_annot_line(line, ind, data):
                idx = ind["ind"][0]
                x_val_line, y_val_line = line.get_data()
                vx = x_val_line[idx]
                dt = mdates.num2date(vx) if isinstance(vx, (int, float)) else vx
                annot.xy = (vx, y_val_line[idx])
                annot.set_text(f"{data['name']}\nFecha: {dt.strftime('%d/%m/%Y')}\nValor: {y_val_line[idx]:,.2f}")

            def hover_line(event):
                if event.inaxes == ax:
                    found = False
                    for line, data in lines:
                        cont, ind = line.contains(event)
                        if cont:
                            update_annot_line(line, ind, data); annot.set_visible(True); fig.canvas.draw_idle(); found = True; break
                    if not found and annot.get_visible(): annot.set_visible(False); fig.canvas.draw_idle()
            fig.canvas.mpl_connect("motion_notify_event", hover_line)

        def on_pick(event):
            label = event.artist.get_label() if hasattr(event.artist, 'get_label') else ""
            if not label and estilo == "Pastel":
                try: label = [final_entities[eid]['name'] for eid in final_entities][event.ind[0]]
                except: return
            if "Otros" in label: self._mostrar_detalle_otros(others_breakdown, metrica)
        fig.canvas.mpl_connect('pick_event', on_pick)

        ax.set_title(f"{tipo_stats} - {metrica}", fontsize=12, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.6)
        if len(final_entities) <= 15: ax.legend(loc='upper left', fontsize=8)
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=left_panel)
        canvas.draw()
        if target_frame: NavigationToolbar2Tk(canvas, left_panel).update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Resumen Derecha
        ttk.Label(right_panel, text="Resumen del Período", font=("Segoe UI", 10, "bold"), background="#F9FAFB").pack(pady=10)
        summary_tree = ttk.Treeview(right_panel, columns=("Nombre", "Total"), show="headings", height=20)
        summary_tree.heading("Nombre", text="Nombre"); summary_tree.heading("Total", text=metrica)
        summary_tree.column("Nombre", width=150); summary_tree.column("Total", width=90, anchor=tk.E)
        summary_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        summ_data = sorted([(d['name'], sum(d['values'])) for d in entities_data.values()], key=lambda x: x[1], reverse=True)
        for n, v in summ_data:
            summary_tree.insert("", tk.END, values=(n, f"${v:,.2f}" if "Monto" in metrica else int(v)))

    def abrir_ventana_agrandada(self):
        if not hasattr(self, 'last_chart_data'): return
        rows, tipo_stats, metrica, estilo = self.last_chart_data
        top = tk.Toplevel(self); top.title("Gráfico Expandido"); top.state('zoomed')
        container = tk.Frame(top, bg="white"); container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._mostrar_grafico(rows, tipo_stats, metrica, estilo, target_frame=container)

    def _mostrar_detalle_otros(self, breakdown, metrica):
        top = tk.Toplevel(self); top.title("Detalle de Otros"); top.geometry("400x500")
        main = ttk.Frame(top, padding=20); main.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(main, columns=("nombre", "valor"), show="headings")
        tree.heading("nombre", text="Nombre"); tree.heading("valor", text=metrica)
        tree.pack(fill=tk.BOTH, expand=True)
        for n, v in sorted(breakdown, key=lambda x: x[1], reverse=True):
            tree.insert("", tk.END, values=(n, f"${v:,.2f}" if "Monto" in metrica else int(v)))
        ttk.Button(main, text="Cerrar", command=top.destroy).pack(pady=10)

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
