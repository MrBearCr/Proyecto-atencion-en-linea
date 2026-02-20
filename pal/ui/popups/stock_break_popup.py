import tkinter as tk
from tkinter import ttk
from datetime import datetime

class StockBreakPopup:
    """
    Ventana emergente moderna para mostrar alertas de quiebre de stock (Lost Sales).
    Agrupa los quiebres por sede usando pestañas.
    """
    def __init__(self, parent, data_list):
        self.top = tk.Toplevel(parent)
        self.top.title("⚠️ Alertas de Quiebre de Stock (Ventas Perdidas)")
        self.top.geometry("1000x650")
        self.top.minsize(900, 500)
        self.top.attributes("-topmost", True)
        
        # Agrupar lista de tuplas por Sede (index 2)
        # Formato esperado: (codigo, descripcion, sede, unidades_perdidas, dias_quiebre, u_compra, u_venta)
        self.quiebres_por_sede = {}
        for q in data_list:
            sede = q[2]
            if sede not in self.quiebres_por_sede:
                self.quiebres_por_sede[sede] = []
            self.quiebres_por_sede[sede].append(q)

        # Centrar ventana
        self.top.update_idletasks()
        width = self.top.winfo_width()
        height = self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (width // 2)
        y = (self.top.winfo_screenheight() // 2) - (height // 2)
        self.top.geometry(f'{width}x{height}+{x}+{y}')

        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.configure("Quiebre.Treeview", rowheight=30, font=("Segoe UI", 10))
        style.configure("Quiebre.Treeview.Heading", font=("Segoe UI", 10, "bold"))
        
        # Colores para niveles de alerta
        style.map("Quiebre.Treeview", background=[('selected', '#0078d7')])

    def build_ui(self):
        # Header area
        header_frame = tk.Frame(self.top, bg="#f3f3f3", pady=15, padx=20)
        header_frame.pack(fill=tk.X)
        
        title_label = tk.Label(
            header_frame, 
            text="🚨 Detección de Quiebres de Stock", 
            font=("Segoe UI", 16, "bold"),
            bg="#f3f3f3",
            fg="#d32f2f"
        )
        title_label.pack(side=tk.LEFT)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        time_label = tk.Label(
            header_frame,
            text=f"Última detección: {timestamp}",
            font=("Segoe UI", 9),
            bg="#f3f3f3",
            fg="#666666"
        )
        time_label.pack(side=tk.RIGHT)

        # Info banner
        info_frame = tk.Frame(self.top, bg="#e3f2fd", pady=10)
        info_frame.pack(fill=tk.X)
        info_label = tk.Label(
            info_frame,
            text="Estos productos son de ALTA ROTACIÓN (TRA) y tienen STOCK 0 en los almacenes configurados de la sede.",
            font=("Segoe UI", 10, "italic"),
            bg="#e3f2fd",
            fg="#1976d2"
        )
        info_label.pack()

        # Content area with tabs
        self.notebook = ttk.Notebook(self.top)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for sede_name, quiebres in self.quiebres_por_sede.items():
            if not quiebres:
                continue
            
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=f" {sede_name} ({len(quiebres)}) ")
            
            self.create_quiebre_table(tab, quiebres)

        # Footer
        footer_frame = tk.Frame(self.top, pady=15, padx=20)
        footer_frame.pack(fill=tk.X)
        
        close_btn = tk.Button(
            footer_frame,
            text="Entendido, registrar revisión",
            command=self.top.destroy,
            bg="#2196f3",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT)
        
        # Hover effect
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#1976d2"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg="#2196f3"))

    def create_quiebre_table(self, container, data):
        table_frame = tk.Frame(container)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        cols = ("codigo", "descripcion", "perdidas", "dias", "u_liquidacion", "u_venta")
        tree = ttk.Treeview(
            table_frame, 
            columns=cols, 
            show="headings", 
            style="Quiebre.Treeview",
            selectmode="browse"
        )
        
        # Scrollbar
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.heading("codigo", text="Código")
        tree.heading("descripcion", text="Descripción")
        tree.heading("perdidas", text="Venta Perdida")
        tree.heading("dias", text="Días en 0")
        tree.heading("u_liquidacion", text="Últ. Liquid.")
        tree.heading("u_venta", text="Última Venta")
        
        tree.column("codigo", width=100, anchor=tk.CENTER)
        tree.column("descripcion", width=300, anchor=tk.W)
        tree.column("perdidas", width=100, anchor=tk.CENTER)
        tree.column("dias", width=80, anchor=tk.CENTER)
        tree.column("u_liquidacion", width=100, anchor=tk.CENTER)
        tree.column("u_venta", width=100, anchor=tk.CENTER)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert data (formato tupla de app.py)
        # (codigo, descripcion, sede, unidades_perdidas, dias_quiebre, u_compra, u_venta)
        for q in data:
            try:
                unidades = int(round(float(q[3])))
            except (ValueError, TypeError):
                unidades = 0
                
            tree.insert("", tk.END, values=(
                q[0], # codigo
                q[1], # descripcion
                f"{unidades}", # unidades perdidas (entero)
                f"{q[4]} d", # dias quiebre
                q[5].strftime("%Y-%m-%d") if q[5] and hasattr(q[5], 'strftime') else (q[5] if q[5] else "N/A"), # ultima liquidacion (q[5] is u_compra)
                q[6].strftime("%Y-%m-%d") if q[6] and hasattr(q[6], 'strftime') else (q[6] if q[6] else "N/A") # ultima venta
            ))

# Singleton helper to avoid multiple concurrent popups
_active_popup = None

def show_stock_break_popup(parent, quiebres_por_sede):
    global _active_popup
    if _active_popup and _active_popup.top.winfo_exists():
        # Update existing popup? For now just bring to front
        _active_popup.top.lift()
        return
    
    _active_popup = StockBreakPopup(parent, quiebres_por_sede)
