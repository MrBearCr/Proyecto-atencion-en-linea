import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta

class ClientesReportesTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.sedes_config = []
        self.selected_sede_config = None
        self.vad20_conn = None # Conexión a la BD VAD20 de la sede seleccionada

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
        # --- Controles de Fecha (Solo Hoy) ---
        ttk.Label(control_frame, text="Fecha (Hoy):").pack(side=tk.LEFT, padx=(15, 0))
        
        today = datetime.now()
        
        self.fecha_inicio_entry = DateEntry(control_frame, width=12, date_pattern='yyyy-mm-dd')
        self.fecha_inicio_entry.set_date(today)
        self.fecha_inicio_entry.configure(state='disabled')
        self.fecha_inicio_entry.pack(side=tk.LEFT, padx=5)

        # Ocultamos el campo "Hasta" ya que es redundante si solo es HOY
        self.fecha_fin_entry = DateEntry(control_frame, width=12, date_pattern='yyyy-mm-dd')
        self.fecha_fin_entry.set_date(today)
        self.fecha_fin_entry.configure(state='disabled')
        # self.fecha_fin_entry.pack(side=tk.LEFT, padx=5) # No mostrar

        self.btn_generar_reporte = ttk.Button(control_frame, text="Generar Reporte del Día", command=self.generar_reporte)
        self.btn_generar_reporte.pack(side=tk.LEFT, padx=10)
        
        # Botón para volver al menú de clientes
        back_button = ttk.Button(control_frame, text="↩ Volver", command=lambda: self.controller.show_clientes_sub_view('menu'))
        back_button.pack(side=tk.RIGHT, padx=10)
        
        # Frame del Treeview (resultados del reporte)
        tree_frame = ttk.Frame(self)
        tree_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Definir las columnas para el Treeview (para elementos padre)
        columns = ["RIF/ID", "Nombre Cliente", "Factura", "Fecha", "N° Items", "Total USD"]
        self.report_tree = ttk.Treeview(tree_frame, columns=columns, show='headings') # 'headings' para mostrar solo los encabezados
        
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

    def generar_reporte(self):
        """Genera el reporte para la sede seleccionada y el rango de fechas (SOLO HOY)."""
        if not self.selected_sede_config:
            messagebox.showwarning("Selección de Sede", "Por favor, seleccione una sede para generar el reporte.")
            return

        # Forzar fechas a HOY
        now = datetime.now()
        fecha_inicio = now.date()
        fecha_fin = now.date()

        # Validación de rangos eliminada porque siempre es hoy == hoy

        self.report_tree.delete(*self.report_tree.get_children()) # Limpiar treeview
        self.vad20_conn = None # Asegurarse de que la conexión esté limpia

        try:
            # 1. Establecer conexión temporal a la BD VAD20 de la sede
            self.vad20_conn = self.controller.db_manager.connect_to_vad20_sede(self.selected_sede_config)

            # Obtener factor dolar (Usando conexión PRINCIPAL VAD10, no la de la sede)
            # MA_MONEDAS solo existe en VAD10
            # Se usa .conn porque es el atributo de conexión principal en DatabaseManager
            factor_dolar = self.controller.db_manager.get_dolar_factor(self.controller.db_manager.conn)
            if factor_dolar <= 0: factor_dolar = 1.0
            
            # 2. Obtener los datos del reporte (raw data, one row per product)
            report_data_raw = self.controller.db_manager.get_reporte_compras_por_cliente(
                self.vad20_conn, fecha_inicio, fecha_fin
            )
            
            # 3. Agrupar los datos por factura para la visualización jerárquica
            invoices = {}
            for row in report_data_raw:
                # Ahora row tiene 6 elementos: RIF, Nombre, Num, Fecha, CodProd, N_Total
                rif, client_name, invoice_num, invoice_date, product_code, n_total_bs = row
                
                invoice_key = (rif, invoice_num) # Usar RIF y número de factura como clave única
                
                if invoice_key not in invoices:
                    invoices[invoice_key] = {
                        'rif': rif,
                        'client_name': client_name,
                        'invoice_num': invoice_num,
                        'invoice_date': invoice_date,
                        'total_bs': float(n_total_bs) if n_total_bs else 0.0,
                        'products': []
                    }
                invoices[invoice_key]['products'].append(product_code)
            
            # 4. Calcular totales y ordenar de mayor a menor monto USD
            invoices_list = []
            for invoice_data in invoices.values():
                invoice_data['total_usd'] = invoice_data['total_bs'] / factor_dolar
                invoices_list.append(invoice_data)
            
            # Ordenar por total_usd descendente (mayor a menor)
            invoices_list.sort(key=lambda x: x['total_usd'], reverse=True)

            # 5. Insertar datos en el Treeview jerárquicamente
            for invoice_data in invoices_list:
                formatted_date = invoice_data['invoice_date'].strftime('%Y-%m-%d')
                num_items = len(invoice_data['products'])
                
                # Elemento padre para la factura
                parent_values = (
                    str(invoice_data['rif']),
                    str(invoice_data['client_name']),
                    str(invoice_data['invoice_num']),
                    formatted_date,
                    str(num_items),
                    f"{invoice_data['total_usd']:,.2f}"
                )
                # Insertar el parent item, inicialmente cerrado
                parent_iid = self.report_tree.insert("", tk.END, values=parent_values, open=False) 
                
                # Elementos hijo para los productos bajo esta factura
                for product_code in invoice_data['products']:
                    # Los child items solo mostrarán el código de producto.
                    # Rellenamos columnas vacías para alinear
                    self.report_tree.insert(parent_iid, tk.END, values=(str(product_code), "", "", "", "", ""))

            messagebox.showinfo("Reporte Generado", f"Se encontraron {len(invoices)} facturas para {self.selected_sede_config['nombre_sede']}.")

        except Exception as e:
            messagebox.showerror("Error al Generar Reporte", f"No se pudo generar el reporte: {e}")
        finally:
            # 5. Siempre cerrar la conexión VAD20
            if self.vad20_conn:
                try:
                    self.vad20_conn.close()
                    self.vad20_conn = None
                    self.controller.log("Conexión VAD20 cerrada.", "INFO")
                except Exception as e:
                    self.controller.log(f"Error cerrando conexión VAD20: {e}", "ERROR")


    def on_tab_close(self):
        """Se llama cuando la pestaña es cerrada para limpiar recursos."""
        if self.vad20_conn:
            try:
                self.vad20_conn.close()
                self.vad20_conn = None
            except Exception as e:
                self.controller.log(f"Error cerrando conexión VAD20 al cerrar pestaña: {e}", "WARNING")
        self.controller.log("Pestaña de reportes de clientes cerrada. Conexión VAD20 limpia.", "INFO")