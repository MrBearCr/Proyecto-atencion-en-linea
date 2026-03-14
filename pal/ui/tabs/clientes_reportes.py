import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import os
from tkinter import filedialog
from pal.services.exports import export_clientes_reporte_excel, EXCEL_AVAILABLE

class ClientesReportesTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.sedes_config = []
        self.selected_sede_config = None
        self.vad20_conn = None 
        self.current_report_data = [] # Para exportar a Excel

        self.create_widgets()
        self.load_sedes_config()

    def create_widgets(self):
        # Frame de Controles (filtros, botones)
        control_frame = ttk.Frame(self)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(control_frame, text="Seleccionar Sede:").pack(side=tk.LEFT, padx=5)
        
        self.sede_var = tk.StringVar()
        self.sede_combobox = ttk.Combobox(control_frame, textvariable=self.sede_var, state="readonly", width=20)
        self.sede_combobox.pack(side=tk.LEFT, padx=5)
        self.sede_combobox.bind("<<ComboboxSelected>>", self.on_sede_selected)
        
        # --- Controles de Fecha ---
        # --- Controles de Período y Fecha ---
        ttk.Label(control_frame, text="Período:").pack(side=tk.LEFT, padx=(15, 0))
        self.periodo_combo = ttk.Combobox(control_frame, state='readonly', width=18)
        self.periodo_combo['values'] = ("7 días", "15 días", "30 días", "60 días", "90 días", "180 días", "365 días", "Personalizado")
        self.periodo_combo.current(2) # 30 días por defecto
        self.periodo_combo.pack(side=tk.LEFT, padx=5)
        self.periodo_combo.bind("<<ComboboxSelected>>", self._on_period_change)

        ttk.Label(control_frame, text="Desde:").pack(side=tk.LEFT, padx=(15, 0))
        today = datetime.now()
        self.fecha_inicio_entry = DateEntry(control_frame, width=12, date_pattern='yyyy-mm-dd', background='#004C97', foreground='white')
        self.fecha_inicio_entry.set_date(today)
        self.fecha_inicio_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(control_frame, text="Hasta:").pack(side=tk.LEFT, padx=(10, 0))
        self.fecha_fin_entry = DateEntry(control_frame, width=12, date_pattern='yyyy-mm-dd', background='#004C97', foreground='white')
        self.fecha_fin_entry.set_date(today)
        self.fecha_fin_entry.pack(side=tk.LEFT, padx=5)

        # Segunda fila de controles (Filtros de búsqueda)
        search_frame = ttk.Frame(self)
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(search_frame, text="RIF/ID:").pack(side=tk.LEFT, padx=(5, 0))
        self.rif_filter_entry = ttk.Entry(search_frame, width=15)
        self.rif_filter_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(search_frame, text="Descripción:").pack(side=tk.LEFT, padx=(15, 0))
        self.desc_filter_entry = ttk.Entry(search_frame, width=30)
        self.desc_filter_entry.pack(side=tk.LEFT, padx=5)

        # Barra de progreso y estado
        self.progress_frame = ttk.Frame(search_frame)
        self.progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, mode='determinate', length=150)
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(self.progress_frame, text="", font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.btn_generar_reporte = ttk.Button(search_frame, text="Generar Reporte", command=self.generar_reporte)
        self.btn_generar_reporte.pack(side=tk.LEFT, padx=5)

        self.btn_exportar_excel = ttk.Button(search_frame, text="Excel", command=self.export_to_excel, state=tk.DISABLED)
        self.btn_exportar_excel.pack(side=tk.LEFT, padx=5)
        
        # Botón para volver al menú de clientes
        back_button = ttk.Button(control_frame, text="↩ Volver", command=lambda: self.controller.show_clientes_sub_view('menu'))
        back_button.pack(side=tk.RIGHT, padx=10)
        
        # Frame del Treeview (resultados del reporte)
        tree_frame = ttk.Frame(self)
        tree_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configurar estilo para selección highlight
        style = ttk.Style()
        style.configure('Clientes.Treeview', rowheight=22)
        style.map('Clientes.Treeview',
                  background=[('selected', '#0D47A1')],
                  foreground=[('selected', 'white')])

        # Definir las columnas para el Treeview (para elementos padre)
        columns = ["RIF/ID", "Nombre Cliente", "Factura", "Fecha", "N° Items", "Total USD"]
        self.report_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', style='Clientes.Treeview')
        
        # Configurar encabezados y columnas
        for col in columns:
            self.report_tree.heading(col, text=col)
            self.report_tree.column(col, width=100) # Ancho por defecto

        # Configurar el ancho de las columnas parent para que se ajusten mejor
        self.report_tree.column("RIF/ID", width=100, anchor=tk.W)
        self.report_tree.column("Nombre Cliente", width=200, anchor=tk.W)
        self.report_tree.column("Factura", width=80, anchor=tk.W)
        self.report_tree.column("Fecha", width=90, anchor=tk.CENTER)
        self.report_tree.column("N° Items", width=70, anchor=tk.CENTER)
        self.report_tree.column("Total USD", width=100, anchor=tk.E)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.report_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.report_tree.xview)
        self.report_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.report_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    def load_sedes_config(self):
        """Carga la configuración de sedes desde la base de datos central."""
        try:
            self.sedes_config = self.controller.db_manager.get_sedes_config()
            sede_nombres = [sede['nombre_sede'] for sede in self.sedes_config]
            self.sede_combobox['values'] = sede_nombres
            if sede_nombres:
                self.sede_var.set(sede_nombres[0])
                self.on_sede_selected() # Seleccionar la primera sede por defecto
        except Exception as e:
            messagebox.showerror("Error de Configuración", f"No se pudo cargar la configuración de sedes: {e}")
            self.sedes_config = []
            self.sede_combobox['values'] = []
            self.sede_var.set("")
            self.btn_generar_reporte.config(state=tk.DISABLED)

    def on_sede_selected(self, event=None):
        """Se ejecuta cuando se selecciona una sede del combobox."""
        selected_name = self.sede_var.get()
        self.selected_sede_config = next((s for s in self.sedes_config if s['nombre_sede'] == selected_name), None)
        
        if self.vad20_conn:
            try:
                self.vad20_conn.close()
                self.vad20_conn = None
            except Exception as e:
                self.controller.log(f"Error cerrando conexión VAD20 anterior: {e}", "WARNING")
        
        if self.selected_sede_config:
            self.controller.log(f"Sede seleccionada: {self.selected_sede_config['nombre_sede']}", "INFO")
            self.btn_generar_reporte.config(state=tk.NORMAL)
        else:
            self.controller.log("Ninguna sede seleccionada o configurada.", "WARNING")
            self.btn_generar_reporte.config(state=tk.DISABLED)

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

    def generar_reporte(self):
        """Inicia la generación del reporte en segundo plano."""
        if not self.selected_sede_config:
            messagebox.showwarning("Selección de Sede", "Por favor, seleccione una sede para generar el reporte.")
            return

        fecha_inicio = self.fecha_inicio_entry.get_date()
        fecha_fin = self.fecha_fin_entry.get_date()
        
        # Deshabilitar interfaz
        self.btn_generar_reporte.state(['disabled'])
        self.report_tree.delete(*self.report_tree.get_children())
        self.status_label.config(text="Procesando datos...", foreground="#004C97")
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start()
        
        rif_filter = self.rif_filter_entry.get().strip()
        desc_filter = self.desc_filter_entry.get().strip()

        # Ejecutar en hilo
        import threading
        thread = threading.Thread(
            target=self._background_generar_reporte,
            args=(fecha_inicio, fecha_fin, rif_filter, desc_filter),
            daemon=True
        )
        thread.start()

    def _background_generar_reporte(self, fecha_inicio, fecha_fin, rif_filter, desc_filter):
        """Procesa el reporte en segundo plano con USD históricos desde BD"""
        try:
            # 1. Conexión a la BD VAD20 de la sede
            conn_sede = self.controller.db_manager.connect_to_vad20_sede(self.selected_sede_config)
            if not conn_sede:
                raise Exception("No se pudo conectar a la base de datos de la sede")
            
            # Callback para actualizar barra de progreso
            def update_progress(current, total):
                if total > 0:
                    percent = (current / total) * 100
                    self.after(0, lambda: self.progress_bar.config(value=percent))
                    self.after(0, lambda: self.status_label.config(text=f"Procesando: {int(percent)}%"))

            # Obtener datos (ahora con TotalUSD calculado en SQL por cada factura/día)
            report_data_raw = self.controller.db_manager.get_reporte_compras_por_cliente(
                conn_sede, fecha_inicio, fecha_fin, 
                rif_filter=rif_filter, desc_filter=desc_filter,
                progress_callback=update_progress
            )
            conn_sede.close()
            
            # Procesar datos (agrupación de facturas y sus productos)
            invoices = {}
            for row in report_data_raw:
                # row: (rif, name, num, date, prod_code, total_bs, desc, dept, grupo, sub, marca, total_usd, cantidad)
                rif, client_name, invoice_num, invoice_date, product_code, n_total_bs, \
                p_desc, p_dept, p_grupo, p_sub, p_marca, p_qty, total_usd = row
                
                invoice_key = (rif, invoice_num)
                
                if invoice_key not in invoices:
                    # Primera vez que vemos esta factura
                    invoices[invoice_key] = {
                        'rif': rif, 
                        'client_name': client_name, 
                        'invoice_num': invoice_num,
                        'invoice_date': invoice_date, 
                        'total_bs': float(n_total_bs) if n_total_bs else 0.0,
                        'total_usd': float(total_usd) if total_usd else 0.0,
                        'products_map': {} # Use a map for aggregation: (code, metadata) -> qty
                    }
                
                # Añadir/Agregar el producto
                if product_code:
                    metadata_key = (product_code, p_desc, p_dept, p_grupo, p_sub, p_marca)
                    current_qty = float(p_qty) if p_qty else 0.0
                    
                    if metadata_key not in invoices[invoice_key]['products_map']:
                        invoices[invoice_key]['products_map'][metadata_key] = current_qty
                    else:
                        invoices[invoice_key]['products_map'][metadata_key] += current_qty
            
            # Convertir a lista y ordenar por monto descendente
            invoices_list = list(invoices.values())
            for inv in invoices_list:
                # Reconstruir products_full desde el map
                inv['products_full'] = []
                for (code, desc, dept, grupo, sub, marca), total_qty in inv['products_map'].items():
                    inv['products_full'].append((code, desc, dept, grupo, sub, marca, total_qty))
                
                # Ordenar productos por código
                inv['products_full'].sort(key=lambda x: x[0])
            
            invoices_list.sort(key=lambda x: x['total_usd'], reverse=True)
            
            # Guardar para exportar
            self.current_report_data = invoices_list
            
            # Actualizar UI
            self.after(0, lambda: self._on_report_loaded(invoices_list))
            
        except Exception as e:
            self.after(0, lambda: self._on_report_error(str(e)))

    def _on_report_loaded(self, invoices_list):
        """Muestra los resultados en el Treeview"""
        self.btn_generar_reporte.state(['!disabled'])
        if invoices_list:
            self.btn_exportar_excel.state(['!disabled'])
        else:
            self.btn_exportar_excel.state(['disabled'])
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=100)
        self.status_label.config(text="✓ Completado", foreground="#10B981")
        
        for invoice_data in invoices_list:
            formatted_date = invoice_data['invoice_date'].strftime('%Y-%m-%d')
            num_items = len(invoice_data['products_full'])
            parent_values = (
                str(invoice_data['rif']), str(invoice_data['client_name']),
                str(invoice_data['invoice_num']), formatted_date,
                str(num_items), f"{invoice_data['total_usd']:,.2f}"
            )
            parent_iid = self.report_tree.insert("", tk.END, values=parent_values, open=False) 
            for p_tuple in invoice_data['products_full']:
                # p_tuple: (code, desc, dept, grupo, sub, marca, qty)
                # Mostramos [Cant] x Código - Descripción
                p_code, p_desc, p_qty = p_tuple[0], p_tuple[1], p_tuple[6]
                qty_str = f"{p_qty:g}" if p_qty is not None else "0" # g format remove trailing zeros
                display_text = f"{qty_str} x {p_code} - {p_desc if p_desc else ''}".strip()
                self.report_tree.insert(parent_iid, tk.END, values=(display_text, "", "", "", "", ""))

        messagebox.showinfo("Reporte Generado", f"Se encontraron {len(invoices_list)} facturas.")

    def _on_report_error(self, message):
        """Maneja errores en el reporte"""
        self.btn_generar_reporte.state(['!disabled'])
        self.btn_exportar_excel.state(['disabled'])
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=0)
        self.status_label.config(text="⚠ Error", foreground="#EF4444")
        messagebox.showerror("Error", f"No se pudo generar el reporte: {message}")

    def export_to_excel(self):
        """Exporta los datos actuales a Excel."""
        if not self.current_report_data:
            messagebox.showwarning("Exportar", "No hay datos para exportar.")
            return
            
        if not EXCEL_AVAILABLE:
            messagebox.showerror("Error", "La librería openpyxl no está instalada.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"Reporte_Clientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
        if not filename:
            return
            
        try:
            sede_nombre = self.selected_sede_config['nombre_sede'] if self.selected_sede_config else "Desconocida"
            num_rows = export_clientes_reporte_excel(
                filename, 
                self.current_report_data, 
                sede_nombre,
                db_manager=self.controller.db_manager,
                fecha_inicio=self.fecha_inicio_entry.get_date(),
                fecha_fin=self.fecha_fin_entry.get_date()
            )
            
            messagebox.showinfo("Exportación Exitosa", f"Se han exportado {num_rows} registros a:\n{filename}")
            
            # Intentar abrir el archivo
            try:
                os.startfile(filename)
            except:
                pass
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar el archivo: {e}")

    def on_tab_close(self):
        """Se llama cuando la pestaña es cerrada para limpiar recursos."""
        if self.vad20_conn:
            try:
                self.vad20_conn.close()
                self.vad20_conn = None
            except Exception as e:
                self.controller.log(f"Error cerrando conexión VAD20 al cerrar pestaña: {e}", "WARNING")
        self.controller.log("Pestaña de reportes de clientes cerrada. Conexión VAD20 limpia.", "INFO")
