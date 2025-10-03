#!/usr/bin/env python3
"""
Demo del botón de recarga del módulo de stock
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class StockReloadDemo:
    def __init__(self, root):
        self.root = root
        self.root.title("Demo - Botón de Recarga del Módulo de Stock")
        self.root.geometry("800x600")
        
        # Variables para simular el estado de la aplicación
        self.modules_enabled = {"stock": True}
        self.stock_full_loading_started = False
        self.cached_alertas = []
        self.current_page = 1
        
        self.setup_ui()
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Título
        title_label = ttk.Label(main_frame, text="🚨 Módulo de Stock - Demo Recarga", 
                               font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=10)
        
        # Frame de acciones (simulando la estructura real)
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(action_frame, text="Acciones disponibles:").pack(side=tk.LEFT)
        
        # Botón exportar CSV (simulado)
        ttk.Button(action_frame, text="📥 Exportar CSV", 
                  command=self.exportar_csv_demo).pack(side=tk.LEFT, padx=5)
        
        # Botón de recarga (el que implementamos)
        ttk.Button(action_frame, text="🔄 Recargar", 
                  command=self.recargar_stock).pack(side=tk.LEFT, padx=5)
        
        # Barra de estado
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.api_status = ttk.Label(status_frame, text="API: Lista", foreground="green")
        self.api_status.pack(side=tk.LEFT)
        
        self.global_progress = ttk.Progressbar(status_frame, orient="horizontal", length=200)
        self.global_progress.pack(side=tk.RIGHT, padx=10)
        self.global_progress.pack_forget()  # Ocultar inicialmente
        
        # Área de logs
        log_frame = ttk.LabelFrame(main_frame, text="📋 Logs de Sistema")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Text widget para logs con scrollbar
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.logs_text = tk.Text(text_frame, height=15, wrap=tk.WORD, state='disabled')
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.logs_text.yview)
        self.logs_text.configure(yscrollcommand=scrollbar.set)
        
        self.logs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configurar colores para logs
        self.logs_text.tag_configure("INFO", foreground="blue")
        self.logs_text.tag_configure("SUCCESS", foreground="green", font=("Consolas", 9, "bold"))
        self.logs_text.tag_configure("WARNING", foreground="orange")
        self.logs_text.tag_configure("ERROR", foreground="red", font=("Consolas", 9, "bold"))
        self.logs_text.tag_configure("DEBUG", foreground="gray")
        
        # Botón para limpiar logs
        ttk.Button(log_frame, text="🗑️ Limpiar Logs", 
                  command=self.limpiar_logs).pack(pady=5)
        
        # Log inicial
        self.log("🚀 Demo del sistema de recarga de stock iniciada", "INFO")
        self.log("💡 Presiona el botón '🔄 Recargar' para probar la funcionalidad", "INFO")
    
    def log(self, message, level="INFO"):
        """Simula el sistema de logs de la aplicación real"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        self.logs_text.configure(state='normal')
        self.logs_text.insert(tk.END, log_entry, level)
        self.logs_text.see(tk.END)
        self.logs_text.configure(state='disabled')
    
    def limpiar_logs(self):
        """Limpia el área de logs"""
        self.logs_text.configure(state='normal')
        self.logs_text.delete('1.0', tk.END)
        self.logs_text.configure(state='disabled')
    
    def exportar_csv_demo(self):
        """Simulación del botón exportar CSV"""
        self.log("📥 Exportar CSV presionado (demo)", "INFO")
        messagebox.showinfo("Demo", "Esta es una simulación del botón Exportar CSV")
    
    def recargar_stock(self):
        """Función de recarga del stock (copia de la implementación real)"""
        if not self.modules_enabled.get("stock", False):
            self.log("Módulo de stock deshabilitado", "WARNING")
            return
        
        # Confirmar acción con el usuario
        if not messagebox.askyesno(
            "Confirmar Recarga", 
            "¿Está seguro de que desea recargar completamente el módulo de stock?\n\n"
            "Esto incluirá:\n"
            "• Recarga de filtros jerárquicos\n"
            "• Actualización de alertas desde la BD\n"
            "• Reinicio de la carga paralela\n"
            "• Limpieza de cachés"
        ):
            self.log("❌ Recarga cancelada por el usuario", "INFO")
            return
            
        try:
            # Simular verificación de conexión
            self.log("🔍 Verificando conexión a la base de datos...", "INFO")
            time.sleep(0.5)  # Simular tiempo de verificación
            
            # Mostrar progreso
            self.api_status.config(text="Recargando stock...", foreground="#004C97")
            self.global_progress.pack(side=tk.RIGHT, padx=10)
            self.global_progress.config(mode="indeterminate")
            self.global_progress.start(10)
            
            self.log("🔄 Iniciando recarga completa del módulo de stock...", "INFO")
            
            # Simular proceso de recarga paso a paso
            def proceso_recarga():
                # 1. Resetear estado
                self.stock_full_loading_started = False
                self.log("1️⃣ Reseteando estado de carga paralela...", "INFO")
                time.sleep(1)
                
                # 2. Limpiar caches
                self.cached_alertas = []
                self.log("2️⃣ Limpiando cachés de datos...", "INFO")
                time.sleep(1)
                
                # 3. Recargar filtros
                self.log("3️⃣ Recargando filtros jerárquicos...", "INFO")
                time.sleep(1.5)
                self.log("✅ Filtros jerárquicos recargados", "SUCCESS")
                
                # 4. Actualizar alertas
                self.log("4️⃣ Forzando actualización de alertas...", "INFO")
                time.sleep(2)
                self.log("✅ Alertas de stock actualizadas", "SUCCESS")
                
                # 5. Jerarquía
                self.log("5️⃣ Iniciando recarga de jerarquía en hilo paralelo...", "INFO")
                time.sleep(1)
                self.log("✅ Recarga de jerarquía iniciada", "SUCCESS")
                
                # 6. Resetear página
                self.current_page = 1
                self.log("6️⃣ Página actual reseteada a 1", "INFO")
                
                # 7. Aplicar filtros
                self.log("7️⃣ Aplicando filtros actuales...", "INFO")
                time.sleep(1)
                
                # Finalizar
                self.log("🎉 Recarga del módulo de stock completada exitosamente", "SUCCESS")
                
                # Actualizar UI en hilo principal
                self.root.after(0, self.finalizar_recarga)
            
            # Ejecutar en hilo separado para no bloquear UI
            threading.Thread(target=proceso_recarga, daemon=True).start()
            
        except Exception as e:
            error_msg = f"Error recargando módulo de stock: {str(e)}"
            self.log(error_msg, "ERROR")
            self.api_status.config(text="API: Error", foreground="red")
            self.finalizar_recarga()
    
    def finalizar_recarga(self):
        """Finaliza el proceso de recarga y actualiza la UI"""
        try:
            self.global_progress.stop()
            self.global_progress.pack_forget()
            self.api_status.config(text="API: Lista", foreground="green")
            self.log("🏁 Proceso de recarga finalizado", "INFO")
        except Exception:
            pass

def main():
    root = tk.Tk()
    app = StockReloadDemo(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n🛑 Demo terminada por el usuario")

if __name__ == "__main__":
    main()