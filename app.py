import pyodbc
import tkinter as tk
import csv
from tkinter import ttk, messagebox, simpledialog
from tkinter import font 
from cryptography.fernet import Fernet
import keyring
import re
import configparser
import os
import webbrowser
import logging
from logging.handlers import RotatingFileHandler
import time
from typing import Optional
import socket
import http.server
import socketserver
import threading 
import json
import inspect
import math
from tkcalendar import Calendar, DateEntry
from datetime import datetime, timedelta
import requests
import bcrypt
from enum import Enum
from pal.core.errors import ErrorCode
from pal.core.credentials import SecureCredentialsManager
from pal.core.audit import AuditLogger
from pal.infrastructure.database import DatabaseManager
from pal.ui.splash import SplashScreen
from pal.ui.header import setup_styles as ui_setup_styles, create_header
from pal.ui.debug_console import DebugConsole
from pal.core.session import SessionManager
from pal.core.auth import AuthManager
from pal.services.cache import CacheDescripciones
from pal.services.envios import EnvioProgramado, ProgramadorEnvios
from pal.core.log import set_component_level
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from win10toast import ToastNotifier
from PIL import Image, ImageTk
from threading import Event, Timer


CONFIG_FILE = 'db_config.ini'
JERARQUIA_CACHE_FILE = "productos_jerarquia_cache.json"
FAVORITOS_CACHE_FILE = 'favoritos_cache.json'
JERARQUIA_CACHE_TTL = timedelta(hours=15)
LOCATION_GROUPS = {
    'BARINAS': ['0101', '0108'],
    'GUANARE': ['0401', '0402'],
    'CDT': ['0106'],
}

# Mapeo de módulos entre BD (mayúsculas) y flags de la app (minúsculas)
DB_MODULE_TO_FLAG = {
    'STOCK': 'stock',
    'TRA': 'tra',
    'MBRP': 'mbrp',
    'MENSAJES': 'envio_mensajes',
    'ESTADISTICAS': 'estadisticas',
    'CALENDARIO': 'calendario',
    'ADMIN': 'admin',
}
FLAG_TO_DB_MODULE = {v: k for k, v in DB_MODULE_TO_FLAG.items()}

def load_modules_config():
        """Lee la sección [Modules] de db_config.ini o crea valores por defecto."""
        config = configparser.ConfigParser()
        # Si no existe, load_connection_settings ya habrá creado el ini
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
        # Si no hay sección Modules, la inicializamos
        if 'Modules' not in config:
            config['Modules'] = {
                'envio_mensajes': 'True',
                'estadisticas':   'False',
                'calendario':     'False',
                'stock':          'False',
                'tra':          'False',
                'mbrp':           'False',
            }
            with open(CONFIG_FILE, 'w') as f:
                config.write(f)
        # Convertir a booleans
        mods = {}
        for key in config['Modules']:
            mods[key] = config.getboolean('Modules', key, fallback=False)
        return mods

def save_modules_config(mods: dict):
        """Guarda en [Modules] del ini el dict de estados."""
        config = configparser.ConfigParser()
        # Cargamos todo el ini existente (incluye 'Database'…)
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
        if 'Modules' not in config:
            config.add_section('Modules')
        for key, val in mods.items():
            config['Modules'][key] = 'True' if val else 'False'
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)

# === Configuración de Depuración por Módulo ===

def load_debug_config():
        """Lee la sección [Debug] de db_config.ini y devuelve flags por módulo."""
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
        if 'Debug' not in config:
            # Valores por defecto: deshabilitado
            config['Debug'] = {
                'tra': 'False',
                'stock': 'False',
                'mbrp': 'False',
                'db': 'False',
            }
            with open(CONFIG_FILE, 'w') as f:
                config.write(f)
        flags = {}
        for key in config['Debug']:
            flags[key] = config.getboolean('Debug', key, fallback=False)
        return flags

def save_debug_config(flags: dict):
        """Guarda banderas de depuración en la sección [Debug]."""
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
        if 'Debug' not in config:
            config.add_section('Debug')
        for key, val in flags.items():
            config['Debug'][key] = 'True' if val else 'False'
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)




    




class DatabaseApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()  # Ocultar ventana principal

        # Mostrar splash screen
        self.splash = SplashScreen(self.root)
        self.splash.start_animation()
        
        # Iniciar inicialización en segundo plano
        threading.Thread(target=self._initialize_app, daemon=True).start()

    def _show_initial_settings(self):
        """Muestra diálogo de configuración si no hay BD inicial."""
        try:
            if self.root.state() == 'withdrawn':
                self.root.deiconify()
            self.show_settings()
        except Exception as e:
            print(f"[ERROR] No se pudo mostrar diálogo de configuración: {e}")

    def _initialize_app(self):
        try:
            # Tu lógica de inicialización original
            self.ultimas_notificaciones = set()
            print("[DEBUG] Iniciando carga de la aplicación...", flush=True)
            
            # Inicialización de componentes críticos
            self.cred_manager = SecureCredentialsManager()
            self.enviando = False
            self.session = SessionManager(self.root)
            self.session.start_session()
            
            self.modules_enabled = load_modules_config()
            self.audit_log = AuditLogger()
            self.db_manager = DatabaseManager()
            self.auth = None
            self.permissions = None
            self.current_user = None
            self.session_token = None
            self.settings_window = None
            self.show_pwd_var = None
            self.httpd = None
            self.favoritos = set()
            self._load_favoritos_cache()
            
            # Inicialización temprana de atributos de paginación
            self.page_size = 250
            self.current_page = 1
            self.current_filter = 'TODAS'
            self.cached_alertas = []
            self.last_refresh = None
            # Carga paralela de stock
            self.stock_full_loading_started = False

            self.tra_page_size = 500
            self.tra_current_page = 1
            
            # Configuración de UI y bindings
            self.buttons = {}    
            ui_setup_styles(self)
            self.setup_modern_ui()
            # Deshabilitar UI dependiente de BD hasta conectar
            try:
                self._set_ui_connected(False)
            except Exception:
                pass
            self.setup_bindings()
            self.cache = CacheDescripciones()
            
            # Consola de debug flotante (para desarrolladores)
            self.debug_console = DebugConsole(self)
            
            # Flags de carga para evitar duplicados
            self.jerarquias_unificadas_cargadas = False
            
            # Cargar configuración de depuración por módulo
            self.debug_flags = load_debug_config()
            self.tra_debug = self.debug_flags.get('tra', False)
            self.stock_debug = self.debug_flags.get('stock', False)
            self.mbrp_debug = self.debug_flags.get('mbrp', False)
            # Configurar niveles de log por componente para reducir ruido
            try:
                set_component_level("TRA", "DEBUG" if self.tra_debug else "WARNING")
                set_component_level("STOCK", "DEBUG" if self.stock_debug else "WARNING")
                set_component_level("MBRP", "DEBUG" if self.mbrp_debug else "WARNING")
                set_component_level("DB", "DEBUG" if self.debug_flags.get('db', False) else "INFO")
            except Exception:
                pass
            try:
                # Habilitar/Deshabilitar debug en el gestor de BD
                setattr(self.db_manager, 'debug_enabled', self.debug_flags.get('db', False))
            except Exception:
                pass

            if self.modules_enabled.get("envio_mensajes", False):
                self.programador = ProgramadorEnvios(self.db_manager, self)
                self.envios_programados = EnvioProgramado(self.db_manager)

            if self.modules_enabled.get("stock", False):
                # Inicializar el notificador antes de iniciar el hilo que lo usa
                self.toaster = ToastNotifier()
                self.monitor_thread = threading.Thread(target=self.monitorear_favoritos, daemon=True)
                self.monitor_thread.start()

            if self.modules_enabled.get("tra", False):
                # Initialize TRA dictionaries before setting up UI
                self.tra_dept_dict = {}
                self.tra_group_dict = {}
                self.tra_sub_dict = {}
                
                # Inicialización de variables para carga paralela TRA
                self.cached_ventas_tra = []
                self.tra_last_refresh = None
                self.tra_full_loading_started = False
                self.tra_loader_thread = None  # Referencia al hilo de carga TRA
                self.tra_total_neto_scaneado = 0.0
                self.tra_fecha_inicio = None
                self.tra_fecha_fin = None
                self.tra_sede_codigo = None
            
            # MBRP - Movimiento de Baja Rotación de Producto
            if self.modules_enabled.get("mbrp", False):
                # Diccionarios de filtros (separados para MBRP)
                self.mbrp_dept_dict = {}
                self.mbrp_group_dict = {}
                self.mbrp_sub_dict = {}
                
                # Estado de carga MBRP
                self.cached_ventas_mbrp = []
                self.mbrp_loader_thread = None
                self.mbrp_page_size = 500
                self.mbrp_current_page = 1
                self.mbrp_fecha_inicio = None
                self.mbrp_fecha_fin = None
                self.mbrp_sede_codigo = None
            
            # Sistema de Paginacion ya inicializado arriba
            # Sistema de notificaciones y ayuda (inicializar antes de auto-connect)
            self.notification_manager = self.NotificationManager(self.root)  
            self.help_tooltips = self.HelpTooltips(self.root)  
            self.setup_tooltips()
            
            self.attempt_auto_connect()
            self.programar_actualizaciones_stock()
            
            # Verificar hilos activos en segundo plano
            self.listar_hilos_activos()
            
            print("[DEBUG] Inicialización completada exitosamente", flush=True)
            
        except Exception as e:
            print(f"[ERROR] Fallo durante la inicialización: {e}", flush=True)
            import traceback
            traceback.print_exc()
            
        finally:
            # Marcar inicialización como completada siempre
            self.splash.app_initialized.set()
            # Si no hay conexión BD y no hay login configurado, mostrar settings después del splash
            if not hasattr(self, 'auth') or not self.auth:
                self.root.after(1000, self._show_initial_settings)
            
            # No deiconificar la ventana principal aquí.
            # La ventana principal se mostrará cuando el splash complete login exitoso.

    def _inicializacion_completa(self):
        # Destruir el splash screen
        self.splash.destroy()
    
        # Mostrar ventana principal
        self.root.deiconify()

    def _load_favoritos_cache(self):
        """Carga el archivo JSON de favoritos si existe"""
        try:
            if os.path.exists(FAVORITOS_CACHE_FILE):
                with open(FAVORITOS_CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.favoritos = set(data)
            else:
                self.favoritos = set()
        except Exception:
            self.favoritos = set()

    def _save_favoritos_cache(self):
        """Guarda el set de favoritos al archivo JSON"""
        try:
            with open(FAVORITOS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(self.favoritos), f, ensure_ascii=False)
        except Exception:
            pass

    def _toggle_favorito_local(self, codigo):
        """Alterna un código en el set de favoritos y lo cachea"""
        if codigo in self.favoritos:
            self.favoritos.remove(codigo)
        else:
            self.favoritos.add(codigo)
        self._save_favoritos_cache()
        return True
    
    def _check_product_stock_alert(self, codigo):
        """Verifica si un producto tiene alerta de stock y devuelve el nivel de alerta.
        
        Args:
            codigo (str): Código del producto a verificar
            
        Returns:
            str or None: Nivel de alerta ('Crítica', 'Media', 'Leve') o None si no tiene alerta
        """
        try:
            # Si no hay alertas cacheadas, retornar None
            if not hasattr(self, 'cached_alertas') or not self.cached_alertas:
                return None
            
            # Buscar el producto en las alertas de stock
            codigo_str = str(codigo).strip()
            for alerta_codigo, _, _, nivel in self.cached_alertas:
                if str(alerta_codigo).strip() == codigo_str:
                    return nivel
            
            return None
        except Exception as e:
            self.tra_debug_log(f"Error verificando alerta de stock para {codigo}: {e}")
            return None

    def _get_favoritos_local(self):
        """Devuelve el set de códigos favoritos"""
        return set(self.favoritos)

    def obtener_descripcion_producto(self, codigo: str) -> Optional[str]:
        """Obtiene la descripción de un producto desde la base de datos."""
        try:
            result = self.db_manager.fetch_data(
                "SELECT C_DESCRI FROM MA_PRODUCTOS WHERE C_CODIGO = ?", 
                (codigo,)
            )
            # Devolver cadena directamente, sin formateo adicional
            return str(result[0][0]) if result and result[0][0] else None
        except Exception as e:
            self.log(f"Error obteniendo descripción: {str(e)}", "ERROR")
            return None
        
    def validar_stock_producto(self, codigo: str) -> bool:
        """Valida si un producto tiene stock en el depósito 0301.
        Mantiene la funcionalidad exacta de recup.py
        """
        try:
            result = self.db_manager.fetch_data(
                "SELECT n_cantidad FROM MA_DEPOPROD WHERE c_codarticulo = ? AND c_coddeposito = '0301'",
                (codigo,)
            )
            return result and result[0][0] > 0
        except Exception as e:
            self.log(f"Error validando stock: {str(e)}", "ERROR")
            return False
        
    def obtener_codigo_producto_cliente(self, numero_cliente: str) -> Optional[str]:
        """Obtiene el código de producto asociado a un cliente."""
        try:
            result = self.db_manager.fetch_data(
                "SELECT C_CODIGO FROM pal_clientes WHERE numero_cliente = ?", 
                (numero_cliente,)
            )
            return result[0][0] if result else None
        except Exception as e:
            self.log(f"Error obteniendo código de producto: {str(e)}", "ERROR")
            return None
    
    def actualizar_alertas_stock(self, force_refresh=False):
        if not self.modules_enabled.get("stock", False):
            return
        """Actualiza las alertas con paginación y caché"""
        try:
            # Ensure database connection is valid before proceeding
            if not self.db_manager.ensure_connection():
                print("No hay conexión activa a la base de datos para cargar alertas iniciales")
                return
            # Forzar refresco si han pasado más de 30 minutos
            refresh_needed = (
                force_refresh or 
                not self.last_refresh or 
                (datetime.now() - self.last_refresh).seconds > 1800
            )
        
            if refresh_needed:
                # Carga rápida inicial (limitada) para no bloquear la UI
                self.cached_alertas = self.db_manager.obtener_alertas_stock(limit=300)
                self.last_refresh = datetime.now()
                self.ultimas_notificaciones.clear()  # <-- Limpiar notificaciones
                # Resumen de distribución por nivel para diagnóstico rápido
                try:
                    leves = medias = criticas = 0
                    for _, _, stock, _ in self.cached_alertas:
                        try:
                            s = int(stock or 0)
                        except Exception:
                            s = 0
                        if s >= 15:
                            leves += 1
                        elif s >= 8:
                            medias += 1
                        else:
                            criticas += 1
                    self.stock_debug_log(f"Distribución alertas -> Leves: {leves} | Medias: {medias} | Críticas: {criticas}")
                except Exception:
                    pass
                self.log("Datos de alertas actualizados desde BD", "INFO")
            # Iniciar carga completa en segundo plano una sola vez
                try:
                    if not getattr(self, 'stock_full_loading_started', False):
                        self.stock_full_loading_started = True
                        
                        # Debug: verificar total de registros disponibles
                        try:
                            total_count = self._get_total_stock_count()
                            self.stock_debug_log(f"📃 Registros totales disponibles en BD: {total_count}")
                        except Exception as debug_e:
                            self.stock_debug_log(f"⚠️ No se pudo obtener total de registros: {debug_e}")
                        
                        threading.Thread(target=self._background_load_alertas_stock, daemon=True).start()
                        self.log("Carga paralela de alertas iniciada", "INFO")
                except Exception as e:
                    self.log(f"No se pudo iniciar carga paralela: {e}", "ERROR")
        
        except Exception as e:
            print(f"Error al actualizar alertas: {str(e)}")
            self.log(f"Error crítico al actualizar alertas: {str(e)}", "ERROR")
    
    def recargar_stock(self):
        """Recarga completamente el módulo de stock de forma asíncrona sin bloquear la UI"""
        if not self.modules_enabled.get("stock", False):
            self.log("Módulo de stock deshabilitado", "WARNING")
            return
        
        # Confirmar acción con el usuario
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Confirmar Recarga", 
            "¿Está seguro de que desea recargar completamente el módulo de stock?\n\n"
            "Esto incluirá:\n"
            "• Recarga de filtros jerárquicos\n"
            "• Actualización de alertas desde la BD\n"
            "• Reinicio de la carga paralela\n"
            
        ):
            return
        
        # Verificar conexión
        if not hasattr(self.db_manager, 'conn') or not self.db_manager.conn:
            self.log("No hay conexión activa a la base de datos", "ERROR")
            messagebox.showerror("Error de Conexión", "No hay conexión activa a la base de datos.")
            return
        
        # Iniciar recarga asíncrona
        self.log("🚀 Iniciando recarga asíncrona del módulo de stock...", "INFO")
        threading.Thread(target=self._recargar_stock_async, daemon=True).start()
    
    def _recargar_stock_async(self):
        """Ejecuta la recarga completa del stock en segundo plano con actualizaciones progresivas de UI"""
        import time
        start_time = time.perf_counter()
        
        try:
            # FASE 1: Inicialización y limpieza (5%)
            self._update_stock_reload_progress(5, "Inicializando recarga...")
            
            # Resetear estado de carga paralela
            self.stock_full_loading_started = False
            
            # Limpiar caches
            self.cached_alertas = []
            self.last_refresh = None
            if hasattr(self, 'all_jerarquia'):
                self.all_jerarquia = {}
            if hasattr(self, 'producto_jerarquia'):
                self.producto_jerarquia = {}
            
            time.sleep(0.3)  # Dar tiempo para que UI se actualice
            
            # FASE 2: Recargar filtros jerárquicos (25%)
            self._update_stock_reload_progress(10, "Cargando departamentos...")
            self.root.after(0, self._load_stock_filters_async_step1)
            time.sleep(0.5)
            
            self._update_stock_reload_progress(25, "Filtros jerárquicos cargados")
            self.root.after(0, lambda: self.log("✅ Filtros jerárquicos recargados", "SUCCESS"))
            
            # FASE 3: Cargar alertas iniciales (50%)
            self._update_stock_reload_progress(30, "Cargando alertas de stock...")
            
            try:
                # Cargar primer lote de alertas (limitado para rapidez)
                alertas_iniciales = self.db_manager.obtener_alertas_stock(limit=500)
                self.cached_alertas = alertas_iniciales or []
                self.last_refresh = datetime.now()
                self.ultimas_notificaciones.clear()
                
                self._update_stock_reload_progress(50, f"Cargadas {len(self.cached_alertas)} alertas iniciales")
                self.root.after(0, lambda: self.log(f"✅ {len(self.cached_alertas)} alertas de stock cargadas", "SUCCESS"))
                
            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log(f"⚠️ Error cargando alertas: {err}", "WARNING"))
                self.cached_alertas = []
            
            time.sleep(0.3)
            
            # FASE 4: Cargar jerarquía de productos (75%)
            self._update_stock_reload_progress(55, "Cargando jerarquía de productos...")
            
            try:
                from pal.services.stock import load_all_jerarquia, build_producto_jerarquia
                
                # Cargar jerarquía completa
                all_jerarquia = load_all_jerarquia(
                    self.db_manager,
                    JERARQUIA_CACHE_FILE,
                    int(JERARQUIA_CACHE_TTL.total_seconds())
                )
                self.all_jerarquia = all_jerarquia or {}
                
                self._update_stock_reload_progress(65, f"Jerarquía cargada: {len(self.all_jerarquia)} productos")
                
                # Filtrar jerarquía por códigos en alerta
                codigos_en_alerta = {str(r[0]).strip() for r in self.cached_alertas}
                self.producto_jerarquia = build_producto_jerarquia(self.all_jerarquia, codigos_en_alerta)
                
                self._update_stock_reload_progress(75, f"Jerarquía filtrada: {len(self.producto_jerarquia)} productos")
                self.root.after(0, lambda: self.log(f"✅ Jerarquía cargada: {len(self.all_jerarquia)} productos totales", "SUCCESS"))
                
            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log(f"⚠️ Error cargando jerarquía: {err}", "WARNING"))
                self.all_jerarquia = {}
                self.producto_jerarquia = {}
            
            time.sleep(0.3)
            
            # FASE 5: Resetear y aplicar filtros (90%)
            self._update_stock_reload_progress(80, "Aplicando filtros...")
            
            # Resetear página actual
            self.current_page = 1
            
            # Aplicar filtros en el hilo principal
            self.root.after(0, self.aplicar_filtro_stock)
            time.sleep(0.5)
            
            self._update_stock_reload_progress(90, "Filtros aplicados")
            
            # FASE 6: Iniciar carga completa en segundo plano (100%)
            self._update_stock_reload_progress(95, "Iniciando carga completa...")
            
            # Iniciar carga completa de alertas en background
            if not getattr(self, 'stock_full_loading_started', False):
                self.stock_full_loading_started = True
                threading.Thread(target=self._background_load_alertas_stock, daemon=True).start()
                self.root.after(0, lambda: self.log("✅ Carga paralela de alertas iniciada", "SUCCESS"))
            
            # FINALIZACIÓN (100%)
            elapsed_time = time.perf_counter() - start_time
            final_msg = f"Recarga completada en {elapsed_time:.1f}s"
            self._update_stock_reload_progress(100, final_msg)
            
            self.root.after(0, lambda: self.log(f"🎉 {final_msg}", "SUCCESS"))
            
            # Ocultar progreso después de 2 segundos
            time.sleep(2)
            self.root.after(0, self._hide_stock_reload_progress)
            
        except Exception as e:
            error_msg = f"Error en recarga asíncrona de stock: {str(e)}"
            self.root.after(0, lambda: self.log(error_msg, "ERROR"))
            self.root.after(0, lambda: self._update_stock_reload_progress(0, "Error en recarga", error=True))
            time.sleep(3)
            self.root.after(0, self._hide_stock_reload_progress)
    
    def _load_stock_filters_async_step1(self):
        """Carga filtros de stock de forma segura en el hilo principal"""
        try:
            self.load_stock_filters()
        except Exception as e:
            self.log(f"Error cargando filtros: {e}", "ERROR")
    
    def _update_stock_reload_progress(self, percentage, message, error=False):
        """Actualiza el progreso de la recarga de stock en la UI"""
        def update_ui():
            try:
                # Actualizar texto del status
                color = "red" if error else "#004C97" if percentage < 100 else "green"
                status_text = f"Stock: {message} ({percentage}%)"
                
                if hasattr(self, 'api_status'):
                    self.api_status.config(text=status_text, foreground=color)
                
                # Actualizar barra de progreso
                if hasattr(self, 'global_progress'):
                    if percentage == 0 or error:
                        # Ocultar barra en caso de error o reset
                        self.global_progress.pack_forget()
                    else:
                        # Mostrar barra determinada
                        self.global_progress.pack(side=tk.RIGHT, padx=10)
                        self.global_progress.config(mode="determinate", maximum=100, value=percentage)
                        
            except Exception as e:
                print(f"Error actualizando progreso de recarga: {e}")
        
        self.root.after(0, update_ui)
    
    def _hide_stock_reload_progress(self):
        """Oculta los indicadores de progreso de recarga"""
        try:
            if hasattr(self, 'global_progress'):
                self.global_progress.stop()
                self.global_progress.pack_forget()
            
            if hasattr(self, 'api_status'):
                self.api_status.config(text="API: Lista", foreground="green")
                
        except Exception as e:
            print(f"Error ocultando progreso: {e}")
    
    def _background_load_ventas_tra(self):
        """Carga todas las ventas TRA en segundo plano con adaptive chunking optimizado.
        
        Implementa:
        - Adaptive chunking basado en latencia objetivo
        - Cache con TTL por parámetros de consulta
        - Optimizaciones SQL con índices
        - Manejo thread-safe del pool de conexiones
        """
        if not hasattr(self, 'tra_fecha_inicio') or not hasattr(self, 'tra_fecha_fin') or not hasattr(self, 'tra_sede_codigo'):
            self.log("No hay parámetros TRA para carga paralela", "ERROR")
            return
            
        load_start_time = time.perf_counter()
        
        # Parámetros de adaptive chunking
        target_latency = 2.0  # Latencia objetivo por chunk en segundos
        min_chunk_size = 100
        max_chunk_size = 2000
        initial_chunk_size = 500
        
        # Inicializar controlador de chunks adaptativos
        from pal.core.chunks import AdaptiveChunkController
        controller = AdaptiveChunkController(
            initial=initial_chunk_size,
            min_size=min_chunk_size,
            max_size=max_chunk_size,
            target_latency=target_latency,
            fast_ratio=0.5,
            slow_ratio=1.2,
            grow_factor=1.3,
            shrink_factor=0.8,
            ema_alpha=0.4,
            cooldown=2,
        )
        
        # Parámetros de cache
        cache_key = f"tra_{self.tra_sede_codigo}_{self.tra_fecha_inicio}_{self.tra_fecha_fin}"
        
        try:
            # Verificar cache primero
            if self._check_tra_cache(cache_key):
                self.log("[TRA] Usando datos desde cache", "INFO")
                self.root.after(0, self.aplicar_filtro_tra)
                return
            
            # Inicializar variables de control
            chunk_count = 0
            total_loaded = 0
            consecutive_failures = 0
            max_consecutive_failures = 3
            
            # Usar dict para evitar duplicados y optimizar búsquedas
            existentes = {r[0]: r for r in (self.cached_ventas_tra or [])}
            initial_count = len(existentes)
            
            self.log(f"🚀 [TRA] Iniciando carga adaptativa - Cache: {cache_key}, Registros existentes: {initial_count}", "INFO")
            
            start_row = 1
            
            while True:
                chunk_start_time = time.perf_counter()
                
                # Obtener chunk usando consulta optimizada con índices
                rows = self._fetch_tra_chunk_optimized(
                    self.tra_fecha_inicio, 
                    self.tra_fecha_fin, 
                    self.tra_sede_codigo, 
                    start_row=start_row, 
                    fetch_size=controller.size
                )
                
                chunk_query_time = time.perf_counter() - chunk_start_time
                
                if not rows:
                    consecutive_failures += 1
                    # Solo loggear si es el primer fallo o el último antes de terminar
                    if consecutive_failures == 1 or consecutive_failures >= max_consecutive_failures:
                        self.tra_debug_log(
                            f"Chunk {chunk_count + 1}: Sin datos (fallo {consecutive_failures}/{max_consecutive_failures})",
                            level="WARNING"
                        )
                    
                    if consecutive_failures >= max_consecutive_failures:
                        self.log(f"[TRA] Carga finalizada - {consecutive_failures} chunks consecutivos sin datos", "INFO")
                        break
                    
                    # Ajustar parámetros para siguiente intento
                    start_row += controller.size
                    time.sleep(1.0)  # Pausa tras error
                    continue
                else:
                    consecutive_failures = 0  # Reset en éxito
                
                chunk_count += 1
                new_records = 0
                updated_records = 0
                
                # Procesar registros del chunk
                for r in rows:
                    codigo_str = str(r[0])
                    if codigo_str in existentes:
                        updated_records += 1
                    else:
                        new_records += 1
                    existentes[codigo_str] = r
                
                # Ajuste adaptativo: delegar en el controlador (EMA + cooldown)
                controller.update(chunk_query_time, len(rows))
                
                # OPTIMIZACIÓN: Guardar en cache sin clasificar (clasificamos solo al final)
                # Esto ahorra muchísimo tiempo en consultas largas (180 días)
                if chunk_count % 10 == 0:  # Cada 10 chunks (menos frecuente)
                    self._save_tra_cache(cache_key, list(existentes.values()))
                
                total_loaded += len(rows)
                
                # Logging optimizado - solo cada 5 chunks o si es importante
                total_time = time.perf_counter() - load_start_time
                avg_latency = total_time / chunk_count
                records_per_sec = total_loaded / total_time if total_time > 0 else 0
                
                # Log cada 5 chunks, al inicio, o si hay problemas de rendimiento
                should_log = (
                    chunk_count <= 2 or  # Primeros 2 chunks siempre
                    chunk_count % 5 == 0 or  # Cada 5 chunks
                    chunk_query_time > target_latency * 1.5 or  # Si es muy lento
                    len(rows) < controller.size  # Último chunk
                )
                
                if should_log:
                    self.tra_debug_log(
                        f"Chunk {chunk_count}: {len(rows)} filas | Nuevos: {new_records} | "
                        f"Total: {len(existentes)} | Latencia: {chunk_query_time:.2f}s | "
                        f"Size: {controller.size} | Velocidad: {records_per_sec:.0f} reg/s",
                        level="INFO",
                        throttle_key="chunk_progress",
                        throttle_seconds=3.0
                    )
                
                # Actualizar UI de forma eficiente (cada 3 chunks o al final para reducir overhead)
                if chunk_count % 3 == 0 or len(rows) < controller.size:
                    try:
                        self.root.after(0, self._update_tra_ui_after_chunk, len(existentes), chunk_count, records_per_sec)
                    except Exception as e:
                        self.tra_debug_log(f"Error actualizando UI TRA: {e}", level="ERROR")
                
                start_row += len(rows)
                
                # Pausa adaptativa según rendimiento (recomendación del controlador)
                time.sleep(controller.recommend_sleep(chunk_query_time))
                
                # Condición de salida optimizada
                if len(rows) < controller.size:
                    self.log(f"[TRA] Último chunk cargado: {len(rows)} registros", "INFO")
                    break
            
            # Clasificación final y guardado en cache
            from pal.services.tra import clasificar_rotacion_tra
            self.cached_ventas_tra = clasificar_rotacion_tra(list(existentes.values()))
            self._save_tra_cache(cache_key, self.cached_ventas_tra)
            
            # Estadísticas finales
            total_time = time.perf_counter() - load_start_time
            final_count = len(existentes)
            net_new = final_count - initial_count
            avg_chunk_time = total_time / chunk_count if chunk_count > 0 else 0
            
            self.log(
                f"✅ [TRA] Carga adaptativa completada: {chunk_count} chunks | "
                f"{final_count} registros totales | {net_new} nuevos | "
                f"Tiempo: {total_time:.2f}s | Promedio/chunk: {avg_chunk_time:.2f}s | "
                f"Velocidad final: {final_count / total_time:.0f} reg/s", 
                "SUCCESS"
            )
            
            # Aplicar filtros con datos completos
            try:
                self.root.after(0, self.aplicar_filtro_tra)
            except Exception as e:
                self.log(f"Error aplicando filtros TRA tras carga: {e}", "ERROR")
            
        except Exception as e:
            load_time = time.perf_counter() - load_start_time
            self.log(f"Error en carga adaptativa TRA (tiempo: {load_time:.2f}s): {str(e)}", "ERROR")
    
    def _check_tra_cache(self, cache_key):
        """Verifica si existe cache válido para los parámetros TRA dados"""
        try:
            import os
            import json
            from datetime import datetime, timedelta
            
            cache_file = f"tra_cache_{cache_key.replace('/', '_').replace(':', '_')}.json"
            cache_ttl = timedelta(hours=2)  # Cache válido por 2 horas
            
            if not os.path.exists(cache_file):
                return False
            
            # Verificar TTL
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - mtime > cache_ttl:
                self.tra_debug_log(f"Cache expirado: {cache_file}")
                try:
                    os.remove(cache_file)
                except Exception:
                    pass
                return False
            
            # Cargar datos desde cache
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            if isinstance(cached_data, list) and len(cached_data) > 0:
                self.cached_ventas_tra = [tuple(item) for item in cached_data]
                self.log(f"[TRA] Cache cargado: {len(self.cached_ventas_tra)} registros", "INFO")
                return True
            
            return False
            
        except Exception as e:
            self.tra_debug_log(f"Error verificando cache TRA: {e}")
            return False
    
    def _save_tra_cache(self, cache_key, data):
        """Guarda datos TRA en cache local con TTL"""
        try:
            import json
            
            cache_file = f"tra_cache_{cache_key.replace('/', '_').replace(':', '_')}.json"
            
            # Convertir tuplas a listas para JSON
            json_data = [list(item) if isinstance(item, tuple) else item for item in data]
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, default=str)
            
            # Solo loggear si es un guardado significativo
            if len(data) > 100:
                self.tra_debug_log(
                    f"Cache guardado: {len(data)} registros",
                    level="DEBUG",
                    throttle_key="cache_save",
                    throttle_seconds=10.0
                )
            
        except Exception as e:
            self.tra_debug_log(f"Error guardando cache TRA: {e}")
    
    def _fetch_tra_chunk_optimized(self, fecha_inicio, fecha_fin, sede_codigo, start_row=1, fetch_size=500):
        """Consulta optimizada para chunks TRA con índices y selección minimal"""
        try:
            # Consulta optimizada: solo seleccionar columnas necesarias y usar índices
            # Usar el método correcto del DatabaseManager para evitar consultas duplicadas
            return self.db_manager.obtener_ventas_por_producto_chunk(
                fecha_inicio, fecha_fin, sede_codigo, start_row, fetch_size
            )
            
        except Exception as e:
            self.tra_debug_log(f"Error en consulta TRA: {e}", level="ERROR", throttle_key="query_error", throttle_seconds=5.0)
            # Fallback a método original si la optimizada falla
            try:
                return self.db_manager.obtener_ventas_por_producto_chunk(
                    fecha_inicio, fecha_fin, sede_codigo, start_row, fetch_size
                )
            except Exception as e2:
                self.tra_debug_log(f"Error en fallback TRA: {e2}", level="ERROR")
                return []
    
    def _update_tra_ui_after_chunk(self, total_records, chunk_count, records_per_sec=0):
        """Actualiza UI TRA después de cargar un chunk en segundo plano con estadísticas de rendimiento"""
        try:
            # Evitar errores si la UI fue destruida/reconstruida
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                return
            # Actualizar status con estadísticas de rendimiento
            if hasattr(self, 'api_status') and self.api_status.winfo_exists():
                status_text = f"TRA: {total_records} registros"
                if records_per_sec > 0:
                    status_text += f" | {records_per_sec:.0f} reg/s"
                self.api_status.config(text=status_text, foreground="#004C97")
            
            # Actualizar paginación y vista si el tree existe
            if hasattr(self, 'tra_tree') and self.tra_tree and self.tra_tree.winfo_exists():
                if hasattr(self, 'tra_pagina_label') and self.tra_pagina_label.winfo_exists():
                    # Nota: solo actualizar etiqueta; el refresco completo se hace en aplicar_filtro_tra()
                    self.tra_pagina_label.config(text=f"{total_records} registros")
        except Exception as e:
            self.tra_debug_log(f"Error actualizando UI TRA: {e}", level="ERROR")
            if hasattr(self, 'aplicar_filtro_tra') and total_records > 10:
                self.aplicar_filtro_tra()
            
        except Exception as e:
            self.tra_debug_log(f"Error actualizando UI: {e}", level="ERROR", throttle_key="ui_update_error", throttle_seconds=5.0)
    
    def _background_load_ventas_tra_fast(self):
        """Versión super optimizada de carga TRA - primeros datos en <2 segundos"""
        if not hasattr(self, 'tra_fecha_inicio') or not hasattr(self, 'tra_fecha_fin') or not hasattr(self, 'tra_sede_codigo'):
            self.log("No hay parámetros TRA para carga rápida", "ERROR")
            return
        
        load_start_time = time.perf_counter()
        
        try:
            # FASE 1: Carga ultra rápida (primeros 50 registros) - <1 segundo
            self.log("🚀 TRA: Iniciando carga ultra rápida (50 registros)...", "INFO")
            
            # Obtener primeros datos rápidamente
            datos_ultra_rapidos = self.db_manager.obtener_ventas_completas_tra(
                self.tra_fecha_inicio, 
                self.tra_fecha_fin, 
                self.tra_sede_codigo, 
                limit=50
            )
            
            if not datos_ultra_rapidos:
                self.root.after(0, self._show_no_data_tra)
                return
            
            # Clasificar y mostrar inmediatamente
            from pal.services.tra import clasificar_rotacion
            self.cached_ventas_tra = clasificar_rotacion(datos_ultra_rapidos)
            phase1_time = time.perf_counter() - load_start_time
            
            # Actualizar UI inmediatamente
            self.root.after(0, lambda: self._update_tra_phase(1, len(self.cached_ventas_tra), phase1_time))
            
            # FASE 2: Carga rápida (200 registros más) - a los 2-3 segundos
            time.sleep(0.5)  # Pausa mínima
            self.tra_debug_log("Iniciando fase 2: 200 registros adicionales")
            
            datos_rapidos = self.db_manager.obtener_ventas_completas_tra(
                self.tra_fecha_inicio, 
                self.tra_fecha_fin, 
                self.tra_sede_codigo, 
                limit=250  # Total 250 (ya tenemos 50)
            )
            
            if datos_rapidos and len(datos_rapidos) > len(self.cached_ventas_tra):
                self.cached_ventas_tra = clasificar_rotacion(datos_rapidos)
                phase2_time = time.perf_counter() - load_start_time
                self.root.after(0, lambda: self._update_tra_phase(2, len(self.cached_ventas_tra), phase2_time))
            
            # FASE 3: Carga progresiva en chunks (resto de datos)
            time.sleep(1)  # Dar tiempo a la UI
            self.tra_debug_log("Iniciando fase 3: carga progresiva por chunks")
            
            chunk_size = 500
            start_row = 251  # Comenzar después de los primeros 250
            chunk_count = 0
            consecutive_failures = 0
            max_consecutive_failures = 2
            
            existentes = {r[0]: r for r in (self.cached_ventas_tra or [])}
            
            while consecutive_failures < max_consecutive_failures:
                chunk_start = time.perf_counter()
                
                # Usar función de chunk thread-safe
                chunk_data = self.db_manager.obtener_ventas_por_producto_chunk(
                    self.tra_fecha_inicio, 
                    self.tra_fecha_fin, 
                    self.tra_sede_codigo, 
                    start_row=start_row, 
                    fetch_size=chunk_size
                )
                
                if not chunk_data:
                    consecutive_failures += 1
                    self.tra_debug_log(f"Chunk vacío en posición {start_row} (fallo {consecutive_failures})")
                    start_row += chunk_size
                    continue
                
                consecutive_failures = 0
                chunk_count += 1
                new_records = 0
                
                # Añadir nuevos registros
                for r in chunk_data:
                    codigo_str = str(r[0])
                    if codigo_str not in existentes:
                        existentes[codigo_str] = r
                        new_records += 1
                
                # Actualizar cache con clasificación de rotación
                self.cached_ventas_tra = clasificar_rotacion(list(existentes.values()))
                
                chunk_time = time.perf_counter() - chunk_start
                total_time = time.perf_counter() - load_start_time
                
                self.tra_debug_log(
                    f"Chunk {chunk_count}: +{new_records} nuevos | "
                    f"Total: {len(existentes)} | "
                    f"Tiempo chunk: {chunk_time:.2f}s"
                )
                
                # Actualizar UI cada 2 chunks
                if chunk_count % 2 == 0:
                    self.root.after(0, lambda c=chunk_count, t=len(existentes): 
                                  self._update_tra_chunk_progress(c, t))
                
                start_row += len(chunk_data)
                
                # Pausa breve para no sobrecargar la BD
                time.sleep(0.1)
                
                # Si el chunk es más pequeño, probablemente sea el último
                if len(chunk_data) < chunk_size:
                    self.tra_debug_log(f"Último chunk detectado ({len(chunk_data)} < {chunk_size})")
                    break
            
            # Finalización
            total_time = time.perf_counter() - load_start_time
            final_count = len(existentes)
            
            self.log(
                f"✅ TRA: Carga completa finalizada - "
                f"{final_count} registros en {total_time:.2f}s | "
                f"{chunk_count} chunks procesados", 
                "SUCCESS"
            )
            
            # Aplicar filtros finales
            self.root.after(0, self._finalize_tra_loading)
            
        except Exception as e:
            load_time = time.perf_counter() - load_start_time
            self.log(f"Error en carga rápida TRA (tiempo: {load_time:.2f}s): {str(e)}", "ERROR")
            self.root.after(0, lambda: self._show_tra_error(str(e)))
    
    def _update_tra_phase(self, phase, count, elapsed_time):
        """Actualiza UI tras cada fase de carga TRA"""
        try:
            phase_names = {1: "Ultra Rápida", 2: "Rápida", 3: "Completa"}
            phase_name = phase_names.get(phase, f"Fase {phase}")
            
            self.api_status.config(
                text=f"TRA: {phase_name} - {count} registros ({elapsed_time:.1f}s)", 
                foreground="#004C97"
            )
            
            # Aplicar filtros para mostrar datos
            self.aplicar_filtro_tra()
            
            self.tra_debug_log(f"Fase {phase} completada: {count} registros en {elapsed_time:.1f}s")
            
        except Exception as e:
            self.tra_debug_log(f"Error actualizando fase {phase}: {e}")
    
    def _update_tra_chunk_progress(self, chunk_num, total_records):
        """Actualiza progreso durante carga por chunks"""
        try:
            self.api_status.config(
                text=f"TRA: Chunk {chunk_num} - {total_records} registros", 
                foreground="#004C97"
            )
            
            # Reaplicar filtros para mostrar datos actualizados
            self.aplicar_filtro_tra()
            
        except Exception as e:
            self.tra_debug_log(f"Error actualizando chunk {chunk_num}: {e}")
    
    def _finalize_tra_loading(self):
        """Finaliza la carga TRA"""
        try:
            self.api_status.config(text="TRA: Completo", foreground="green")
            self.aplicar_filtro_tra()
            self.log("🎉 TRA: Carga finalizada - datos listos", "SUCCESS")
        except Exception as e:
            self.tra_debug_log(f"Error finalizando carga TRA: {e}")
    
    def _show_no_data_tra(self):
        """Muestra mensaje cuando no hay datos TRA"""
        try:
            if hasattr(self, 'tra_tree'):
                self.tra_tree.delete(*self.tra_tree.get_children())
                self.tra_tree.insert("", tk.END, values=(
                    "", "No se encontraron ventas para este rango", "", "", "", "", "", ""
                ), tags=("no_data",))
            
            self.api_status.config(text="TRA: Sin datos", foreground="orange")
            messagebox.showinfo("Sin resultados", "No se encontraron ventas para ese rango y sede.")
            
        except Exception as e:
            self.tra_debug_log(f"Error mostrando 'sin datos': {e}")
    
    def _show_tra_error(self, error_msg):
        """Muestra error en la UI TRA"""
        try:
            if hasattr(self, 'tra_tree'):
                self.tra_tree.delete(*self.tra_tree.get_children())
                self.tra_tree.insert("", tk.END, values=(
                    "ERROR", f"Error cargando datos: {error_msg[:50]}...", "", "", "", "", "", ""
                ), tags=("error",))
            
            self.api_status.config(text="TRA: Error", foreground="red")
            
        except Exception as e:
            self.tra_debug_log(f"Error mostrando error: {e}")

    def mostrar_alertas_paginadas(self, datos):
        """Mostrar datos con estado de favoritos"""
        self.stock_tree.delete(*self.stock_tree.get_children())
        favoritos = self._get_favoritos_local()
    
        for codigo, desc, stock, nivel in datos:
            es_favorito = codigo in favoritos
            estado = "✓" if es_favorito else "☐"
            tags = ('favorito' if es_favorito else '', nivel.lower().replace('ítica', 'itica'))
        
            self.stock_tree.insert("", tk.END, 
                                values=(estado, codigo, desc, stock, nivel),
                                tags=tags)
        # Limpiar selección después de actualizar
        self.stock_tree.selection_remove(self.stock_tree.selection())

    def listar_hilos_activos(self):
            hilos_activos = threading.enumerate()
            self.log(f"Hilos activos: {[h.name for h in hilos_activos]}", "DEBUG")
        


    def monitorear_favoritos(self):
        """Monitorea favoritos y productos críticos de rotación alta/media"""
        self.log("[MONITOR] Hilo de monitoreo de favoritos iniciado", "INFO")
        wait_count = 0
        while True:
            try:
                if not self.db_manager.conn:
                    wait_count += 1
                    if wait_count % 6 == 0:  # Log cada 6 iteraciones (360s = 6 min)
                        self.log(f"[MONITOR] Esperando conexión BD... ({wait_count * 60}s)", "DEBUG")
                    time.sleep(60)
                    continue
                
                wait_count = 0  # Reset cuando hay conexión
            
                # Obtener favoritos desde el JSON
                favoritos = self._get_favoritos_local()
                if not favoritos:
                    time.sleep(300)
                    continue
            
                # Mantener lógica original de alertas
                try:
                    current_alerts = self.db_manager.obtener_alertas_stock()
                except Exception as e:
                    self.log(f"[MONITOR] Error obteniendo alertas: {e}", "WARNING")
                    time.sleep(300)
                    continue
            
                for codigo, desc, stock, nivel in (current_alerts or []):
                    if codigo in favoritos:
                        clave = (codigo, stock, nivel)
                        if clave not in self.ultimas_notificaciones:
                            try:
                                self.mostrar_notificacion(codigo, stock, nivel)
                                self.ultimas_notificaciones.add(clave)
                            except Exception as e:
                                self.log(f"[MONITOR] Error mostrando notificación: {e}", "WARNING")
                
                # NUEVA CARACTERÍSTICA: Detectar productos críticos de alta/media rotación
                if hasattr(self, 'cached_ventas_tra') and self.cached_ventas_tra:
                    try:
                        self._detectar_y_notificar_criticos(current_alerts or [])
                    except Exception as e:
                        self.log(f"[MONITOR] Error detectando críticos: {e}", "DEBUG")
                        
                time.sleep(300)  # 5 minutos
            
            except Exception as e:
                self.log(f"[MONITOR] Error monitoreo favoritos: {str(e)}", "ERROR")
                time.sleep(100)
    
    def _detectar_y_notificar_criticos(self, alertas_stock):
        """Detecta y notifica sobre productos de alta/media rotación con alerta de stock"""
        try:
            from pal.services.tra import detectar_alertas_rotacion_alta, generar_reporte_critico_rotacion
            
            # Detectar productos críticos
            productos_criticos = detectar_alertas_rotacion_alta(
                self.cached_ventas_tra,
                alertas_stock,
                rotaciones_objetivo=["ALTA", "MEDIA"]
            )
            
            if not productos_criticos:
                return
            
            # Generar reporte
            reporte = generar_reporte_critico_rotacion(productos_criticos)
            
            # Mostrar notificación al usuario (solo primera vez o cambios)
            # Usar hash del reporte para detectar cambios
            hash_actual = hash(str(sorted([p['codigo'] for p in productos_criticos])))
            hash_anterior = getattr(self, '_hash_criticos_anterior', None)
            
            if hash_actual != hash_anterior:
                self._mostrar_alerta_compras(reporte)
                self._hash_criticos_anterior = hash_actual
        
        except Exception as e:
            self.log(f"Error detectando productos críticos: {e}", "DEBUG")
    
    def _mostrar_alerta_compras(self, reporte):
        """Muestra alerta visual para el departamento de compras"""
        try:
            total = reporte.get('total', 0)
            if total == 0:
                return
            
            por_rotacion = reporte.get('por_rotacion', {})
            por_nivel = reporte.get('por_nivel', {})
            
            # Construir mensaje de alerta
            mensaje_titulo = f"⚠️ ALERTA CRÍTICA: {total} Producto(s) sin Stock"
            
            detalles = []
            detalles.append(f"Total productos críticos: {total}")
            
            if por_rotacion:
                detalles.append("\nPor Rotación:")
                for rotacion, cantidad in por_rotacion.items():
                    detalles.append(f"  • {rotacion}: {cantidad}")
            
            if por_nivel:
                detalles.append("\nPor Nivel de Alerta:")
                for nivel, cantidad in por_nivel.items():
                    detalles.append(f"  • {nivel}: {cantidad}")
            
            mensaje = "\n".join(detalles)
            
            # Mostrar alerta
            self.log(f"🚨 {mensaje_titulo} - {total} productos", "ERROR")
            
            # Toast notification (si disponible)
            try:
                if hasattr(self, 'toaster'):
                    self.toaster.show_toast(
                        "ALERTA DE COMPRAS",
                        f"{total} producto(s) de alta/media rotación sin stock",
                        duration=15,
                        threaded=False
                    )
            except Exception:
                pass
        
        except Exception as e:
            self.log(f"Error mostrando alerta de compras: {e}", "ERROR")


    def mostrar_notificacion(self, codigo, stock, nivel):
        """
        Muestra un toast con el nivel de alerta en el depósito principal
        y las existencias en las ubicaciones de transferencia.
        """
        from pal.services.stock import get_existencias_por_ubicacion
        # Base del mensaje
        mensaje = f"Código:{codigo}| Stock actual:{stock}|Nivel:{nivel} "

        # Para cada grupo de transferencia, consultar existencias vía servicio
        for region, deps in LOCATION_GROUPS.items():
            try:
                existencias = get_existencias_por_ubicacion(self.db_manager, codigo, deps)
                mensaje += f"{region}:{existencias} "
            except Exception:
                mensaje += f"{region}: error al consultar\n"

        # Mostrar toast
        self.toaster.show_toast(
            "CASAPRO STOCK",
            mensaje,
            duration=10,
            threaded=False
        )

    
    def exportar_tra_excel(self):
        """Exporta datos TRA en formato Excel con múltiples hojas y formato profesional - ASYNC"""
        import threading
        
        try:
            # Permisos: TRA.exportar
            allowed = False
            try:
                if hasattr(self, 'permissions') and self.current_user:
                    allowed = self.permissions.tiene_permiso(self.current_user['id'], 'TRA', 'exportar')
                if self.current_user and self.current_user.get('username','').lower() == 'admin':
                    allowed = True
            except Exception:
                allowed = False
            if not allowed:
                messagebox.showwarning("Permiso denegado", "No tienes permiso para exportar datos de TRA")
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='PERMISSION_DENIED', usuario_id=self.current_user['id'], modulo='TRA', detalle='exportar')
                except Exception:
                    pass
                return
            # Verificar si hay datos para exportar
            if not hasattr(self, 'cached_ventas_tra') or not self.cached_ventas_tra:
                messagebox.showwarning("Sin datos", "No hay datos TRA cargados para exportar")
                return
            
            # Verificar si openpyxl está disponible
            try:
                import openpyxl
            except ImportError:
                messagebox.showerror(
                    "Módulo no encontrado", 
                    "Para exportar en Excel necesita instalar openpyxl:\n\n"
                    "pip install openpyxl\n\n"
                    "Use la exportación CSV como alternativa."
                )
                return
            
            # Obtener los mismos datos filtrados que se muestran en la interfaz
            if not hasattr(self, 'cached_ventas_tra') or not self.cached_ventas_tra:
                messagebox.showwarning("Sin datos", "No hay datos TRA cargados para exportar")
                return
            
            # Aplicar los mismos filtros que se usan en la interfaz
            dept_cod = self.tra_dept_dict.get(self.tra_dept_var.get()) if hasattr(self, 'tra_dept_var') else None
            group_cod = None
            sub_cod = None
            
            if dept_cod and hasattr(self, 'tra_group_var'):
                group_desc = self.tra_group_var.get()
                group_cod = self.tra_group_dict.get(dept_cod, {}).get(group_desc)
                
                if group_cod and hasattr(self, 'tra_sub_var'):
                    sub_desc = self.tra_sub_var.get()
                    key = f"{dept_cod}|{group_cod}"
                    sub_cod = self.tra_sub_dict.get(key, {}).get(sub_desc)
            
            texto = self.tra_search_var.get() if hasattr(self, 'tra_search_var') else ''
            favoritos = self._get_favoritos_local()
            
            # Usar las mismas funciones de filtrado que la interfaz
            from pal.services.tra import filter_ventas_tra
            
            datos_exportar = filter_ventas_tra(
                ventas=self.cached_ventas_tra,
                dept_code=dept_cod,
                group_code=group_cod,
                sub_code=sub_cod,
                search_text=texto,
                filter_rotacion='TODAS',
                favoritos=favoritos
            )
            
            # DEBUG: Log para diagnosticar discrepancias
            self.log(f"[EXPORT DEBUG] Datos originales en cache: {len(self.cached_ventas_tra)} registros", "DEBUG")
            self.log(f"[EXPORT DEBUG] Filtros aplicados - Dept: {dept_cod}, Group: {group_cod}, Sub: {sub_cod}, Texto: '{texto}'", "DEBUG")
            self.log(f"[EXPORT DEBUG] Datos para exportar: {len(datos_exportar)} registros", "DEBUG")
            if datos_exportar:
                primer_item = datos_exportar[0]
                self.log(f"[EXPORT DEBUG] Primer item: {primer_item}", "DEBUG")
                if len(primer_item) > 5:
                    neto_raw = primer_item[5]
                    self.log(f"[EXPORT DEBUG] Neto raw del primer item: {neto_raw} (tipo: {type(neto_raw)})", "DEBUG")
            
            if not datos_exportar:
                messagebox.showwarning("Sin datos", "No hay registros TRA para exportar")
                return
            
            # Configurar progreso
            total_registros = len(datos_exportar)
            self.global_progress.pack(side=tk.RIGHT, padx=10)
            self.global_progress['value'] = 0
            self.global_progress['maximum'] = total_registros
            self.api_status.config(text="Exportando TRA: 0%", foreground="#004C97")
            
            filename = f"reporte_tra_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Callback de progreso thread-safe
            def progress_cb(i, total):
                if i % max(1, total // 50) == 0 or i == total:
                    progreso = int((i / total) * 100)
                    # Usar after() para actualizar UI de forma segura desde otro hilo
                    self.root.after(0, lambda: self._update_export_progress(i, progreso, "TRA"))
            
            # Función para ejecutar la exportación en hilo separado
            def export_thread():
                try:
                    from pal.services.exports import export_tra_excel
                    
                    total_registros = export_tra_excel(
                        filename=filename,
                        datos_tra=datos_exportar,
                        db_manager=self.db_manager,
                        progress_cb=progress_cb,
                    )
                    
                    # Notificar éxito en el hilo principal
                    self.root.after(0, lambda: self._export_success(
                        "TRA",
                        total_registros,
                        filename,
                        "• Hojas incluidas: Datos principales, Resumen por rotación, Productos de baja rotación\n"
                        "• Formato: Tablas con filtros y formato condicional"
                    ))
                    try:
                        if hasattr(self, 'audit_db') and self.current_user:
                            self.audit_db.log_action(
                                accion='EXPORT', usuario_id=self.current_user['id'], modulo='TRA', detalle=filename, exitoso=True)
                    except Exception:
                        pass
                    
                except Exception as e:
                    # Notificar error en el hilo principal
                    self.root.after(0, lambda err=str(e): self._export_error("TRA", err))
                    try:
                        if hasattr(self, 'audit_db') and self.current_user:
                            self.audit_db.log_action(
                                accion='EXPORT', usuario_id=self.current_user['id'], modulo='TRA', detalle=str(e), exitoso=False)
                    except Exception:
                        pass
            
            # Iniciar exportación en hilo separado
            thread = threading.Thread(target=export_thread, daemon=True, name="ExportTRA")
            thread.start()
            
        except Exception as e:
            self.log(f"Error iniciando exportación TRA: {str(e)}", "ERROR")
            self.api_status.config(text="API: Error", foreground="red")
            messagebox.showerror("Error en Exportación TRA", f"Error durante la exportación:\n{str(e)}")
            self._cleanup_export_progress()
    
    def exportar_mbrp_excel(self):
        """Exporta datos MBRP en formato Excel con múltiples hojas y análisis de rentabilidad - ASYNC"""
        import threading
        
        try:
            # Permisos: MBRP.exportar
            allowed = False
            try:
                if hasattr(self, 'permissions') and self.current_user:
                    allowed = self.permissions.tiene_permiso(self.current_user['id'], 'MBRP', 'exportar')
                if self.current_user and self.current_user.get('username','').lower() == 'admin':
                    allowed = True
            except Exception:
                allowed = False
            if not allowed:
                messagebox.showwarning("Permiso denegado", "No tienes permiso para exportar datos de MBRP")
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='PERMISSION_DENEGADO', usuario_id=self.current_user['id'], modulo='MBRP', detalle='exportar')
                except Exception:
                    pass
                return
            # Verificar si hay datos para exportar
            if not hasattr(self, 'cached_ventas_mbrp') or not self.cached_ventas_mbrp:
                messagebox.showwarning("Sin datos", "No hay datos MBRP cargados para exportar")
                return
            
            # Verificar si openpyxl está disponible
            try:
                import openpyxl
            except ImportError:
                messagebox.showerror(
                    "Módulo no encontrado", 
                    "Para exportar en Excel necesita instalar openpyxl:\n\n"
                    "pip install openpyxl\n\n"
                    "Use la exportación CSV como alternativa."
                )
                return
            
            # Preparar datos filtrados para exportar
            datos_exportar = getattr(self, 'mbrp_ventas_datos_filtrados', self.cached_ventas_mbrp) or self.cached_ventas_mbrp
            
            if not datos_exportar:
                messagebox.showwarning("Sin datos", "No hay registros MBRP para exportar")
                return
            
            # Configurar progreso
            total_registros = len(datos_exportar)
            self.global_progress.pack(side=tk.RIGHT, padx=10)
            self.global_progress['value'] = 0
            self.global_progress['maximum'] = total_registros
            self.api_status.config(text="Exportando MBRP: 0%", foreground="#004C97")
            
            filename = f"reporte_mbrp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Callback de progreso thread-safe
            def progress_cb(i, total):
                if i % max(1, total // 50) == 0 or i == total:
                    progreso = int((i / total) * 100)
                    # Usar after() para actualizar UI de forma segura desde otro hilo
                    self.root.after(0, lambda: self._update_export_progress(i, progreso, "MBRP"))
            
            # Función para ejecutar la exportación en hilo separado
            def export_thread():
                try:
                    from pal.services.exports import export_mbrp_excel
                    
                    total_registros = export_mbrp_excel(
                        filename=filename,
                        datos_mbrp=datos_exportar,
                        db_manager=self.db_manager,
                        progress_cb=progress_cb,
                    )
                    
                    # Notificar éxito en el hilo principal
                    self.root.after(0, lambda: self._export_success(
                        "MBRP",
                        total_registros,
                        filename,
                        "• Hojas incluidas: Datos principales, Resumen por rentabilidad, Productos críticos\n"
                        "• Formato: Tablas con filtros y formato condicional por margen"
                    ))
                    try:
                        if hasattr(self, 'audit_db') and self.current_user:
                            self.audit_db.log_action(
                                accion='EXPORT', usuario_id=self.current_user['id'], modulo='MBRP', detalle=filename, exitoso=True)
                    except Exception:
                        pass
                    
                except Exception as e:
                    # Notificar error en el hilo principal
                    self.root.after(0, lambda err=str(e): self._export_error("MBRP", err))
                    try:
                        if hasattr(self, 'audit_db') and self.current_user:
                            self.audit_db.log_action(
                                accion='EXPORT', usuario_id=self.current_user['id'], modulo='MBRP', detalle=str(e), exitoso=False)
                    except Exception:
                        pass
            
            # Iniciar exportación en hilo separado
            thread = threading.Thread(target=export_thread, daemon=True, name="ExportMBRP")
            thread.start()
            
        except Exception as e:
            self.log(f"Error iniciando exportación MBRP: {str(e)}", "ERROR")
            self.api_status.config(text="API: Error", foreground="red")
            messagebox.showerror("Error en Exportación MBRP", f"Error durante la exportación:\n{str(e)}")
            self._cleanup_export_progress()
    
    def exportar_excel(self):
        """Exporta datos de stock en formato Excel con múltiples hojas y formato avanzado - ASYNC"""
        import threading
        
        try:
            # Permisos: STOCK.exportar
            allowed = False
            try:
                if hasattr(self, 'permissions') and self.current_user:
                    allowed = self.permissions.tiene_permiso(self.current_user['id'], 'STOCK', 'exportar')
                if self.current_user and self.current_user.get('username','').lower() == 'admin':
                    allowed = True
            except Exception:
                allowed = False
            if not allowed:
                messagebox.showwarning("Permiso denegado", "No tienes permiso para exportar datos de Stock")
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='PERMISSION_DENIED', usuario_id=self.current_user['id'], modulo='STOCK', detalle='exportar')
                except Exception:
                    pass
                return
            # Verificar si openpyxl está disponible
            try:
                import openpyxl
            except ImportError:
                messagebox.showerror(
                    "Módulo no encontrado", 
                    "Para exportar en Excel necesita instalar openpyxl:\n\n"
                    "pip install openpyxl\n\n"
                    "Use la exportación CSV como alternativa."
                )
                return
            
            # 1. Mostrar diálogo para seleccionar ubicaciones (igual que CSV)
            dialog = tk.Toplevel(self.root)
            dialog.title("Exportar a Excel - Seleccionar Ubicaciones")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.geometry("400x300")
        
            ubicaciones_vars = {
                ubicacion: tk.BooleanVar(value=True)
                for ubicacion in LOCATION_GROUPS
            }

            # Título del diálogo
            ttk.Label(dialog, text="Exportación Excel - Formato Profesional", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            ttk.Label(dialog, text="Incluye: Tablas con filtros, formato condicional,\nresumen por niveles y hoja de productos críticos", 
                     font=("Arial", 9)).pack(pady=(0,10))
            
            ttk.Label(dialog, text="Seleccione las ubicaciones a incluir:").pack(pady=10)
            
            for ubicacion in LOCATION_GROUPS:
                frame = ttk.Frame(dialog)
                frame.pack(anchor='w', padx=20, pady=2)
                cb = ttk.Checkbutton(
                    frame,
                    text=f"{ubicacion}",
                    variable=ubicaciones_vars[ubicacion]
                )
                cb.pack(side=tk.LEFT)
                ttk.Label(frame, text=f"({len(LOCATION_GROUPS[ubicacion])} depósitos)", 
                         foreground="gray").pack(side=tk.LEFT, padx=(5,0))

            seleccionadas = []
            def confirmar():
                nonlocal seleccionadas
                seleccionadas = [u for u, var in ubicaciones_vars.items() if var.get()]
                dialog.destroy()
        
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=20)
            ttk.Button(btn_frame, text="📈 Exportar Excel", command=confirmar).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

            dialog.wait_window()
            if not seleccionadas:
                return

            # 2. Obtener datos filtrados
            datos_exportar = self._obtener_datos_filtrados()
            if not datos_exportar:
                messagebox.showwarning("Sin datos", "No hay registros para exportar")
                return

            # 3. Configurar progreso
            total_registros = len(datos_exportar)
            self.global_progress.pack(side=tk.RIGHT, padx=10)
            self.global_progress['value'] = 0
            self.global_progress['maximum'] = total_registros
            self.api_status.config(text="Creando Excel: 0%", foreground="#004C97")

            filename = f"reporte_stock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            # Callback de progreso thread-safe
            def progress_cb(i, total):
                if i % max(1, total // 20) == 0 or i == total:
                    progreso = int((i / total) * 100)
                    # Usar after() para actualizar UI de forma segura desde otro hilo
                    self.root.after(0, lambda: self._update_export_progress(i, progreso, "Stock"))

            # Función para ejecutar la exportación en hilo separado
            def export_thread():
                try:
                    from pal.services.exports import export_stock_excel
                    
                    total_registros = export_stock_excel(
                        filename=filename,
                        datos_exportar=datos_exportar,
                        seleccionadas=seleccionadas,
                        location_groups=LOCATION_GROUPS,
                        db_manager=self.db_manager,
                        progress_cb=progress_cb,
                    )
                    
                    # Notificar éxito en el hilo principal
                    ubicaciones_info = f"🗺️ Ubicaciones: {len(seleccionadas)}\n🏢 Depósitos: {sum(len(LOCATION_GROUPS[u]) for u in seleccionadas)}\n\n"
                    self.root.after(0, lambda: self._export_success(
                        "Stock",
                        total_registros,
                        filename,
                        f"{ubicaciones_info}"
                        "Características:\n"
                        "• 3 hojas: Datos, Resumen, Críticos\n"
                        "• Tablas con filtros automáticos\n"
                        "• Formato condicional por niveles\n"
                        "• Columnas auto-ajustadas"
                    ))
                    try:
                        if hasattr(self, 'audit_db') and self.current_user:
                            self.audit_db.log_action(
                                accion='EXPORT', usuario_id=self.current_user['id'], modulo='STOCK', detalle=filename, exitoso=True)
                    except Exception:
                        pass
                    
                except Exception as e:
                    # Notificar error en el hilo principal
                    self.root.after(0, lambda err=str(e): self._export_error("Stock", err))
                    try:
                        if hasattr(self, 'audit_db') and self.current_user:
                            self.audit_db.log_action(
                                accion='EXPORT', usuario_id=self.current_user['id'], modulo='STOCK', detalle=str(e), exitoso=False)
                    except Exception:
                        pass
            
            # Iniciar exportación en hilo separado
            thread = threading.Thread(target=export_thread, daemon=True, name="ExportStock")
            thread.start()

        except Exception as e:
            self.log(f"Error iniciando exportación Excel: {str(e)}", "ERROR")
            self.api_status.config(text="API: Error", foreground="red")
            messagebox.showerror("Error en Exportación Excel", f"Error durante la exportación:\n{str(e)}")
            self._cleanup_export_progress()
    
    def _safe_update_api_status(self, text, color):
        """Actualiza el estado API de forma segura verificando que el widget exista"""
        try:
            if hasattr(self, 'api_status') and hasattr(self, 'root') and self.root.winfo_exists():
                self.api_status.config(text=text, foreground=color)
        except tk.TclError:
            pass  # Widget destruido, ignorar
                
            
            
    def _obtener_datos_filtrados(self):
        """Réplica de la lógica de filtrado SIN paginación"""
        # Aplicar mismos filtros que en aplicar_filtro_stock
        datos_filtrados = list(self.cached_alertas)
    
        # Filtro jerárquico
        dept_code = self.dept_dict.get(self.dept_var.get())
        group_code = self.group_dict.get(self.group_var.get())
        sub_code = self.sub_dict.get(self.sub_var.get())
    
        if any([dept_code, group_code, sub_code]):
            datos_filtrados = [
                r for r in datos_filtrados 
                if self._coincide_jerarquia(r[0], dept_code, group_code, sub_code)
            ]
    
        # Filtro texto
        texto_busqueda = self.search_var.get().strip().lower()
        if texto_busqueda:
            datos_filtrados = [
                r for r in datos_filtrados 
                if texto_busqueda in (r[1].lower() + r[0].lower())
            ]
    
        # Filtro nivel
        filtro_nivel = self.filter_var.get().upper()
        if filtro_nivel != 'TODAS':
            datos_filtrados = [r for r in datos_filtrados if r[3].upper() == filtro_nivel]
    
        # Ordenar por favoritos
        favoritos = self._get_favoritos_local()
        return sorted(datos_filtrados, key=lambda x: x[0] not in favoritos)
    
    # === Funciones auxiliares para exportación asíncrona ===
    
    def _update_export_progress(self, current, percentage, module_name):
        """Actualiza la barra de progreso y el estado durante la exportación (thread-safe)"""
        try:
            if hasattr(self, 'global_progress') and self.global_progress.winfo_exists():
                self.global_progress['value'] = current
            if hasattr(self, 'api_status'):
                self.api_status.config(text=f"Exportando {module_name}: {percentage}%", foreground="#004C97")
        except tk.TclError:
            pass  # Widget destruido, ignorar
    
    def _export_success(self, module_name, total_registros, filename, extra_info=""):
        """Muestra mensaje de éxito tras completar la exportación (thread-safe)"""
        try:
            self._cleanup_export_progress()
            self.api_status.config(text="API: Lista", foreground="green")
            
            messagebox.showinfo(
                f"Exportación {module_name} Exitosa",
                f"Reporte {module_name} generado con éxito:\n\n"
                f"• Registros: {total_registros}\n"
                f"{extra_info}\n\n"
                f"📁 Ruta: {os.path.abspath(filename)}"
            )
            
            # Restaurar estado después de 3 segundos
            self.root.after(3000, lambda: self._safe_update_api_status("API: Lista", "green"))
            
        except Exception as e:
            self.log(f"Error mostrando mensaje de éxito: {e}", "ERROR")
    
    def _export_error(self, module_name, error_msg):
        """Muestra mensaje de error tras fallar la exportación (thread-safe)"""
        try:
            self._cleanup_export_progress()
            self.api_status.config(text="API: Error", foreground="red")
            self.log(f"Error en exportación {module_name}: {error_msg}", "ERROR")
            
            messagebox.showerror(
                f"Error en Exportación {module_name}",
                f"Error durante la exportación:\n{error_msg}"
            )
            
            # Restaurar estado después de 3 segundos
            self.root.after(3000, lambda: self._safe_update_api_status("API: Lista", "green"))
            
        except Exception as e:
            self.log(f"Error mostrando mensaje de error: {e}", "ERROR")
    
    def _cleanup_export_progress(self):
        """Limpia la barra de progreso tras finalizar exportación (thread-safe)"""
        try:
            if hasattr(self, 'global_progress') and self.global_progress.winfo_exists():
                self.global_progress.pack_forget()
        except tk.TclError:
            pass  # Widget ya fue destruido

    def buscar_por_fecha(self):
        # Obtener fechas como objetos datetime.datetime (incluyendo hora)
        fecha_inicio = datetime.combine(self.fecha_inicio.get_date(), datetime.min.time())
        fecha_fin = datetime.combine(self.fecha_fin.get_date(), datetime.max.time())

        query = "SELECT * FROM pal_envios_programados WHERE fecha_programada BETWEEN ? AND ?"
        params = (fecha_inicio, fecha_fin)  # Ahora son datetime.datetime

        records = self.db_manager.fetch_data(query, params)
        self.tree.delete(*self.tree.get_children())
        for row in records:
            self.tree.insert("", tk.END, values=row)

    def cargar_eventos_calendario(self):
        """Carga en el calendario los envíos PENDIENTES desde la BD y resalta las fechas."""
        try:
            if not hasattr(self, 'cal'):
                return
            # Limpiar eventos anteriores del calendario
            try:
                for ev_id in self.cal.get_calevents():
                    self.cal.calevent_remove(ev_id)
            except Exception:
                pass

            # Asegurar conexión y consultar envíos pendientes
            if not self.db_manager.ensure_connection():
                return
            rows = self.db_manager.fetch_data(
                "SELECT id, numero_cliente, fecha_programada, tipo_envio, codigo_producto, estado "
                "FROM pal_envios_programados WHERE estado = 'PENDIENTE'"
            )

            # Mapear eventos por fecha (YYYY-MM-DD)
            self.eventos_por_fecha = {}
            for id_envio, numero, fecha_prog, tipo, codigo, estado in (rows or []):
                try:
                    key = fecha_prog.strftime('%Y-%m-%d')
                except Exception:
                    key = str(fecha_prog)[:10]
                self.eventos_por_fecha.setdefault(key, []).append({
                    'id': id_envio,
                    'numero': numero,
                    'fecha': fecha_prog,
                    'tipo': (tipo or ''),
                    'codigo': codigo,
                    'estado': estado,
                })

            # Resaltar fechas en el calendario
            for key, lst in self.eventos_por_fecha.items():
                try:
                    y, m, d = [int(x) for x in key.split('-')]
                    dt = datetime(y, m, d)
                    self.cal.calevent_create(dt, f"{len(lst)} pendiente(s)", 'pendiente')
                except Exception:
                    continue
            try:
                self.cal.tag_config('pendiente', background='#FFB81C', foreground='#004C97')
            except Exception:
                pass

            # Mostrar detalles del día seleccionado
            self.mostrar_eventos_fecha(None)
        except Exception as e:
            try:
                self.log(f"Error cargando eventos de calendario: {e}", "ERROR")
            except Exception:
                pass

    def mostrar_eventos_fecha(self, event):
        """Muestra en el panel de detalles los envíos del día seleccionado."""
        try:
            if not hasattr(self, 'eventos_text') or not hasattr(self, 'cal'):
                return 0
            fecha_sel = self.cal.get_date()  # 'YYYY-MM-DD' por date_pattern
            key = str(fecha_sel)

            self.eventos_text.delete('1.0', tk.END)
            eventos = (getattr(self, 'eventos_por_fecha', {}) or {}).get(key, [])
            if not eventos:
                self.eventos_text.insert(tk.END, "Sin envíos pendientes para esta fecha.")
                return 0

            # Ordenar por hora si es posible
            try:
                eventos_sorted = sorted(eventos, key=lambda e: e['fecha'])
            except Exception:
                eventos_sorted = eventos

            for e in eventos_sorted:
                try:
                    hora = e['fecha'].strftime('%H:%M')
                except Exception:
                    hora = ''
                linea = (
                    f"#{e['id']} | {hora} | {e['tipo']} | Cliente: {e['numero']} | "
                    f"Producto: {e['codigo'] or '-'} | Estado: {e['estado']}\n"
                )
                self.eventos_text.insert(tk.END, linea)
            return 0
        except Exception as e:
            try:
                self.log(f"Error mostrando eventos: {e}", "ERROR")
            except Exception:
                pass
            return 0

    def programar_actualizaciones_stock(self):
        def actualizar():
            while True:
                if hasattr(self, 'last_refresh'):  # <-- Verificar atributo
                    self.actualizar_alertas_stock()
                time.sleep(3600)  # <-- Actualizar cada hora
        threading.Thread(target=actualizar, daemon=True).start()
                        


    def setup_bindings(self):
        """Configurar eventos del teclado y widgets"""
        # Doble click en la tabla (solo si existe)
        if hasattr(self, 'tree'):
            self.tree.bind("<Double-1>", lambda e: self.on_tree_double_click(e) or 0)
        
        # Validación en tiempo real del código de producto (solo si existe)
        if hasattr(self, 'cod_producto'):
            self.cod_producto.bind("<KeyRelease>", lambda e: self.buscar_descripcion(e) or 0)
        
        # Atajo de teclado para consola de debug (Ctrl+Shift+D)
        self.root.bind_all("<Control-Shift-D>", lambda e: (self.debug_console.toggle() or 0))

    def setup_modern_ui(self):   
        self.root.title("Gestión de Clientes - Corporativo")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # create_header(self)  # Header eliminado para aprovechar espacio
        self.create_main_workspace()
        self.create_status_panel()

        style = ttk.Style()
        style.configure("TButton", background="#FFB81C", foreground="#004C97")
        style.map("TButton",
            background=[('active', '#e89f00')],
            foreground=[('active', '#003f7e')])
        

    def load_stock_filters(self):
        """Puebla Combobox tras conectar a BD usando descripciones como identificador visible"""
        try:
            deps = self.db_manager.fetch_data(
                "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_DEPARTAMENTOS"
            )
            self.dept_dict = {desc: cod for cod, desc in deps if cod and desc}
            self.dept_combo['values'] = ['Todos'] + list(self.dept_dict.keys())
            self.dept_var.set('Todos')
        except Exception as e:
            print("Error cargando departamentos:", e)
            self.dept_dict = {}
            self.dept_combo['values'] = ['Todos']
        self.dept_var.set('Todos')

        self.group_dict = {}
        self.group_combo['values'] = ['Todos']
        self.group_var.set('Todos')

        self.sub_dict = {}
        self.sub_combo['values'] = ['Todos']
        self.sub_var.set('Todos')
        
        # Cargar depósitos y preferencias
        try:
            self._load_stock_depositos_preference()
            self.load_depositos_stock()
            self._update_stock_depositos_label()
        except Exception as e:
            self.log(f"Error cargando depósitos: {e}", "DEBUG")
            self.stock_depositos_seleccionados = ['0301']

    def load_tra_filters(self):
        """Carga departamentos, grupos y subgrupos para la pestaña T.R.A"""
        try:
            # Departamentos
            deps = self.db_manager.fetch_data(
                "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_DEPARTAMENTOS"
            )
            self.tra_dept_dict = {desc: cod for cod, desc in deps if cod and desc}
            self.tra_dept_combo['values'] = ['Todos'] + list(self.tra_dept_dict.keys())
            self.tra_dept_var.set('Todos')
        except Exception as e:
            print("Error cargando departamentos del modulo tra:", e)

            # Inicializar grupos y subgrupos vacíos
            self.tra_group_dict = {}
            self.tra_group_combo['values'] = ['Todos']
            self.tra_group_var.set('Todos')

            self.tra_sub_dict = {}
            self.tra_sub_combo['values'] = ['Todos']
            self.tra_sub_var.set('Todos')

    def on_dept_selected(self):
        desc = self.dept_var.get()
        codigo = self.dept_dict.get(desc)
        if not codigo:
            self.group_combo['values'] = ['Todos']
            self.group_var.set('Todos')
            self.sub_combo['values'] = ['Todos']
            self.sub_var.set('Todos')
            self.aplicar_filtro_stock()
            return
        try:
            grupos = self.db_manager.fetch_data(
                "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_GRUPOS WHERE C_DEPARTAMENTO = ?",
                (codigo,)
            )
        except Exception as e:
            print("Error cargando grupos:", e)
            grupos = []
        self.group_dict = {desc: cod for cod, desc in grupos if cod and desc}
        self.group_combo['values'] = ['Todos'] + list(self.group_dict.keys())
        self.group_var.set('Todos')
        self.sub_combo['values'] = ['Todos']
        self.sub_var.set('Todos')
        self.aplicar_filtro_stock()

    def on_tra_dept_selected(self, event=None):
        """Actualiza grupos cuando se selecciona departamento"""
        dept = self.tra_dept_var.get() if hasattr(self, 'tra_dept_var') else None
        dept_cod = self.tra_dept_dict.get(dept) if dept else None
    
        # Resetear subgrupos
        if hasattr(self, 'tra_sub_combo'):
            self.tra_sub_combo['values'] = ['Todos']
            self.tra_sub_var.set('Todos')
    
        if dept_cod and hasattr(self, 'tra_group_combo'):
            grupos = list(self.tra_group_dict.get(dept_cod, {}).keys())
            self.tra_group_combo['values'] = ['Todos'] + grupos
        elif hasattr(self, 'tra_group_combo'):
            self.tra_group_combo['values'] = ['Todos']
    
        if hasattr(self, 'tra_group_var'):
            self.tra_group_var.set('Todos')
        
        # Resetear página actual y aplicar filtros
        self.tra_current_page = 1
        self.aplicar_filtro_tra()

    def on_group_selected(self):
        dept_desc = self.dept_var.get()
        grupo_desc = self.group_var.get()
        dept_codigo = self.dept_dict.get(dept_desc)
        grupo_codigo = self.group_dict.get(grupo_desc)
        if not (dept_codigo and grupo_codigo):
            self.sub_combo['values'] = ['Todos']
            self.sub_var.set('Todos')
            self.aplicar_filtro_stock()
            return
        try:
            subs = self.db_manager.fetch_data(
                "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_SUBGRUPOS WHERE C_IN_DEPARTAMENTO = ? AND C_IN_GRUPO = ?",
                (dept_codigo, grupo_codigo)
            )
        except Exception as e:
            print("Error cargando subgrupos:", e)
            subs = []
        self.sub_dict = {desc: cod for cod, desc in subs if cod and desc}
        self.sub_combo['values'] = ['Todos'] + list(self.sub_dict.keys())
        self.sub_var.set('Todos')
        def esperar_inicio():
            if self.db_manager.conn:
                self.aplicar_filtro_stock()
            else:
                self.root.after(100, esperar_inicio)

        esperar_inicio()

    def on_tra_group_selected(self, event=None):
        """Actualiza subgrupos cuando se selecciona grupo"""
        dept = self.tra_dept_var.get() if hasattr(self, 'tra_dept_var') else None
        group = self.tra_group_var.get() if hasattr(self, 'tra_group_var') else None
        dept_cod = self.tra_dept_dict.get(dept) if dept else None
        group_cod = self.tra_group_dict.get(dept_cod, {}).get(group) if dept_cod else None
    
        if hasattr(self, 'tra_sub_combo'):
            if dept_cod and group_cod:
                # Usar string como key (formato: "dept|group")
                key = f"{dept_cod}|{group_cod}"
                subgrupos = list(self.tra_sub_dict.get(key, {}).keys())
                self.tra_sub_combo['values'] = ['Todos'] + subgrupos
            else:
                self.tra_sub_combo['values'] = ['Todos']
    
        if hasattr(self, 'tra_sub_var'):
            self.tra_sub_var.set('Todos')
        
        # Resetear página actual y aplicar filtros
        self.tra_current_page = 1
        self.aplicar_filtro_tra()

        
        
    
    def cargar_jerarquia_productos(self):
        """Filtra la jerarquía usando solo los códigos actualmente en alerta."""
        start = time.perf_counter()
        try:
            if not hasattr(self, 'all_jerarquia') or not self.all_jerarquia:
                self.log("Jerarquía vacía, iniciando carga completa", "WARNING")
                self._cargar_toda_jerarquia_productos()

            # Normalizar códigos antes de filtrar
            def _s(x):
                try:
                    return str(x).strip()
                except Exception:
                    return ""
            codigos_en_alerta = {_s(r[0]) for r in self.cached_alertas}
            all_jerarquia_norm = {_s(k): v for k, v in (self.all_jerarquia or {}).items()}
            self.producto_jerarquia = {cod: all_jerarquia_norm[cod] for cod in codigos_en_alerta if cod in all_jerarquia_norm}
            elapsed = time.perf_counter() - start
            self.log(f"🔍 Filtrado de jerarquía: {len(self.producto_jerarquia)} en {elapsed:.2f}s", "DEBUG")
        except Exception as e:
            self.log(f"Error filtrando jerarquía: {e}", "ERROR")
            self.producto_jerarquia = {}

    def _cargar_toda_jerarquia_productos(self):
        """Carga el mapeo completo de productos a jerarquía con caché local."""
        start = time.perf_counter()
        try:
            if os.path.exists(JERARQUIA_CACHE_FILE):
                mtime = datetime.fromtimestamp(os.path.getmtime(JERARQUIA_CACHE_FILE))
                if datetime.now() - mtime < JERARQUIA_CACHE_TTL:
                    self.log("Cargando jerarquía desde cache", "INFO")
                    with open(JERARQUIA_CACHE_FILE, 'r', encoding='utf-8') as f:
                        self.all_jerarquia = json.load(f)
                    elapsed = time.perf_counter() - start
                    self.log(f"✅ Jerarquía leída en {elapsed:.2f}s (productos: {len(self.all_jerarquia)})", "DEBUG")
                    return
                else:
                    self.log("Cache vencido, recargando jerarquía desde BD", "INFO")
            else:
                self.log("Cache no existe, cargando jerarquía desde BD", "INFO")

            filas = self.db_manager.fetch_data(
                "SELECT C_CODIGO, C_DEPARTAMENTO, C_GRUPO, C_SUBGRUPO FROM MA_PRODUCTOS"
            )
            # Normalizar y cargar incluyendo productos con campos vacíos
            def _s(x):
                try:
                    s = str(x).strip()
                    return s if s and s.lower() != 'none' else ""
                except Exception:
                    return ""
            self.all_jerarquia = {}
            for fila in filas or []:
                try:
                    if not fila:
                        continue
                    cod = _s(fila[0])
                    if not cod:
                        continue
                    dep = _s(fila[1]) if len(fila) > 1 else ""
                    grp = _s(fila[2]) if len(fila) > 2 else ""
                    sub = _s(fila[3]) if len(fila) > 3 else ""
                    self.all_jerarquia[cod] = (dep, grp, sub)
                except Exception:
                    continue
            with open(JERARQUIA_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.all_jerarquia, f, ensure_ascii=False)
            elapsed = time.perf_counter() - start
            self.log(f"✅ Jerarquía cargada y cacheada ({len(self.all_jerarquia)} productos) en {elapsed:.2f}s", "SUCCESS")

        except Exception as e:
            self.log(f"Error cargando jerarquía: {e}", "ERROR")
            self.all_jerarquia = {}

    def _init_jerarquia_async(self):
        """Thread en background para cargar y filtrar jerarquía sin bloquear UI."""
        total_start = time.perf_counter()
        try:
            from pal.services.stock import load_all_jerarquia, build_producto_jerarquia
            # Cargar jerarquía (con caché)
            all_jerarquia = load_all_jerarquia(
                self.db_manager,
                JERARQUIA_CACHE_FILE,
                int(JERARQUIA_CACHE_TTL.total_seconds())
            )
            self.all_jerarquia = all_jerarquia or {}
            # Filtrar sólo códigos en alerta
            codigos_en_alerta = {r[0] for r in getattr(self, 'cached_alertas', [])}
            self.producto_jerarquia = build_producto_jerarquia(self.all_jerarquia, codigos_en_alerta)
        except Exception as e:
            self.log(f"Error inicializando jerarquía: {e}", "ERROR")
            self.producto_jerarquia = {}
        elapsed = time.perf_counter() - total_start
        self.log(f"🏁 Jerarquía inicializada en {elapsed:.2f}s", "INFO")
        # Actualizar UI en hilo principal
        try:
            self.root.after(0, self.aplicar_filtro_stock)
        except Exception:
            pass

    def aplicar_filtro_stock(self):
        # Asegurar datos base
        if not hasattr(self, 'cached_alertas') or not self.cached_alertas:
            self.actualizar_alertas_stock(force_refresh=True)
        
        # Verificar y manejar jerarquía de productos
        if not hasattr(self, 'producto_jerarquia'):
            self.producto_jerarquia = {}
        
        # DEBUG: Verificar estado de jerarquía
        jerarquia_count = len(self.producto_jerarquia)
        alertas_count = len(self.cached_alertas)
        self.stock_debug_log(f"Filtro Stock - Jerarquía: {jerarquia_count} productos, Alertas: {alertas_count}")
        
        # Filtros actuales (robustos aunque aún no se hayan cargado dicts)
        dept_dict = getattr(self, 'dept_dict', {}) or {}
        group_dict = getattr(self, 'group_dict', {}) or {}
        sub_dict = getattr(self, 'sub_dict', {}) or {}
        dept_val = self.dept_var.get() if hasattr(self, 'dept_var') else None
        group_val = self.group_var.get() if hasattr(self, 'group_var') else None
        sub_val = self.sub_var.get() if hasattr(self, 'sub_var') else None
        dept_code = dept_dict.get(dept_val)
        group_code = group_dict.get(group_val)
        sub_code = sub_dict.get(sub_val)
        texto_busqueda = (self.search_var.get() if hasattr(self, 'search_var') else '' ).strip()
        filtro_nivel = (self.filter_var.get() if hasattr(self, 'filter_var') else 'TODAS').upper()
        favoritos = self._get_favoritos_local()
        
        # DEBUG: Log de filtros aplicados
        filtros_activos = []
        if dept_code:
            filtros_activos.append(f"Dept: {self.dept_var.get()}")
        if group_code:
            filtros_activos.append(f"Group: {self.group_var.get()}")
        if sub_code:
            filtros_activos.append(f"Sub: {self.sub_var.get()}")
        if texto_busqueda:
            filtros_activos.append(f"Texto: {texto_busqueda}")
        if filtro_nivel != 'TODAS':
            filtros_activos.append(f"Nivel: {filtro_nivel}")
        
        self.stock_debug_log(f"Filtros activos: {', '.join(filtros_activos) if filtros_activos else 'Ninguno'}")
        
        # Si hay filtros jerárquicos pero no hay jerarquía, intentar cargarla
        if any([dept_code, group_code, sub_code]) and jerarquia_count == 0:
            self.stock_debug_log("Detectados filtros jerárquicos pero jerarquía vacía - intentando recargar")
            try:
                # Intentar cargar jerarquía de productos de forma síncrona rápida
                from pal.services.stock import load_all_jerarquia, build_producto_jerarquia
                if hasattr(self, 'all_jerarquia') and self.all_jerarquia:
                    # Si tenemos all_jerarquia, crear producto_jerarquia filtrado
                    # Normalizar códigos antes de construir
                    codigos_en_alerta = {str(r[0]).strip() for r in self.cached_alertas}
                    self.producto_jerarquia = build_producto_jerarquia(self.all_jerarquia, codigos_en_alerta)
                    self.stock_debug_log(f"Jerarquía reconstruida desde all_jerarquia: {len(self.producto_jerarquia)} productos")
                else:
                    # Cargar desde BD de forma rápida (solo para filtro actual)
                    self.log("⚠️ Jerarquía vacía detectada - cargando para filtros", "WARNING")
                    threading.Thread(target=self._init_jerarquia_async, daemon=True).start()
            except Exception as e:
                self.stock_debug_log(f"Error intentando recargar jerarquía: {e}")

        from pal.services.stock import filter_alertas, paginate
        # Filtrar y ordenar
        filtrados = filter_alertas(
            alertas=self.cached_alertas,
            producto_jerarquia=self.producto_jerarquia,
            dept_code=dept_code,
            group_code=group_code,
            sub_code=sub_code,
            search_text=texto_busqueda,
            filter_level=filtro_nivel,
            favoritos=favoritos,
        )
        # Diagnóstico: distribución tras aplicar filtro seleccionado (solo en modo debug)
        # Comentado para reducir spam en logs
        # try:
        #     leves = medias = criticas = 0
        #     for _, _, stock_val, _ in filtrados:
        #         try:
        #             s = int(stock_val or 0)
        #         except Exception:
        #             s = 0
        #         if s >= 15:
        #             leves += 1
        #         elif s >= 8:
        #             medias += 1
        #         else:
        #             criticas += 1
        #     self.log(
        #         f"Filtro='{filtro_nivel}', total filtradas={len(filtrados)} | Leves:{leves} Medias:{medias} Críticas:{criticas}",
        #         "DEBUG"
        #     )
        # except Exception:
        #     pass
        # Sanitizar filas con longitud incorrecta y tipos esperados
        filtrados_clean = []
        for r in filtrados:
            try:
                codigo = str(r[0])
                desc = str(r[1])
                stock_val = int(r[2]) if r[2] is not None else 0
                nivel_val = str(r[3]) if len(r) > 3 else ''
                filtrados_clean.append((codigo, desc, stock_val, nivel_val))
            except Exception:
                continue
        # Paginación
        datos_pagina, total_paginas, self.current_page = paginate(
            filtrados_clean, self.current_page, self.page_size
        )
        # DEBUG: Log de resultados finales
        self.stock_debug_log(
            f"Resultado filtrado: {len(filtrados_clean)} productos | "
            f"Página {self.current_page}/{total_paginas} | "
            f"Mostrando: {len(datos_pagina)} productos"
        )
        
        # Actualizar UI
        self.mostrar_alertas_paginadas(datos_pagina)
        self.actualizar_controles_paginacion(total_paginas)

    def _coincide_jerarquia(self, codigo, dept_code, group_code, sub_code):
        """Helper function para filtro jerárquico optimizado"""
        jerarquia = self.producto_jerarquia.get(codigo)
        if not jerarquia:
            return False
    
        dep, grp, sub = jerarquia
        return  (not dept_code or dep == dept_code) and \
                (not group_code or grp == group_code) and \
                (not sub_code or sub == sub_code)
    
    def _coincide_jerarquia_tra(self, codigo, tra_dept_code, tra_group_code, tra_sub_code):
        """Helper function para filtro jerárquico optimizado"""
        jerarquia = self.producto_jerarquia.get(codigo)
        if not jerarquia:
            return False
    
        dep, grp, sub = jerarquia
        return  (not tra_dept_code or dep == tra_dept_code) and \
                (not tra_group_code or grp == tra_group_code) and \
                (not tra_sub_code or sub == tra_sub_code)
        
    def actualizar_controles_paginacion(self, total_paginas):
        """Actualiza los controles de paginación"""
        self.pagination_label.config(text=f"Página {self.current_page}/{total_paginas}")
        self.btn_prev['state'] = 'normal' if self.current_page > 1 else 'disabled'
        self.btn_next['state'] = 'normal' if self.current_page < total_paginas else 'disabled'    
    
    def load_depositos_stock(self):
        """Carga lista de depósitos desde la base de datos"""
        try:
            depositos = self.db_manager.obtener_depositos()
            if not depositos:
                self.log("No se encontraron depósitos en la BD", "WARNING")
                return
            
            # Agrupar por localidad según prefijo
            localidades = {}
            for cod, desc in depositos:
                cod = str(cod).strip()
                desc = str(desc).strip()
                
                # Determinar localidad por prefijo
                if cod.startswith('03'):
                    localidad = 'Cabudare'
                elif cod.startswith('01'):
                    localidad = 'Barinas'
                elif cod.startswith('04'):
                    localidad = 'Guanare'
                else:
                    localidad = 'Otra'
                
                if localidad not in localidades:
                    localidades[localidad] = []
                localidades[localidad].append({'codigo': cod, 'descripcion': desc})
            
            # Guardar en atributos
            self.stock_localidades = localidades
            self.stock_depositos_por_codigo = {cod: desc for cod, desc in depositos}
            
            # Inicializar seleccionados (default a Cabudare)
            if not hasattr(self, 'stock_depositos_seleccionados'):
                self.stock_depositos_seleccionados = [d['codigo'] for d in localidades.get('Cabudare', [])]
            
            # Actualizar label de depósitos
            self._update_stock_depositos_label()
            
            self.log(f"✅ Depósitos cargados: {len(depositos)} depósitos en {len(localidades)} localidades", "SUCCESS")
            
        except Exception as e:
            self.log(f"Error cargando depósitos: {e}", "ERROR")
    
    def _update_stock_depositos_label(self):
        """Actualiza el label con los depósitos seleccionados"""
        try:
            if not hasattr(self, 'stock_depositos_seleccionados'):
                self.stock_depositos_seleccionados = ['0301']
            
            if hasattr(self, 'stock_depositos_label'):
                # Crear texto descriptivo
                descs = [self.stock_depositos_por_codigo.get(cod, cod) 
                        for cod in sorted(self.stock_depositos_seleccionados)]
                texto = ', '.join(descs) if descs else '[Sin seleccionar]'
                self.stock_depositos_label.config(text=f"📦 {texto}")
        except Exception as e:
            self.log(f"Error actualizando label de depósitos: {e}", "DEBUG")
    
    def abrir_menu_depositos_stock(self):
        """Abre diálogo para configurar localidad y depósitos"""
        try:
            import tkinter as tk
            from tkinter import ttk
            
            if not hasattr(self, 'stock_localidades'):
                self.log("Cargando depósitos...", "INFO")
                return
            
            # Crear ventana emergente
            ventana = tk.Toplevel(self.root)
            ventana.title("Configurar Localidad y Depósitos")
            ventana.geometry("600x450")
            ventana.resizable(False, False)
            ventana.grab_set()
            
            # Frame de selección de localidad
            frame_localidad_sel = ttk.LabelFrame(ventana, text="1. Seleccionar Localidad", padding=10)
            frame_localidad_sel.pack(fill=tk.X, padx=10, pady=10)
            
            localidad_var = tk.StringVar()
            
            def on_localidad_selected(event=None):
                """Handler cuando se selecciona una localidad"""
                localidad_sel = localidad_var.get()
                # Limpiar y actualizar checkboxes de depósitos
                for widget in frame_depositos_inner.winfo_children():
                    widget.destroy()
                
                if localidad_sel and localidad_sel in self.stock_localidades:
                    for deposito in self.stock_localidades[localidad_sel]:
                        cod = deposito['codigo']
                        desc = deposito['descripcion']
                        var = tk.BooleanVar(value=cod in self.stock_depositos_seleccionados)
                        vars_depositos[cod] = var
                        ttk.Checkbutton(
                            frame_depositos_inner,
                            text=f"{cod} - {desc}",
                            variable=var
                        ).pack(anchor=tk.W, padx=10, pady=3)
            
            # Combobox de localidades
            ttk.Label(frame_localidad_sel, text="Localidad:").pack(side=tk.LEFT, padx=5)
            combo_localidad = ttk.Combobox(
                frame_localidad_sel,
                textvariable=localidad_var,
                values=sorted(self.stock_localidades.keys()),
                state='readonly',
                width=30
            )
            combo_localidad.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            combo_localidad.bind('<<ComboboxSelected>>', on_localidad_selected)
            
            # Obtener localidad actual del primer depósito seleccionado
            localidad_actual = None
            if hasattr(self, 'stock_depositos_seleccionados') and self.stock_depositos_seleccionados:
                for loc, deps in self.stock_localidades.items():
                    for dep in deps:
                        if dep['codigo'] == self.stock_depositos_seleccionados[0]:
                            localidad_actual = loc
                            break
                    if localidad_actual:
                        break
            
            if localidad_actual:
                localidad_var.set(localidad_actual)
            
            # Frame de selección de depósitos
            frame_depositos_label = ttk.LabelFrame(ventana, text="2. Seleccionar Depósitos", padding=10)
            frame_depositos_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Canvas con scrollbar para los depósitos
            canvas = tk.Canvas(frame_depositos_label)
            scrollbar = ttk.Scrollbar(frame_depositos_label, orient="vertical", command=canvas.yview)
            frame_depositos_inner = ttk.Frame(canvas)
            
            frame_depositos_inner.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=frame_depositos_inner, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            vars_depositos = {}
            
            # Mostrar depósitos de la localidad seleccionada
            if localidad_actual:
                on_localidad_selected()
            
            # Frame de botones
            frame_botones = ttk.Frame(ventana)
            frame_botones.pack(fill=tk.X, padx=10, pady=10)
            
            def guardar_seleccion():
                """Guarda la selección de localidad y depósitos"""
                localidad_sel = localidad_var.get()
                if not localidad_sel:
                    self.log("Debe seleccionar una localidad", "WARNING")
                    return
                
                seleccionados = [cod for cod, var in vars_depositos.items() if var.get()]
                
                if not seleccionados:
                    self.log("Debe seleccionar al menos un depósito", "WARNING")
                    return
                
                # Guardar localidad actual
                self.stock_localidad_actual = localidad_sel
                self.stock_depositos_seleccionados = seleccionados
                self._update_stock_depositos_label()
                
                # Guardar preferencia
                self._save_stock_depositos_preference()
                
                # Recargar datos
                self.current_page = 1
                self.recargar_stock()
                
                ventana.destroy()
                self.log(f"✅ Localidad: {localidad_sel} | Depósitos: {', '.join(seleccionados)}", "SUCCESS")
            
            ttk.Button(frame_botones, text="✅ Guardar", command=guardar_seleccion).pack(side=tk.LEFT, padx=5)
            ttk.Button(frame_botones, text="❌ Cancelar", command=ventana.destroy).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            self.log(f"Error abriendo menú de depósitos: {e}", "ERROR")
    
    def _save_stock_depositos_preference(self):
        """Guarda preferencia de localidad y depósitos seleccionados en archivo local"""
        try:
            import json
            pref_file = "stock_depositos_preference.json"
            pref_data = {
                'localidad': getattr(self, 'stock_localidad_actual', 'Cabudare'),
                'depositos': self.stock_depositos_seleccionados,
                'timestamp': str(time.time())
            }
            with open(pref_file, 'w', encoding='utf-8') as f:
                json.dump(pref_data, f, ensure_ascii=False)
            self.log(f"💾 Preferencia guardada", "DEBUG")
        except Exception as e:
            self.log(f"Error guardando preferencia de depósitos: {e}", "DEBUG")
    
    def _load_stock_depositos_preference(self):
        """Carga preferencia de localidad y depósitos guardada"""
        try:
            import json
            import os
            pref_file = "stock_depositos_preference.json"
            if os.path.exists(pref_file):
                with open(pref_file, 'r', encoding='utf-8') as f:
                    pref_data = json.load(f)
                    self.stock_localidad_actual = pref_data.get('localidad', 'Cabudare')
                    self.stock_depositos_seleccionados = pref_data.get('depositos', ['0301'])
                    self.log(f"📂 Preferencia cargada - Localidad: {self.stock_localidad_actual}", "DEBUG")
            else:
                self.stock_localidad_actual = 'Cabudare'
                self.stock_depositos_seleccionados = ['0301']
        except Exception as e:
            self.log(f"Error cargando preferencia: {e}", "DEBUG")
            self.stock_localidad_actual = 'Cabudare'
            self.stock_depositos_seleccionados = ['0301']
    
    def on_deposito_stock_selected(self):
        """Handler cuando cambian los depósitos seleccionados"""
        try:
            self.current_page = 1
            self.recargar_stock()
        except Exception as e:
            self.log(f"Error en cambio de depósito: {e}", "ERROR")

    def hover_row(self, event):
        item = self.stock_tree.identify_row(event.y)
        if item:  # Solo añadir tag si se identificó un item
            try:
                self.stock_tree.tk.call(self.stock_tree, 'tag', 'add', 'hover', item)
            except Exception as e:
                print(f"Error en hover_row: {str(e)}")
        return 0  # Valor entero apropiado para WNDPROC en Windows

    def leave_row(self, event):
        item = self.stock_tree.identify_row(event.y)
        if item:  # Solo remover tag si se identificó un item
            try:
                self.stock_tree.tk.call(self.stock_tree, 'tag', 'remove', 'hover', item)
            except Exception as e:
                print(f"Error en leave_row: {str(e)}")
        return 0  # Valor entero apropiado para WNDPROC en Windows

    def select_row(self, event):
        selected_items = self.stock_tree.selection()
        if not selected_items:  # Verificar si hay selección
            return 0  # Valor entero apropiado para WNDPROC en Windows
        item = selected_items[0]
        try:
            # Limpiar tags previos
            self.stock_tree.tk.call(self.stock_tree, 'tag', 'remove', 'selected', '')
            # Aplicar tag a nuevo item seleccionado
            self.stock_tree.tk.call(self.stock_tree, 'tag', 'add', 'selected', item)
        except Exception as e:
            print(f"Error en select_row: {str(e)}")
        return 0  # Valor entero apropiado para WNDPROC en Windows

    

    def on_favorito_click(self, event):
        """Manejar clic en la columna de favoritos usando cache local"""
        try:
            region = self.stock_tree.identify_region(event.x, event.y)
            if region == "cell":
                col = self.stock_tree.identify_column(event.x)
                item = self.stock_tree.identify_row(event.y)
                if item and col == "#1":
                    values = self.stock_tree.item(item, 'values')
                    if values and len(values) > 1:
                        codigo = values[1]
                        if self._toggle_favorito_local(codigo):
                            self.aplicar_filtro_stock()
        except Exception as e:
            print(f"Error en on_favorito_click: {e}")
        return 0
        

    def mostrar_alertas_paginadas(self, datos):
        """Mostrar datos con estado de favoritos y filas alternadas"""
        self.stock_tree.delete(*self.stock_tree.get_children())
        favoritos = self._get_favoritos_local()
        
        for idx, (codigo, desc, stock, nivel) in enumerate(datos):
            es_favorito = codigo in favoritos
            estado = "✓" if es_favorito else "☐"
            
            # Si es favorito, usar estilo de favorito
            if es_favorito:
                tags = ('favorito',)
            else:
                # Usar estilo alternado basado en el índice
                nivel_base = nivel.lower().replace('ítica', 'itica')
                if idx % 2 == 0:
                    tags = (nivel_base,)  # Filas pares: colores claros
                else:
                    tags = (f"{nivel_base}_alt",)  # Filas impares: colores oscuros
            
            self.stock_tree.insert("", tk.END, 
                                values=(estado, codigo, desc, stock, nivel),
                                tags=tags)
        
    def aplicar_filtro(self):
        self.current_filter = self.filter_var.get()
        self.current_page = 1
        # Limpiar selección antes de actualizar
        self.stock_tree.selection_remove(self.stock_tree.selection())
        self.actualizar_alertas_stock()

    def cambiar_pagina(self, delta):
        self.current_page += delta
        self.aplicar_filtro_stock()
        



    def create_main_workspace(self):

        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        # Pestaña de Dashboard (Pantalla Principal) - siempre visible
        self.dashboard_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.dashboard_tab, text="🏠 Inicio")
        from pal.ui.tabs.dashboard import setup_dashboard_tab
        setup_dashboard_tab(self)
        
        # Pestaña de Registros (solo si el módulo de mensajes está activo)
        if self.modules_enabled.get("envio_mensajes", False):
            self.records_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.records_tab, text="Registros")
            from pal.ui.tabs.records import setup_records_tab as setup_records_tab_ui
            setup_records_tab_ui(self)


        # Pestaña de Mensajería
        if self.modules_enabled.get("envio_mensajes", False):
            self.messaging_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.messaging_tab, text="Mensajería")
            from pal.ui.tabs.messaging import setup_messaging_tab as setup_messaging_tab_ui
            setup_messaging_tab_ui(self)

        # Pestaña de Estadísticas
        if self.modules_enabled.get("estadisticas", False):
            self.stats_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.stats_tab, text="📊 Estadísticas")
            from pal.ui.tabs.stats import setup_stats_tab as setup_stats_tab_ui
            setup_stats_tab_ui(self)  

        # Pestaña de Calendario
        if self.modules_enabled.get("calendario", False):
            self.calendar_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.calendar_tab, text="📅 Calendario")
            from pal.ui.tabs.calendar import setup_calendar_tab as setup_calendar_tab_ui
            setup_calendar_tab_ui(self)

        # Pestaña T.R.A (Rotación de Ventas)
        if self.modules_enabled.get("tra", False):
            self.tra_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.tra_tab, text="📈 T.R.A")
            from pal.ui.tabs.tra import setup_tra_tab as setup_tra_tab_ui
            setup_tra_tab_ui(self)
            self.root.after(500, self._update_hierarchy_combos)
        # Pe staña MBRP (Movimiento de Baja Rotación)
        if self.modules_enabled.get("mbrp", False):
            self.mbrp_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.mbrp_tab, text="📉 MBRP")
            from pal.ui.tabs.mbrp import setup_mbrp_tab as setup_mbrp_tab_ui
            setup_mbrp_tab_ui(self)
            # Actualizar combos MBRP inmediatamente si ya hay datos cargados
            if hasattr(self, 'mbrp_dept_dict') and self.mbrp_dept_dict:
                self.mbrp_dept_combo['values'] = ['Todos'] + list(self.mbrp_dept_dict.keys())
                self.mbrp_dept_var.set('Todos')
            # Programar actualización adicional en caso de que se carguen después
            self.root.after(500, self._update_hierarchy_combos)
            self.root.after(500, self._update_hierarchy_combos)

        # Alerta de stock Supervisores
        if self.modules_enabled.get("stock", False):
            self.stock_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.stock_tab, text="🚨 Alertas Stock")
            from pal.ui.tabs.stock import setup_stock_tab as setup_stock_tab_ui
            setup_stock_tab_ui(self)
        
        # Pestaña de Administración (solo si ADMIN habilitado)
        if self.modules_enabled.get("admin", False):
            self.admin_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.admin_tab, text="🔓 Administración")

            admin_nb = ttk.Notebook(self.admin_tab)
            admin_nb.pack(fill=tk.BOTH, expand=True)

            # Tab: Usuarios (visible si permiso admin.usuarios o admin)
            show_users = False
            try:
                if hasattr(self, 'permissions') and self.current_user:
                    show_users = self.permissions.tiene_permiso(self.current_user['id'], 'ADMIN', 'usuarios')
                if self.current_user and self.current_user.get('username', '').lower() == 'admin':
                    show_users = True
            except Exception:
                show_users = self.current_user and self.current_user.get('username', '').lower() == 'admin'

            if show_users:
                admin_users_frame = ttk.Frame(admin_nb)
                admin_nb.add(admin_users_frame, text="Usuarios")
                self._create_admin_users_tab(admin_users_frame)

            # Tab: Roles y Permisos (visible si admin o tiene permiso admin.roles)
            show_roles = False
            try:
                if hasattr(self, 'permissions') and self.current_user:
                    show_roles = (
                        self.current_user.get('username', '').lower() == 'admin' or
                        self.permissions.tiene_permiso(self.current_user['id'], 'ADMIN', 'roles')
                    )
            except Exception:
                show_roles = self.current_user and self.current_user.get('username', '').lower() == 'admin'

            if show_roles:
                roles_frame = ttk.Frame(admin_nb)
                admin_nb.add(roles_frame, text="Roles y Permisos")
                self._create_roles_permissions_tab(roles_frame)

            # Tab: Auditoría (visible si admin o permiso admin.auditoria)
            show_audit = False
            try:
                if hasattr(self, 'permissions') and self.current_user:
                    show_audit = (
                        self.current_user.get('username', '').lower() == 'admin' or
                        self.permissions.tiene_permiso(self.current_user['id'], 'ADMIN', 'auditoria')
                    )
            except Exception:
                show_audit = self.current_user and self.current_user.get('username', '').lower() == 'admin'

            if show_audit:
                audit_frame = ttk.Frame(admin_nb)
                admin_nb.add(audit_frame, text="Auditoría")
                self._create_audit_tab(audit_frame)
    
    def mostrar_tra_filtrado(self, datos_filtrados):
        """Muestra datos filtrados TRA en el Treeview con colores, stock actual e ideal, y días restantes"""
        self.tra_tree.delete(*self.tra_tree.get_children())
        
        # Actualizar variable para paginación
        self.tra_ventas_datos_filtrados = datos_filtrados
        
        # Solo mostrar una página de datos
        items_por_pagina = min(self.tra_page_size, len(datos_filtrados))
        page_rows = datos_filtrados[:items_por_pagina]
        codigos = [r[0] for r in page_rows]
        sede = (self.sede_var.get() or '').split(' - ')[0]
        stock_map = self.obtener_stock_actual_bulk(codigos, sede)
        fecha_inicio = self.fecha_inicio_entry.get_date()
        fecha_fin = self.fecha_fin_entry.get_date()
        
        for fila in page_rows:
            codigo, desc, _, _, _, neto, rotacion = fila
            stock_actual = int(stock_map.get(codigo, 0) or 0)
            
            # Calcular stock ideal y días restantes
            stock_ideal = self.calcular_stock_ideal_producto(neto)
            dias_restantes = self.calcular_dias_restantes(stock_actual, neto, fecha_inicio, fecha_fin)
            
            # Determinar tag de color según rotación
            tag_rotacion = rotacion.lower()
            
            # Verificar si producto tiene alerta de stock y es de rotación ALTA o MEDIA
            alerta_stock = self._check_product_stock_alert(codigo)
            es_rotacion_critica = rotacion.upper() in ['ALTA', 'MEDIA']
            tiene_alerta_critica = alerta_stock and es_rotacion_critica
            
            # Si tiene alerta crítica (alta/media rotación + stock bajo), agregar indicador
            desc_mostrada = desc
            tags_mostrados = (tag_rotacion,)
            if tiene_alerta_critica:
                # Agregar indicador visual prominente al inicio de la descripción
                desc_mostrada = f"🔴 {desc}"
                # Agregar tag de alerta además del tag de rotación
                tags_mostrados = (tag_rotacion, 'stock_alert')
            
            self.tra_tree.insert(
                "", tk.END,
                values=(codigo, desc_mostrada, rotacion, int(neto), stock_actual, stock_ideal, dias_restantes),
                tags=tags_mostrados
            )
    
    def cambiar_pagina_tra(self, delta):
        """Cambia de página en el módulo TRA"""
        self.tra_current_page += delta
        self.aplicar_filtro_tra()  # Esto recalculará la paginación y mostrará los datos
    
    def mostrar_pagina_tra(self):
        """Muestra la página actual de resultados"""
        if not hasattr(self, 'tra_ventas_datos_filtrados'):
            return
    
        total_items = len(self.tra_ventas_datos_filtrados)
        total_pages = max(1, (total_items + self.tra_page_size - 1) // self.tra_page_size)
    
        # Asegurar página válida
        self.tra_current_page = max(1, min(self.tra_current_page, total_pages))
    
        # Calcular rango de items a mostrar
        start_idx = (self.tra_current_page - 1) * self.tra_page_size
        end_idx = min(start_idx + self.tra_page_size, total_items)
        page_data = self.tra_ventas_datos_filtrados[start_idx:end_idx]
    
        # Actualizar Treeview con colores, stock actual, stock ideal y días restantes
        self.tra_tree.delete(*self.tra_tree.get_children())
        codigos = [r[0] for r in page_data]
        sede = (self.sede_var.get() or '').split(' - ')[0]
        stock_map = self.obtener_stock_actual_bulk(codigos, sede)
        fecha_inicio = self.fecha_inicio_entry.get_date()
        fecha_fin = self.fecha_fin_entry.get_date()
        for fila in page_data:
            codigo, desc, _, _, _, neto, rotacion = fila
            stock_actual = int(stock_map.get(codigo, 0) or 0)
            stock_ideal = self.calcular_stock_ideal_producto(neto)
            dias_restantes = self.calcular_dias_restantes(stock_actual, neto, fecha_inicio, fecha_fin)
            tag_rotacion = rotacion.lower()
            # Formatear neto: si es entero, mostrar sin decimales
            neto_valor = float(neto or 0)
            neto_formateado = int(neto_valor) if neto_valor == int(neto_valor) else round(neto_valor, 2)
            
            # Verificar si producto tiene alerta de stock y es de rotación ALTA o MEDIA
            alerta_stock = self._check_product_stock_alert(codigo)
            es_rotacion_critica = rotacion.upper() in ['ALTA', 'MEDIA']
            tiene_alerta_critica = alerta_stock and es_rotacion_critica
            
            # Si tiene alerta crítica (alta/media rotación + stock bajo), agregar indicador
            desc_mostrada = desc
            tags_mostrados = (tag_rotacion,)
            if tiene_alerta_critica:
                # Agregar indicador visual prominente al inicio de la descripción
                desc_mostrada = f"🔴 {desc}"
                # Agregar tag de alerta además del tag de rotación
                tags_mostrados = (tag_rotacion, 'stock_alert')
            
            self.tra_tree.insert(
                "", "end", 
                values=(codigo, desc_mostrada, rotacion, neto_formateado, stock_actual, stock_ideal, dias_restantes),
                tags=tags_mostrados
            )
    
        # Actualizar controles
        self.tra_pagina_label.config(text=f"Página {self.tra_current_page}/{total_pages}")
        self.tra_btn_prev['state'] = 'normal' if self.tra_current_page > 1 else 'disabled'
        self.tra_btn_next['state'] = 'normal' if self.tra_current_page < total_pages else 'disabled'
        
    def tra_debug_log(self, message: str, level: str = "DEBUG", throttle_key: str = None, throttle_seconds: float = 2.0):
        """Log DEBUG inteligente para módulo TRA con throttling para evitar spam.
        
        Args:
            message: Mensaje a loggear
            level: Nivel del log (DEBUG, INFO, etc.)
            throttle_key: Clave para agrupar mensajes similares (ej: "chunk_load")
            throttle_seconds: Segundos mínimos entre logs del mismo throttle_key
        """
        if not getattr(self, 'tra_debug', False):
            return
            
        try:
            # Inicializar throttle cache si no existe
            if not hasattr(self, '_tra_debug_throttle'):
                self._tra_debug_throttle = {}
            
            current_time = time.time()
            
            # Si hay throttle_key, verificar si debemos loggear
            if throttle_key:
                last_time = self._tra_debug_throttle.get(throttle_key, 0)
                if current_time - last_time < throttle_seconds:
                    return  # Suprimir este log por throttling
                self._tra_debug_throttle[throttle_key] = current_time
            
            self.log(f"[TRA DEBUG] {message}", level)
        except Exception:
            pass

    def stock_debug_log(self, message: str, level: str = "DEBUG", throttle_key: str = None, throttle_seconds: float = 2.0):
        """Log DEBUG inteligente para módulo Stock con throttling para evitar spam.
        
        Args:
            message: Mensaje a loggear
            level: Nivel del log (DEBUG, INFO, etc.)
            throttle_key: Clave para agrupar mensajes similares
            throttle_seconds: Segundos mínimos entre logs del mismo throttle_key
        """
        if not getattr(self, 'stock_debug', False):
            return
            
        try:
            # Inicializar throttle cache si no existe
            if not hasattr(self, '_stock_debug_throttle'):
                self._stock_debug_throttle = {}
            
            current_time = time.time()
            
            # Si hay throttle_key, verificar si debemos loggear
            if throttle_key:
                last_time = self._stock_debug_throttle.get(throttle_key, 0)
                if current_time - last_time < throttle_seconds:
                    return  # Suprimir este log por throttling
                self._stock_debug_throttle[throttle_key] = current_time
            
            self.log(f"[STOCK DEBUG] {message}", level)
        except Exception:
            pass

    def mbrp_debug_log(self, message: str, level: str = "DEBUG", throttle_key: str = None, throttle_seconds: float = 2.0):
        """Log DEBUG inteligente para módulo MBRP con throttling para evitar spam.
        
        Args:
            message: Mensaje a loggear
            level: Nivel del log (DEBUG, INFO, etc.)
            throttle_key: Clave para agrupar mensajes similares
            throttle_seconds: Segundos mínimos entre logs del mismo throttle_key
        """
        if not getattr(self, 'mbrp_debug', False):
            return
            
        try:
            # Inicializar throttle cache si no existe
            if not hasattr(self, '_mbrp_debug_throttle'):
                self._mbrp_debug_throttle = {}
            
            current_time = time.time()
            
            # Si hay throttle_key, verificar si debemos loggear
            if throttle_key:
                last_time = self._mbrp_debug_throttle.get(throttle_key, 0)
                if current_time - last_time < throttle_seconds:
                    return  # Suprimir este log por throttling
                self._mbrp_debug_throttle[throttle_key] = current_time
            
            self.log(f"[MBRP DEBUG] {message}", level)
        except Exception:
            pass

    def aplicar_filtro_tra(self):
        """Aplica filtros jerárquicos y de texto a los datos TRA usando las nuevas funciones de filtrado"""
        if not hasattr(self, 'cached_ventas_tra') or not self.cached_ventas_tra:
            # Solo aviso en warning, no debug
            self.log("No hay datos TRA cacheados para filtrar", "WARNING")
            return
    
        # Obtener códigos seleccionados  
        dept_cod = self.tra_dept_dict.get(self.tra_dept_var.get()) if hasattr(self, 'tra_dept_var') else None
        group_cod = None
        sub_cod = None
    
        if dept_cod and hasattr(self, 'tra_group_var'):
            group_desc = self.tra_group_var.get()
            group_cod = self.tra_group_dict.get(dept_cod, {}).get(group_desc)
        
            if group_cod and hasattr(self, 'tra_sub_var'):
                sub_desc = self.tra_sub_var.get()
                # Usar string como key (formato: "dept|group")
                key = f"{dept_cod}|{group_cod}"
                sub_cod = self.tra_sub_dict.get(key, {}).get(sub_desc)
    
        # Obtener texto de búsqueda
        texto = self.tra_search_var.get() if hasattr(self, 'tra_search_var') else ''
        
        # Obtener favoritos
        favoritos = self._get_favoritos_local()
    
        # Usar las nuevas funciones de filtrado
        from pal.services.tra import filter_ventas_tra, paginate_tra
        
        # Debug: verificar datos antes del filtro (con throttling para evitar spam)
        self.tra_debug_log(
            f"Aplicando filtros - Datos: {len(self.cached_ventas_tra)} | "
            f"Dept: {dept_cod}, Group: {group_cod}, Sub: {sub_cod}, Texto: '{texto}'",
            throttle_key="filter_input",
            throttle_seconds=2.0
        )
        
        # Obtener alertas de stock si están disponibles
        alertas_para_filtro = getattr(self, 'cached_alertas', [])
        
        # Filtrar y ordenar
        datos_filtrados = filter_ventas_tra(
            ventas=self.cached_ventas_tra,
            dept_code=dept_cod,
            group_code=group_cod,
            sub_code=sub_cod,
            search_text=texto,
            filter_rotacion='TODAS',  # Por ahora no implementamos filtro por rotación en UI
            favoritos=favoritos,
            alertas_stock=alertas_para_filtro  # Pasar alertas para ordenamiento prioritario
        )
        
        self.tra_debug_log(
            f"Resultado filtrado: {len(datos_filtrados)} registros",
            throttle_key="filter_result",
            throttle_seconds=2.0
        )
        
        # Asegurar que la página actual sea válida
        if not hasattr(self, 'tra_current_page') or self.tra_current_page < 1:
            self.tra_current_page = 1
            
        # Paginación
        datos_pagina, total_paginas, self.tra_current_page = paginate_tra(
            datos_filtrados, self.tra_current_page, self.tra_page_size
        )
        
        self.tra_debug_log(
            f"Paginación: página {self.tra_current_page}/{total_paginas} ({len(datos_pagina)} registros)",
            throttle_key="pagination",
            throttle_seconds=1.5
        )
        
        # Actualizar vista
        self.mostrar_tra_paginado(datos_pagina)
        self.actualizar_controles_paginacion_tra(total_paginas)
    
    def mostrar_tra_paginado(self, datos):
        """Muestra datos TRA paginados en el Treeview con colores, stock actual e ideal, días restantes y porcentajes"""
        if not hasattr(self, 'tra_tree'):
            self.tra_debug_log("Error: tra_tree no existe")  # Usar función condicional
            return
            
        self.tra_tree.delete(*self.tra_tree.get_children())
        
        if not datos:
            # Solo loggear una vez para evitar spam
            self.tra_debug_log(
                "No hay datos para mostrar en esta página",
                level="DEBUG",
                throttle_key="empty_page",
                throttle_seconds=5.0
            )
            return
            
        # Optimización: solo calcular porcentajes si no están en cache o si hay cambios significativos
        cached_data = getattr(self, 'cached_ventas_tra', [])
        
        # Cache de porcentajes para evitar recalcular constantemente
        if not hasattr(self, 'tra_porcentajes_map') or not hasattr(self, '_tra_last_porcentaje_count'):
            self.tra_porcentajes_map = {}
            self._tra_last_porcentaje_count = 0
        
        # Solo recalcular si hay cambios significativos (>10% de diferencia)
        current_count = len(cached_data)
        count_diff = abs(current_count - self._tra_last_porcentaje_count)
        
        if count_diff > max(10, current_count * 0.1):  # Más de 10 registros o 10% de diferencia
            from pal.services.tra import calcular_porcentajes_representacion
            self.tra_porcentajes_map = calcular_porcentajes_representacion(cached_data)
            self._tra_last_porcentaje_count = current_count
            self.tra_debug_log(
                f"Porcentajes recalculados para {current_count} productos",
                throttle_key="percentage_calc",
                throttle_seconds=5.0
            )
            
        # Optimización: cache de stock para evitar consultas repetidas
        codigos = [r[0] for r in datos]
        sede = self.tra_sede_codigo or '0301'
        
        # Cache de stock con TTL de 30 segundos
        if not hasattr(self, '_stock_cache') or not hasattr(self, '_stock_cache_time'):
            self._stock_cache = {}
            self._stock_cache_time = 0
        
        current_time = time.time()
        cache_ttl = 30  # 30 segundos
        
        # Identificar qué códigos necesitamos consultar
        codigos_faltantes = [
            cod for cod in codigos 
            if cod not in self._stock_cache or (current_time - self._stock_cache_time) > cache_ttl
        ]
        
        # Solo consultar los códigos que faltan en cache
        if codigos_faltantes:
            nuevos_stocks = self.obtener_stock_actual_bulk(codigos_faltantes, sede)
            self._stock_cache.update(nuevos_stocks)
            self._stock_cache_time = current_time
            self.tra_debug_log(
                f"Stock consultado: {len(codigos_faltantes)} códigos nuevos",
                throttle_key="stock_query",
                throttle_seconds=3.0
            )
        
        # Usar el cache para obtener el stock
        stock_map = {cod: self._stock_cache.get(cod, 0) for cod in codigos}
        
        for idx, fila in enumerate(datos):
            try:
                # Manejo robusto para diferentes longitudes de tupla
                if len(fila) >= 7:
                    # Tomar por índice para evitar errores de desempaquetado si vienen campos extra
                    codigo = fila[0]
                    desc = fila[1]
                    neto = fila[5]
                    rotacion = fila[6]
                elif len(fila) >= 6:
                    codigo, desc, _, _, _, neto = fila[:6]
                    rotacion = "SIN CLASIFICAR"
                    # Solo loggear la primera vez para evitar spam
                    self.tra_debug_log(
                        f"Fila con 6 campos (sin rotación): {codigo}",
                        throttle_key="missing_rotation",
                        throttle_seconds=10.0
                    )
                else:
                    self.log(f"[TRA DEBUG] Fila con formato incorrecto ({len(fila)} campos): {fila}", "WARNING")
                    continue

                stock_actual = int(stock_map.get(codigo, 0) or 0)
                porcentaje = getattr(self, 'tra_porcentajes_map', {}).get(str(codigo), 0.0)

                # Calcular stock ideal y días restantes
                stock_ideal = self.calcular_stock_ideal_producto(neto)
                dias_restantes = self.calcular_dias_restantes(
                    stock_actual, neto, 
                    self.tra_fecha_inicio or datetime.now(),
                    self.tra_fecha_fin or datetime.now()
                )

                # Determinar tag de color según rotación con filas alternadas
                tag_base = (str(rotacion).lower() if rotacion else "sin_clasificar")
                if idx % 2 == 0:
                    tag_rotacion = tag_base  # Filas pares: colores claros
                else:
                    tag_rotacion = f"{tag_base}_alt"  # Filas impares: colores oscuros

                # Formatear neto: si es entero, mostrar sin decimales
                neto_valor = float(neto or 0)
                neto_formateado = int(neto_valor) if neto_valor == int(neto_valor) else round(neto_valor, 2)
                
                self.tra_tree.insert(
                    "", tk.END,
                    values=(codigo, desc, rotacion, neto_formateado, f"{porcentaje}%", stock_actual, stock_ideal, dias_restantes),
                    tags=(tag_rotacion,)
                )
            except Exception as e:
                self.log(f"Error procesando fila TRA {fila}: {str(e)}", "ERROR")
                continue
    
    def actualizar_controles_paginacion_tra(self, total_paginas):
        """Actualiza los controles de paginación TRA"""
        if hasattr(self, 'tra_pagina_label'):
            self.tra_pagina_label.config(text=f"Página {self.tra_current_page}/{total_paginas}")
        
        if hasattr(self, 'tra_btn_prev'):
            self.tra_btn_prev['state'] = 'normal' if self.tra_current_page > 1 else 'disabled'
        
        if hasattr(self, 'tra_btn_next'):
            self.tra_btn_next['state'] = 'normal' if self.tra_current_page < total_paginas else 'disabled'
    
    def _check_jerarquia_cache(self):
        """Verifica si existe cache válido de jerarquías"""
        try:
            import os
            import json
            from datetime import datetime, timedelta
            
            cache_file = "jerarquia_cache.json"
            cache_ttl = timedelta(hours=12)  # Cache por 12 horas
            
            if not os.path.exists(cache_file):
                return None
            
            # Verificar TTL
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - mtime > cache_ttl:
                self.log("Cache de jerarquía expirado, recargando...", "INFO")
                try:
                    os.remove(cache_file)
                except Exception:
                    pass
                return None
            
            # Cargar datos desde cache
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            self.log("⚙️ Cache de jerarquía cargado exitosamente", "SUCCESS")
            return cached_data
            
        except Exception as e:
            self.log(f"Error verificando cache de jerarquía: {e}", "ERROR")
            return None
    
    def _save_jerarquia_cache(self, data):
        """Guarda jerarquías en cache local"""
        try:
            import json
            
            cache_file = "jerarquia_cache.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.log("💾 Cache de jerarquía guardado", "DEBUG")
            
        except Exception as e:
            self.log(f"Error guardando cache de jerarquía: {e}", "ERROR")
    
    def cargar_jerarquia_unificada(self):
        """Carga jerarquías TRA y MBRP con una sola consulta optimizada JOIN"""
        import time
        # Evitar cargas duplicadas si ya fue cargado por otro hilo
        if getattr(self, 'jerarquias_unificadas_cargadas', False):
            self.log("Jerarquía unificada ya cargada — se omite carga duplicada", "DEBUG")
            return
        start_time = time.perf_counter()
        
        # Verificar cache primero
        cached_data = self._check_jerarquia_cache()
        if cached_data and 'tra' in cached_data and 'mbrp' in cached_data:
            # Cargar TRA desde cache
            tra_data = cached_data['tra']
            self.tra_dept_dict = tra_data.get('departments', {})
            self.tra_group_dict = tra_data.get('groups', {})
            self.tra_sub_dict = tra_data.get('subgroups', {})
            
            # Cargar MBRP desde cache
            mbrp_data = cached_data['mbrp']
            self.mbrp_dept_dict = mbrp_data.get('departments', {})
            self.mbrp_group_dict = mbrp_data.get('groups', {})
            self.mbrp_sub_dict = mbrp_data.get('subgroups', {})
            
            # Actualizar combos si existen
            self._update_hierarchy_combos()
            
            total_items = (len(self.tra_dept_dict) + sum(len(v) for v in self.tra_group_dict.values()) + 
                          sum(len(v) for v in self.tra_sub_dict.values()))
            
            load_time = time.perf_counter() - start_time
            self.jerarquias_unificadas_cargadas = True
            self.log(f"⚡ Jerarquía UNIFICADA cargada desde cache en {load_time:.3f}s - {total_items} elementos", "SUCCESS")
            
            # Programar actualización adicional por si los combos se crean después
            if hasattr(self, 'root'):
                self.root.after(200, self._update_hierarchy_combos)
            return
        
        # Si no hay cache válido, cargar desde BD con consulta optimizada
        if not self.db_manager or not self.db_manager.ensure_connection():
            self.log("No hay conexión válida para cargar jerarquía unificada", "WARNING")
            return
        
        try:
            # Consulta JOIN optimizada: UNA SOLA consulta en lugar de 6
            query = """
            SELECT DISTINCT
                d.C_CODIGO as dept_cod, d.C_DESCRIPCIO as dept_desc,
                g.C_CODIGO as group_cod, g.C_DESCRIPCIO as group_desc,
                s.C_CODIGO as sub_cod, s.C_DESCRIPCIO as sub_desc
            FROM MA_DEPARTAMENTOS d
            LEFT JOIN MA_GRUPOS g ON d.C_CODIGO = g.C_DEPARTAMENTO
            LEFT JOIN MA_SUBGRUPOS s ON g.C_DEPARTAMENTO = s.C_IN_DEPARTAMENTO 
                AND g.C_CODIGO = s.C_IN_GRUPO
            WHERE d.C_CODIGO IS NOT NULL AND d.C_DESCRIPCIO IS NOT NULL
            ORDER BY d.C_CODIGO, g.C_CODIGO, s.C_CODIGO
            """
            
            data = self.db_manager.fetch_data(query)
            
            # Procesar resultados de forma eficiente O(n) en lugar de O(n²)
            tra_dept_dict = {}
            tra_group_dict = {}
            tra_sub_dict = {}
            
            for row in data:
                dept_cod, dept_desc, group_cod, group_desc, sub_cod, sub_desc = row
                
                # Departamentos (evitar duplicados)
                if dept_cod and dept_desc and dept_desc.strip() not in tra_dept_dict:
                    tra_dept_dict[dept_desc.strip()] = dept_cod.strip()
                    
                # Grupos por departamento  
                if group_cod and group_desc and dept_cod:
                    dept_key = dept_cod.strip()
                    if dept_key not in tra_group_dict:
                        tra_group_dict[dept_key] = {}
                    tra_group_dict[dept_key][group_desc.strip()] = group_cod.strip()
                    
                # Subgrupos por departamento y grupo
                if sub_cod and sub_desc and dept_cod and group_cod:
                    # Usar string como key en lugar de tupla para compatibilidad con JSON
                    key = f"{dept_cod.strip()}|{group_cod.strip()}"
                    if key not in tra_sub_dict:
                        tra_sub_dict[key] = {}
                    tra_sub_dict[key][sub_desc.strip()] = sub_cod.strip()
            # Asignar a ambos módulos (TRA y MBRP comparten la misma jerar quía)
            self.tra_dept_dict = tra_dept_dict
            self.tra_group_dict = tra_group_dict
            self.tra_sub_dict = tra_sub_dict
            
            self.mbrp_dept_dict = tra_dept_dict.copy()
            self.mbrp_group_dict = tra_group_dict.copy()
            self.mbrp_sub_dict = tra_sub_dict.copy()
            
            # Calcular totales
            total_items = len(tra_dept_dict) + sum(len(v) for v in tra_group_dict.values()) + sum(len(v) for v in tra_sub_dict.values())
            load_time = time.perf_counter() - start_time

            if total_items == 0:
                # Fallback explícito si la consulta no devolvió datos útiles
                self.log("Jerar quía unificada vacía, aplicando fallback por módulos", "WARNING")
                self.cargar_jerarquia_tra()
                self.cargar_jerarquia_mbrp()
                return
            
            # Actualizar combos MBRP inmediatamente si la pestaña ya existe
            if hasattr(self, 'mbrp_dept_combo') and self.mbrp_dept_dict:
                try:
                    self.mbrp_dept_combo['values'] = ['Todos'] + list(self.mbrp_dept_dict.keys())
                    if hasattr(self, 'mbrp_dept_var'):
                        self.mbrp_dept_var.set('Todos')
                except Exception:
                    pass
            
            # Actualizar combos si están disponibles
            self._update_hierarchy_combos()
            self._update_hierarchy_combos()
            
            # Marcar como cargado para evitar duplicados
            self.jerarquias_unificadas_cargadas = True
            
            # Guardar en cache unificado
            cache_data = {
                'tra': {
                    'departments': self.tra_dept_dict,
                    'groups': self.tra_group_dict,
                    'subgroups': self.tra_sub_dict
                },
                'mbrp': {
                    'departments': self.mbrp_dept_dict,
                    'groups': self.mbrp_group_dict,
                    'subgroups': self.mbrp_sub_dict
                }
            }
            self._save_jerarquia_cache(cache_data)
            
            self.log(f"⚙️ Jerarquía UNIFICADA cargada y cacheada en {load_time:.3f}s - {total_items} elementos", "SUCCESS")
            
            # Programar actualización adicional después de 200ms por si los combos se crean tarde
            if hasattr(self, 'root'):
                self.root.after(200, self._update_hierarchy_combos)
            
        except Exception as e:
            self.log(f"Error cargando jerarquía unificada: {e}", "ERROR")
            # Fallback a métodos individuales
            self.cargar_jerarquia_tra()
            self.cargar_jerarquia_mbrp()
    
    def _update_hierarchy_combos(self):
        """Actualiza los combos de jerar quía para ambos módulos"""
        try:
            tra_actualizado = False
            mbrp_actualizado = False
            
            # Debug: verificar estado
            has_tra_combo = hasattr(self, 'tra_dept_combo')
            has_mbrp_combo = hasattr(self, 'mbrp_dept_combo')
            has_tra_dict = hasattr(self, 'tra_dept_dict') and self.tra_dept_dict
            has_mbrp_dict = hasattr(self, 'mbrp_dept_dict') and self.mbrp_dept_dict
            
            # TRA combos - con validación exhaustiva del widget
            if (has_tra_combo and has_tra_dict):
                try:
                    # Validar que el widget existe y es accesible
                    if self.tra_dept_combo.winfo_exists():
                        valores_tra = ['Todos'] + list(self.tra_dept_dict.keys())
                        self.tra_dept_combo['values'] = valores_tra
                        if hasattr(self, 'tra_dept_var'):
                            self.tra_dept_var.set('Todos')
                        tra_actualizado = True
                except (tk.TclError, AttributeError):
                    # Widget destruido o no accesible
                    pass
                
            # MBRP combos - con validación exhaustiva del widget
            if (has_mbrp_combo and has_mbrp_dict):
                try:
                    # Validar que el widget existe y es accesible
                    if self.mbrp_dept_combo.winfo_exists():
                        valores_mbrp = ['Todos'] + list(self.mbrp_dept_dict.keys())
                        self.mbrp_dept_combo['values'] = valores_mbrp
                        if hasattr(self, 'mbrp_dept_var'):
                            self.mbrp_dept_var.set('Todos')
                        mbrp_actualizado = True
                except (tk.TclError, AttributeError):
                    # Widget destruido o no accesible
                    pass
            
            # Log consolidado - solo una línea
            if tra_actualizado or mbrp_actualizado:
                modulos = []
                if tra_actualizado:
                    modulos.append(f"TRA({len(self.tra_dept_dict)} depts)")
                if mbrp_actualizado:
                    modulos.append(f"MBRP({len(self.mbrp_dept_dict)} depts)")
                self.log(f"✅ Filtros actualizados: {', '.join(modulos)}", "SUCCESS")
            elif has_mbrp_dict and not mbrp_actualizado:
                # Debug: MBRP tiene datos pero combo no se actualizó
                self.log(f"⚠️ MBRP tiene {len(self.mbrp_dept_dict)} depts pero combo aún no creado (has_combo={has_mbrp_combo})", "DEBUG")
                
        except Exception as e:
            self.log(f"Error actualizando combos de jerar quía: {e}", "ERROR")
    
    def _inicializar_modulos_paralelo(self):
        """Inicializa módulos en paralelo real usando ThreadPoolExecutor"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        start_time = time.perf_counter()
        self.log("🚀 Iniciando carga paralela de módulos...", "INFO")
        
        # Definir tareas a ejecutar en paralelo
        tareas = []
        
        # Stock: filtros + alertas iniciales
        if self.modules_enabled.get("stock", False):
            tareas.append(("stock_filters", self._load_stock_parallel))
            tareas.append(("stock_alerts", self._load_stock_alerts_parallel))
        
        # Jerarquías TRA/MBRP unificadas
        if (self.modules_enabled.get("tra", False) or self.modules_enabled.get("mbrp", False)):
            tareas.append(("jerarquias", self._load_hierarchies_parallel))
        
        # Jerarquía de productos (para stock)
        if self.modules_enabled.get("stock", False):
            tareas.append(("producto_jerarquia", self._init_jerarquia_async))
        
        # Ejecutar tareas en paralelo con máximo 4 hilos
        max_workers = min(4, len(tareas)) if tareas else 1
        resultados = {}
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ModuleInit") as executor:
                # Enviar todas las tareas
                future_to_task = {
                    executor.submit(task_func): task_name 
                    for task_name, task_func in tareas
                }
                
                # Procesar resultados conforme van completando
                for future in as_completed(future_to_task, timeout=30):
                    task_name = future_to_task[future]
                    try:
                        resultado = future.result(timeout=5)
                        resultados[task_name] = {"status": "success", "result": resultado}
                        self.log(f"✅ Módulo {task_name} cargado exitosamente", "SUCCESS")
                    except Exception as e:
                        resultados[task_name] = {"status": "error", "error": str(e)}
                        self.log(f"❌ Error en módulo {task_name}: {e}", "ERROR")
                        
        except Exception as e:
            self.log(f"Error en carga paralela: {e}", "ERROR")
            # Evitar fallback si ya hay módulos críticos listos (por ejemplo, jerarquías)
            if not getattr(self, 'jerarquias_unificadas_cargadas', False):
                self._fallback_inicializacion_secuencial()
            else:
                self.log("Omitiendo fallback: jerarquías ya cargadas", "INFO")
            return
        
        # Estadísticas finales
        total_time = time.perf_counter() - start_time
        exitosos = sum(1 for r in resultados.values() if r["status"] == "success")
        fallidos = len(resultados) - exitosos
        
        self.log(
            f"🎆 Inicialización paralela completada en {total_time:.3f}s | "
            f"Módulos: {exitosos} exitosos, {fallidos} fallidos", 
            "SUCCESS" if fallidos == 0 else "WARNING"
        )
        
        # Ejecutar tareas post-carga en hilo principal
        self.root.after(100, self._post_init_tasks, resultados)
    
    def _load_stock_parallel(self):
        """Carga filtros de stock en hilo paralelo"""
        try:
            self.load_stock_filters()
            return {"filters_loaded": True}
        except Exception as e:
            raise Exception(f"Error cargando filtros stock: {e}")
    
    def _load_stock_alerts_parallel(self):
        """Carga alertas iniciales de stock en hilo paralelo"""
        try:
            # Ensure connection is valid before loading alerts
            if not self.db_manager.ensure_connection():
                raise Exception("No hay conexión válida a la base de datos")
            
            # Use a smaller, safer initial load
            alertas = self.db_manager.obtener_alertas_stock(limit=50)
            if alertas:
                self.cached_alertas = alertas
                self.last_refresh = datetime.now()
                self.log(f"Alertas stock cargadas: {len(alertas)} registros", "SUCCESS")
            
            return {"alerts_loaded": True, "count": len(alertas) if alertas else 0}
        except Exception as e:
            self.log(f"Error cargando alertas stock: {e}", "ERROR")
            # Don't raise - allow app to continue without initial alerts
            return {"alerts_loaded": False, "error": str(e)}
    
    def _load_hierarchies_parallel(self):
        """Carga jerarquías unificadas en hilo paralelo"""
        try:
            self.cargar_jerarquia_unificada()
            # Programar actualización de combos en hilo principal después de cargar
            self.root.after(100, self._update_hierarchy_combos)
            return {"hierarchies_loaded": True}
        except Exception as e:
            # Fallback a métodos individuales
            try:
                if self.modules_enabled.get("tra", False):
                    self.cargar_jerarquia_tra()
                if self.modules_enabled.get("mbrp", False):
                    self.cargar_jerarquia_mbrp()
                # Programar actualización de combos incluso en fallback
                self.root.after(100, self._update_hierarchy_combos)
                return {"hierarchies_loaded": True, "fallback": True}
            except Exception as e2:
                raise Exception(f"Error cargando jerarquías: {e} (fallback: {e2})")
    
    def _fallback_inicializacion_secuencial(self):
        """Fallback a inicialización secuencial si falla la paralela"""
        self.log("⚠️ Fallback: carga secuencial de módulos", "WARNING")
        
        try:
            if self.modules_enabled.get("stock", False):
                self.load_stock_filters()
                self.actualizar_alertas_stock(force_refresh=True)
                threading.Thread(target=self._init_jerarquia_async, daemon=True).start()
            
            if (self.modules_enabled.get("tra", False) or self.modules_enabled.get("mbrp", False)) and not getattr(self, 'jerarquias_unificadas_cargadas', False):
                self.cargar_jerarquia_unificada()
                
        except Exception as e:
            self.log(f"Error en fallback secuencial: {e}", "ERROR")
    
    def _post_init_tasks(self, resultados):
        """Tareas post-inicialización en hilo principal"""
        try:
            # Realizar búsqueda inicial si stock está habilitado y fue exitoso
            if (self.modules_enabled.get("stock", False) and 
                resultados.get("stock_filters", {}).get("status") == "success"):
                # Esto se ejecuta en hilo principal para actualizar UI
                pass  # search_records ya se ejecutó antes
                
        except Exception as e:
            self.log(f"Error en tareas post-inicialización: {e}", "ERROR")
    
    def cargar_jerarquia_tra(self):
        """Carga diccionarios para departamentos, grupos y subgrupos con cache optimizado"""
        # Intentar cargar desde cache primero
        cached_data = self._check_jerarquia_cache()
        if cached_data and 'tra' in cached_data:
            try:
                tra_data = cached_data['tra']
                self.tra_dept_dict = tra_data.get('departments', {})
                self.tra_group_dict = tra_data.get('groups', {})
                self.tra_sub_dict = tra_data.get('subgroups', {})
                
                # Actualizar combo de departamentos si existe
                if hasattr(self, 'tra_dept_combo') and self.tra_dept_dict:
                    self.tra_dept_combo['values'] = ['Todos'] + list(self.tra_dept_dict.keys())
                    self.tra_dept_var.set('Todos')
                
                total_items = len(self.tra_dept_dict) + sum(len(v) for v in self.tra_group_dict.values()) + sum(len(v) for v in self.tra_sub_dict.values())
                self.log(f"⚙️ Jerarquía TRA cargada desde cache - {total_items} elementos", "SUCCESS")
                return
            except Exception as e:
                self.log(f"Error usando cache TRA: {e}", "ERROR")
        
        # Verificar conexión a la base de datos
        if not self.db_manager or not self.db_manager.ensure_connection():
            self.log("No hay conexión válida a la base de datos para cargar jerarquía TRA", "WARNING")
            return
        
        # Inicializar diccionarios vacíos por si hay errores
        self.tra_dept_dict = {}
        self.tra_group_dict = {}
        self.tra_sub_dict = {}
        
        try:
            # Departamentos con manejo de errores específico
            try:
                deps = self.db_manager.fetch_data(
                    "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_DEPARTAMENTOS WHERE C_CODIGO IS NOT NULL AND C_DESCRIPCIO IS NOT NULL"
                )
                self.tra_dept_dict = {desc.strip(): cod.strip() for cod, desc in deps if cod and desc and str(cod).strip() and str(desc).strip()}
                
                # Actualizar combo de departamentos si existe
                if hasattr(self, 'tra_dept_combo') and self.tra_dept_dict:
                    self.tra_dept_combo['values'] = ['Todos'] + list(self.tra_dept_dict.keys())
                    self.tra_dept_var.set('Todos')
                    
                self.log(f"Departamentos TRA cargados: {len(self.tra_dept_dict)}", "DEBUG")
            except Exception as e:
                self.log(f"Error cargando departamentos TRA: {str(e)}", "ERROR")
        
            # Grupos por departamento con manejo de errores específico
            try:
                grupos = self.db_manager.fetch_data(
                    "SELECT C_DEPARTAMENTO, C_CODIGO, C_DESCRIPCIO FROM MA_GRUPOS WHERE C_DEPARTAMENTO IS NOT NULL AND C_CODIGO IS NOT NULL AND C_DESCRIPCIO IS NOT NULL"
                )
                self.tra_group_dict = {}
                for dept, cod, desc in grupos:
                    if dept and cod and desc:
                        dept_clean = str(dept).strip()
                        cod_clean = str(cod).strip()
                        desc_clean = str(desc).strip()
                        
                        if dept_clean not in self.tra_group_dict:
                            self.tra_group_dict[dept_clean] = {}
                        self.tra_group_dict[dept_clean][desc_clean] = cod_clean
                        
                self.log(f"Grupos TRA cargados: {sum(len(v) for v in self.tra_group_dict.values())}", "DEBUG")
            except Exception as e:
                self.log(f"Error cargando grupos TRA: {str(e)}", "ERROR")
        
            # Subgrupos por departamento y grupo con manejo de errores específico
            try:
                subs = self.db_manager.fetch_data(
                    "SELECT C_IN_DEPARTAMENTO, C_IN_GRUPO, C_CODIGO, C_DESCRIPCIO FROM MA_SUBGRUPOS WHERE C_IN_DEPARTAMENTO IS NOT NULL AND C_IN_GRUPO IS NOT NULL AND C_CODIGO IS NOT NULL AND C_DESCRIPCIO IS NOT NULL"
                )
                self.tra_sub_dict = {}
                for dept, grp, cod, desc in subs:
                    if dept and grp and cod and desc:
                        dept_clean = str(dept).strip()
                        grp_clean = str(grp).strip()
                        cod_clean = str(cod).strip()
                        desc_clean = str(desc).strip()
                        
                        # Usar string como key en lugar de tupla para compatibilidad con JSON
                        key = f"{dept_clean}|{grp_clean}"
                        if key not in self.tra_sub_dict:
                            self.tra_sub_dict[key] = {}
                        self.tra_sub_dict[key][desc_clean] = cod_clean
                        
                self.log(f"Subgrupos TRA cargados: {sum(len(v) for v in self.tra_sub_dict.values())}", "DEBUG")
            except Exception as e:
                self.log(f"Error cargando subgrupos TRA: {str(e)}", "ERROR")
            
            # Verificar si se cargaron datos
            total_items = len(self.tra_dept_dict) + sum(len(v) for v in self.tra_group_dict.values()) + sum(len(v) for v in self.tra_sub_dict.values())
            if total_items > 0:
                self.log(f"✅ Jerarquía TRA cargada correctamente - Total elementos: {total_items}", "SUCCESS")
                
                # Guardar en cache para próximas cargas
                try:
                    cache_data = {
                        'tra': {
                            'departments': self.tra_dept_dict,
                            'groups': self.tra_group_dict,
                            'subgroups': self.tra_sub_dict
                        }
                    }
                    
                    # Si ya existe cache con MBRP, combinar
                    existing_cache = self._check_jerarquia_cache()
                    if existing_cache:
                        cache_data.update(existing_cache)
                    
                    self._save_jerarquia_cache(cache_data)
                except Exception as e:
                    self.log(f"Error guardando cache TRA: {e}", "DEBUG")
            else:
                self.log("⚠️ Jerarquía TRA cargada pero sin datos disponibles", "WARNING")
        
        except Exception as e:
            self.log(f"Error general cargando jerarquía TRA: {str(e)}", "ERROR")
            # Asegurar que los diccionarios estén inicializados incluso en caso de error
            if not hasattr(self, 'tra_dept_dict'):
                self.tra_dept_dict = {}
            if not hasattr(self, 'tra_group_dict'):
                self.tra_group_dict = {}
            if not hasattr(self, 'tra_sub_dict'):
                self.tra_sub_dict = {}

    def cargar_jerarquia_mbrp(self):
        """Carga diccionarios para departamentos, grupos y subgrupos MBRP con cache optimizado"""
        # Intentar cargar desde cache primero
        cached_data = self._check_jerarquia_cache()
        if cached_data and 'mbrp' in cached_data:
            try:
                mbrp_data = cached_data['mbrp']
                self.mbrp_dept_dict = mbrp_data.get('departments', {})
                self.mbrp_group_dict = mbrp_data.get('groups', {})
                self.mbrp_sub_dict = mbrp_data.get('subgroups', {})
                
                # Actualizar combo de departamentos si existe
                if hasattr(self, 'mbrp_dept_combo') and self.mbrp_dept_dict:
                    self.mbrp_dept_combo['values'] = ['Todos'] + list(self.mbrp_dept_dict.keys())
                    self.mbrp_dept_var.set('Todos')
                
                self.log("⚙️ Jerarquía MBRP cargada desde cache", "SUCCESS")
                return
            except Exception as e:
                self.log(f"Error usando cache MBRP: {e}", "ERROR")
        
        if not getattr(self.db_manager, 'conn', None):
            return
        try:
            # Departamentos
            deps = self.db_manager.fetch_data(
                "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_DEPARTAMENTOS"
            )
            self.mbrp_dept_dict = {desc: cod for cod, desc in deps if cod and desc}
            
            # Actualizar combo de departamentos si existe
            if hasattr(self, 'mbrp_dept_combo'):
                self.mbrp_dept_combo['values'] = ['Todos'] + list(self.mbrp_dept_dict.keys())
                self.mbrp_dept_var.set('Todos')
        
            # Grupos por departamento
            grupos = self.db_manager.fetch_data(
                "SELECT C_DEPARTAMENTO, C_CODIGO, C_DESCRIPCIO FROM MA_GRUPOS"
            )
            self.mbrp_group_dict = {}
            for dept, cod, desc in grupos:
                if dept not in self.mbrp_group_dict:
                    self.mbrp_group_dict[dept] = {}
                if desc and cod:
                    self.mbrp_group_dict[dept][desc] = cod
        
            # Subgrupos por departamento y grupo
            subs = self.db_manager.fetch_data(
                "SELECT C_IN_DEPARTAMENTO, C_IN_GRUPO, C_CODIGO, C_DESCRIPCIO FROM MA_SUBGRUPOS"
            )
            self.mbrp_sub_dict = {}
            for dept, grp, cod, desc in subs:
                # Usar string como key en lugar de tupla para compatibilidad con JSON
                key = f"{dept}|{grp}"
                if key not in self.mbrp_sub_dict:
                    self.mbrp_sub_dict[key] = {}
                if desc and cod:
                    self.mbrp_sub_dict[key][desc] = cod
            
            self.log("Jerarquía MBRP cargada correctamente", "SUCCESS")
            
            # Guardar en cache para próximas cargas
            try:
                cache_data = {
                    'mbrp': {
                        'departments': self.mbrp_dept_dict,
                        'groups': self.mbrp_group_dict,
                        'subgroups': self.mbrp_sub_dict
                    }
                }
                
                # Si ya existe cache con TRA, combinar
                existing_cache = self._check_jerarquia_cache()
                if existing_cache:
                    cache_data.update(existing_cache)
                
                self._save_jerarquia_cache(cache_data)
            except Exception as e:
                self.log(f"Error guardando cache MBRP: {e}", "DEBUG")
        
        except Exception as e:
            self.log(f"Error cargando jerarquía MBRP: {str(e)}", "ERROR")
            self.mbrp_dept_dict = {}
            self.mbrp_group_dict = {}
            self.mbrp_sub_dict = {}

    
    def cargar_tra_base(self):
        """Carga datos TRA de forma instantánea - delegando trabajo pesado al hilo paralelo"""
        try:
            # Validación rápida del rango de fechas
            fecha_inicio = self.fecha_inicio_entry.get_date()
            fecha_fin = self.fecha_fin_entry.get_date()
            
            dias_diferencia = (fecha_fin - fecha_inicio).days
            if dias_diferencia > 365:
                messagebox.showwarning(
                    "Rango muy amplio", 
                    "Por favor seleccione un rango menor a 1 año para evitar problemas de rendimiento."
                )
                return
            
            sede = self.sede_var.get().split(" - ")[0]
            
            # Si ya hay una carga en curso, evitar lanzar otra simultáneamente
            try:
                if getattr(self, 'tra_loader_thread', None) is not None and self.tra_loader_thread.is_alive():
                    self.log("TRA: Ya hay una carga en curso; ignorando clic adicional", "WARNING")
                    try:
                        self.api_status.config(text="TRA: Carga en curso...", foreground="#004C97")
                    except Exception:
                        pass
                    return
            except Exception:
                pass

            # Limpiar datos previos y preparar parámetros
            self.cached_ventas_tra = []
            self.tra_fecha_inicio = fecha_inicio
            self.tra_fecha_fin = fecha_fin
            self.tra_sede_codigo = sede
            
            # Mostrar estado de carga inmediatamente
            try:
                self.api_status.config(text="TRA: Iniciando carga...", foreground="#004C97")
                self.global_progress.pack(side=tk.RIGHT, padx=10)
                self.global_progress.config(mode="indeterminate")
                self.global_progress.start(5)
            except Exception:
                pass
            
            # Log inicial
            self.log(f"🚀 TRA: Iniciando carga desde {fecha_inicio} hasta {fecha_fin} para sede {sede}", "INFO")
            
            # Mostrar mensaje temporal en la tabla
            if hasattr(self, 'tra_tree'):
                self.tra_tree.delete(*self.tra_tree.get_children())
                # Insertar mensaje de carga
                self.tra_tree.insert("", tk.END, values=(
                    "...", "Cargando datos TRA...", "...", "...", "...", "...", "...", "..."
                ), tags=("loading",))
            
            # Iniciar carga paralela inmediatamente (sin carga inicial bloqueante)
            from threading import Thread
            self.tra_loader_thread = Thread(target=self._background_load_ventas_tra, daemon=True, name="tra_loader")
            self.tra_loader_thread.start()
            self.log("✅ TRA: Carga paralela iniciada - UI lista para uso", "SUCCESS")
            
            # Ocultar progreso después de un momento
            self.root.after(2000, self._hide_tra_progress)
            
        except Exception as e:
            error_msg = f"Error iniciando carga TRA: {str(e)}"
            self.log(error_msg, "ERROR")
            try:
                self.api_status.config(text="TRA: Error", foreground="red")
                self.global_progress.stop()
                self.global_progress.pack_forget()
            except Exception:
                pass
    
    def _hide_tra_progress(self):
        """Oculta el progreso TRA después de iniciada la carga"""
        try:
            self.global_progress.stop()
            self.global_progress.pack_forget()
        except Exception:
            pass
    
    def on_tra_row_selected(self, event=None):
        """Log detallado al seleccionar una fila del TRA Treeview (solo en modo debug)."""
        try:
            if not getattr(self, 'tra_debug', False):
                return
            if not hasattr(self, 'tra_tree'):
                return
            sel = self.tra_tree.selection()
            if not sel:
                return
            item = self.tra_tree.item(sel[0])
            vals = item.get('values') or []
            if len(vals) < 7:
                return
            codigo = str(vals[0])
            desc = str(vals[1])
            rotacion = str(vals[2])
            try:
                neto = float(vals[3])
            except Exception:
                neto = 0.0
            try:
                stock_actual = int(vals[4])
            except Exception:
                stock_actual = 0
            try:
                stock_ideal = int(vals[5])
            except Exception:
                stock_ideal = 0

            # Intervalo de fechas desde el UI
            try:
                fi = self.fecha_inicio_entry.get_date()
                ff = self.fecha_fin_entry.get_date()
            except Exception:
                from datetime import datetime
                fi = ff = datetime.now().date()

            msg = (
                f"Selección TRA -> Código: {codigo} | Desc: {desc} | Rotación: {rotacion}\n"
                f"Intervalo: {fi} a {ff} | Ventas (neto): {neto} | Stock: {stock_actual} | Stock ideal: {stock_ideal}"
            )
            self.tra_debug_log(msg)
        except Exception as e:
            # No queremos romper selección por logs
            self.tra_debug_log(f"Error en on_tra_row_selected: {e}")
    
    def _on_tra_mouse_motion(self, event):
        """Maneja el movimiento del mouse para mostrar tooltips TRA"""
        try:
            if not hasattr(self, 'tra_tooltip') or not hasattr(self, 'tra_tree'):
                self.tra_debug_log("Tooltip o tree no disponible")
                return
            
            # Obtener item bajo el cursor
            item = self.tra_tree.identify_row(event.y)
            if not item:
                self.tra_tooltip.hide_tooltip()
                return
                
            # Obtener datos del item
            values = self.tra_tree.item(item, 'values')
            if not values:
                self.tra_debug_log("No hay valores en el item")
                return
                
            self.tra_debug_log(f"Valores del item: {values} (longitud: {len(values)})")
                
            # Ajustar índices según la nueva estructura de columnas
            # Columnas: Código, Descripción, Rotación, Neto, Representación %, Stock Actual, Stock Ideal, Días restantes
            if len(values) < 8:
                self.tra_debug_log(f"Item con pocos valores: {len(values)}")
                return
                
            codigo = str(values[0])
            descripcion = str(values[1])
            rotacion = str(values[2])
            
            try:
                neto = float(values[3])
            except (ValueError, IndexError):
                neto = 0.0
                
            # Saltar la columna de Representación % (index 4)
            try:
                stock_actual = int(values[5])  # Stock Actual
            except (ValueError, IndexError):
                stock_actual = 0
                
            try:
                stock_ideal = int(values[6])  # Stock Ideal
            except (ValueError, IndexError):
                stock_ideal = 0
            
            self.tra_debug_log(f"Mostrando tooltip para: {codigo} - {descripcion[:20]}...")
            
            # Mostrar tooltip con información completa
            self.tra_tooltip.show_tooltip(
                event, codigo, descripcion, neto, rotacion, stock_actual, stock_ideal
            )
            
        except Exception as e:
            self.tra_debug_log(f"Error en tooltip motion: {str(e)}")

    def calcular_stock_ideal_producto(self, neto_ventas):
        """Calcula el stock ideal para un producto basado en sus ventas netas"""
        try:
            fecha_inicio = self.fecha_inicio_entry.get_date()
            fecha_fin = self.fecha_fin_entry.get_date()
            dias_periodo = (fecha_fin - fecha_inicio).days or 1
            promedio_diario = neto_ventas / dias_periodo if dias_periodo else 0
            ciclo_reposicion_dias = 30
            factor_seguridad = 1.25
            factor_crecimiento = 1.15
            stock_ideal = promedio_diario * ciclo_reposicion_dias * factor_seguridad * factor_crecimiento
            return max(0, int(round(stock_ideal, 0)))
        except Exception as e:
            self.log(f"Error calculando stock ideal: {str(e)}", "ERROR")
            return 0
    
    def recalcular_stock_ideal_tra(self):
        """Recalcula el stock ideal para todos los productos TRA mostrados"""
        try:
            # Verificar tanto tra_ventas_datos (método antiguo) como cached_ventas_tra (nuevo método)
            if (not hasattr(self, 'tra_ventas_datos') or not self.tra_ventas_datos) and \
               (not hasattr(self, 'cached_ventas_tra') or not self.cached_ventas_tra):
                messagebox.showwarning("Sin datos", "Primero debe cargar los datos TRA")
                return
            
            self.log("Recalculando stock ideal para productos TRA...", "INFO")
            
            # Usar los datos cacheados y reaplicar los filtros para refrescar la vista
            if hasattr(self, 'cached_ventas_tra') and self.cached_ventas_tra:
                self.aplicar_filtro_tra()  # Esto recalculará y mostrará todo
            elif hasattr(self, 'tra_ventas_datos_filtrados') and self.tra_ventas_datos_filtrados:
                self.mostrar_pagina_tra()  # Método legacy
            else:
                # Si no hay datos filtrados, usar el método legacy
                datos_a_usar = getattr(self, 'tra_ventas_datos', [])
                if datos_a_usar:
                    self.tra_tree.delete(*self.tra_tree.get_children())
                    for fila in datos_a_usar[:self.tra_page_size]:  # Mostrar solo primera página
                        try:
                            if len(fila) >= 7:
                                codigo, desc, _, _, _, neto, rotacion = fila
                            elif len(fila) >= 6:
                                codigo, desc, _, _, _, neto = fila
                                rotacion = "SIN CLASIFICAR"
                            else:
                                continue
                                
                            # Calcular stock ideal
                            stock_ideal = self.calcular_stock_ideal_producto(neto)
                            
                            # Determinar tag de color según rotación
                            tag_rotacion = rotacion.lower() if rotacion else "sin_clasificar"
                            
                            self.tra_tree.insert(
                                "", tk.END,
                                values=(codigo, desc, rotacion, round(neto, 2), stock_ideal),
                                tags=(tag_rotacion,)
                            )
                        except Exception as e:
                            self.log(f"Error procesando fila en recalcular: {fila} -> {e}", "ERROR")
                            continue
            
            self.log("Stock ideal recalculado correctamente", "SUCCESS")
            
        except Exception as e:
            self.log(f"Error recalculando stock ideal: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Error al recalcular stock ideal: {str(e)}")
    
    def calcular_dias_restantes(self, stock_actual: int, neto_ventas: float, fecha_inicio, fecha_fin) -> int:
        """Calcula los días restantes antes de romper stock según promedio diario de ventas"""
        try:
            dias_periodo = (fecha_fin - fecha_inicio).days or 1
            promedio_diario = neto_ventas / dias_periodo if dias_periodo else 0
            if promedio_diario <= 0:
                return 0  # Sin consumo o regresos netos, no decrementa stock
            return max(0, int(stock_actual // promedio_diario))
        except Exception as e:
            self.log(f"Error calculando días restantes: {str(e)}", "ERROR")
            return 0
    
    def obtener_stock_actual_bulk(self, codigos: list, deposito: str) -> dict:
        """Obtiene stock actual por código en un depósito específico usando una sola consulta"""
        try:
            if not codigos:
                return {}
            # Evitar IN () muy grande dividiendo en chunks si es necesario
            MAX_IN = 900  # límite seguro para SQL Server
            resultado = {}
            for i in range(0, len(codigos), MAX_IN):
                chunk = codigos[i:i+MAX_IN]
                placeholders = ",".join(["?"] * len(chunk))
                sql = (
                    f"SELECT c_codarticulo, SUM(n_cantidad) "
                    f"FROM MA_DEPOPROD WITH (NOLOCK) "
                    f"WHERE c_coddeposito = ? AND c_codarticulo IN ({placeholders}) "
                    f"GROUP BY c_codarticulo"
                )
                params = [deposito] + chunk
                rows = self.db_manager.fetch_data(sql, params)
                for cod, sum_qty in rows:
                    try:
                        resultado[str(cod)] = int(sum_qty or 0)
                    except Exception:
                        resultado[str(cod)] = 0
                # asegurar claves para todos los códigos del chunk
                for cod in chunk:
                    resultado.setdefault(str(cod), 0)
            return resultado
        except Exception as e:
            self.log(f"Error obteniendo stock actual: {str(e)}", "ERROR")
            return {}
    
    def calcular_stock_ideal(self, fecha_inicio, fecha_fin):
        """Método legacy para compatibilidad con DataFrames"""
        if not hasattr(self, 'tra_ventas_df') or self.tra_ventas_df.empty:
            return

        df = self.tra_ventas_df.copy()
    
        dias_periodo = (fecha_fin - fecha_inicio).days or 1  # evitar división por cero
        promedio_diario = df['neto'] / dias_periodo
    
        # Parámetros para el cálculo
        ciclo_reposicion_dias = 30
        stock_ideal = promedio_diario * ciclo_reposicion_dias * 1.25 * 1.15
    
        df['stock_ideal'] = stock_ideal.round(0).astype(int)

        self.tra_ventas_df = df






    def show_records_view(self):
        self.main_notebook.select(self.records_tab)

    def show_messaging_view(self):
        self.main_notebook.select(self.messaging_tab)







    def log(self, message: str, level: str = 'INFO'):
        """Registrar mensaje con prefijo estandarizado para identificar origen en consola.
        Si el panel de logs aún no existe, hace un print de respaldo con prefijo [PAL][APP].
        """
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'SUCCESS']
        if level not in levels:
            level = 'INFO'

        # Asegurar contadores por defecto
        if not hasattr(self, 'log_counter'):
            self.log_counter = 0
        if not hasattr(self, 'max_logs'):
            self.max_logs = 200

        # Construir prefijo con ubicación del caller y thread
        try:
            caller = inspect.stack()[1]
            module = inspect.getmodule(caller.frame)
            mod_name = getattr(module, '__name__', 'unknown')
            func_name = caller.function
            line_no = caller.lineno
        except Exception:
            mod_name, func_name, line_no = 'unknown', 'unknown', 0
        thread_name = threading.current_thread().name
        timestamp = time.strftime("%H:%M:%S")
        prefix = f"[PAL][APP][{level}][{thread_name}][{mod_name}.{func_name}:{line_no}]"
        console_entry = f"{prefix} {message}\n"

        # SIEMPRE escribir en consola de debug flotante
        if hasattr(self, 'debug_console'):
            try:
                self.debug_console.write(console_entry.strip(), level)
            except Exception:
                pass

        # Rotar logs si excede el máximo
        try:
            if self.log_counter >= self.max_logs:
                self.limpiar_logs()
        except Exception:
            pass

        # Insertar en panel de logs si existe; usar solo mensaje como contenido y nivel como tag
        if hasattr(self, 'logs_text') and self.logs_text:
            try:
                self.logs_text.configure(state='normal')
                # Mostrar también el prefijo dentro del panel para consistencia
                self.logs_text.insert(tk.END, console_entry, level)
                self.logs_text.see(tk.END)  # Auto-scroll
                self.logs_text.configure(state='disabled')
                self.log_counter += 1
                return
            except Exception:
                pass

        # Respaldo a consola si no hay UI de logs disponible
        try:
            print(console_entry.strip())
        except Exception:
            pass

    def limpiar_logs(self):
        """Limpia el panel de logs y reinicia el contador de manera segura."""
        # Reiniciar contador siempre
        self.log_counter = 0
        # Limpiar el widget si existe
        if hasattr(self, 'logs_text') and self.logs_text:
            try:
                self.logs_text.configure(state='normal')
                self.logs_text.delete('1.0', tk.END)
                self.logs_text.configure(state='disabled')
            except Exception:
                # No bloquear si el widget no está listo
                pass

    
    def load_connection_settings(self):
        """Cargar configuración de conexión desde archivo, desencriptando valores."""
        if not os.path.exists(CONFIG_FILE):
            return None

        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)

        if 'Database' not in config:
            return None

        try:
        # Obtener los valores encriptados
            server_enc = config['Database'].get('server', '')
            database_enc = config['Database'].get('database', '')
            user_enc = config['Database'].get('user', '')

            # Desencriptar solo si existen datos
            server = self.cred_manager.decrypt(server_enc) if server_enc else ''
            database = self.cred_manager.decrypt(database_enc) if database_enc else ''
            user = self.cred_manager.decrypt(user_enc) if user_enc else ''

            return {
                'server': server,
                'database': database,
                'user': user
            }
        except Exception as e:
            # Mostrar error usando ErrorCode en la interfaz
            self.notification_manager.show_error("Error", f"No se pudo cargar la configuración: {str(e)}")
            return None
    

    def _ensure_admin_user(self):
        """Crea el usuario 'admin' si no existe con contraseña predeterminada '123' y habilita módulos."""
        try:
            rows = self.db_manager.fetch_data("SELECT id FROM pal_usuarios WHERE username = ?", ("admin",))
            if rows:
                return  # Ya existe
            # Crear con contraseña por defecto '123'
            salt = bcrypt.gensalt(rounds=12)
            pwd_hash = bcrypt.hashpw(b"123", salt).decode('utf-8')
            self.db_manager.execute_query(
                "INSERT INTO pal_usuarios (username, password_hash, nombre_completo, email, activo) VALUES (?, ?, ?, ?, 1)",
                ("admin", pwd_hash, "Administrador del Sistema", None)
            )
            user_id = int(self.db_manager.fetch_data("SELECT id FROM pal_usuarios WHERE username = ?", ("admin",))[0][0])
            for modulo_db in DB_MODULE_TO_FLAG.keys():
                self.db_manager.execute_query(
                    """
                    IF NOT EXISTS (SELECT 1 FROM pal_usuarios_modulos WHERE usuario_id = ? AND modulo = ?)
                        INSERT INTO pal_usuarios_modulos (usuario_id, modulo, habilitado) VALUES (?, ?, 1)
                    ELSE
                        UPDATE pal_usuarios_modulos SET habilitado = 1 WHERE usuario_id = ? AND modulo = ?
                    """,
                    (user_id, modulo_db, user_id, modulo_db, user_id, modulo_db)
                )
            self.log("Usuario 'admin' creado con contraseña predeterminada y módulos habilitados", "SUCCESS")
        except Exception as e:
            self.log(f"No se pudo crear usuario admin: {e}", "ERROR")

    def _ensure_admin_password_interactive(self):
        """Verifica el hash del usuario admin y permite definir una contraseña si es placeholder o inválido."""
        try:
            rows = self.db_manager.fetch_data("SELECT id, password_hash FROM pal_usuarios WHERE username = ?", ("admin",))
            if not rows:
                return
            user_id, pwd_hash = rows[0]
            pwd_hash = str(pwd_hash) if pwd_hash is not None else ""
            needs_set = (not pwd_hash) or ("PLACEHOLDER" in pwd_hash) or (not pwd_hash.startswith("$2")) or (len(pwd_hash) < 55)
            if not needs_set:
                return
            # Pedir nueva contraseña
            while True:
                p1 = simpledialog.askstring("Configurar contraseña", "Ingrese nueva contraseña para admin:", show='*', parent=self.root)
                if p1 is None:
                    # Cancelado
                    break
                p2 = simpledialog.askstring("Confirmar contraseña", "Confirme la contraseña:", show='*', parent=self.root)
                if p2 is None:
                    break
                if p1 != p2:
                    messagebox.showerror("Error", "Las contraseñas no coinciden")
                    continue
                # Generar hash y guardar
                salt = bcrypt.gensalt(rounds=12)
                new_hash = bcrypt.hashpw(p1.encode("utf-8"), salt).decode("utf-8")
                self.db_manager.execute_query("UPDATE pal_usuarios SET password_hash = ? WHERE id = ?", (new_hash, int(user_id)))
                self.log("Contraseña de admin actualizada", "SUCCESS")
                messagebox.showinfo("Listo", "Se actualizó la contraseña de admin")
                break
        except Exception as e:
            self.log(f"No se pudo configurar contraseña de admin: {e}", "WARNING")

    def attempt_auto_connect(self):
        """Intentar conexión automática y habilitar login integrado en el splash."""
        try:
            settings = self.load_connection_settings()
            if not settings:
                self.root.after(0, self.show_settings)
                return

            server = settings.get('server')
            database = settings.get('database')
            user = settings.get('user')
            password = self.cred_manager.get_temp_password()
            api_token = self.cred_manager.get_whatsapp_token()

            if server and database:
                total_start = time.perf_counter()
                if self.db_manager.connect(server, database, user, password):
                    self.update_status('connected', server=server, api_token=api_token)
                    self.log("Conexión a BD exitosa", "SUCCESS")
                    # Inicializar servicios de seguridad y auth
                    try:
                        from pal.core.audit_db import AuditDB
                        self.audit_db = AuditDB(self.db_manager)
                    except Exception:
                        self.audit_db = None
                    self.auth = AuthManager(self.db_manager)
                    # Crear admin si no existe (password predeterminada '123')
                    self._ensure_admin_user()
                    self.root.after(0, lambda: self.splash.enable_login(self._splash_login_submit))

                    # (Opcional) Verificar/crear esquema de seguridad luego del login
                    # Se hará tras login exitoso para evitar prompts durante el splash

                    # Continuar con carga del resto de módulos en paralelo
                    self._inicializar_modulos_paralelo()

                    total_elapsed = time.perf_counter() - total_start
                    self.log(f"🏁 App inicializada (parcial) en {total_elapsed:.2f}s", "INFO")
                return

            self.root.after(0, self.show_settings)
        except Exception:
            self.audit_log.log_event(
                "AUTO_CONNECT_FAILED",
                os.getlogin(),
                "FAILED",
                ErrorCode.DB_CONNECTION_FAILED
            )
            self.root.after(0, self.show_settings)





    def create_status_panel(self):
        status_frame = ttk.Frame(self.root, style="Status.TFrame")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Indicadores de estado
        self.db_status = ttk.Label(status_frame, text="BD: Desconectado", foreground="red")
        self.db_status.pack(side=tk.LEFT, padx=10)
        
        self.api_status = ttk.Label(status_frame, text="API: Inactiva", foreground="orange")
        self.api_status.pack(side=tk.LEFT)
        
        # Menú de usuario (Cerrar sesión, Configuración solo para admin)
        self.user_menu = ttk.Menubutton(status_frame, text="Usuario")
        user_menu_popup = tk.Menu(self.user_menu, tearoff=0)
        user_menu_popup.add_command(label="Cerrar sesión", command=self.logout)
        
        # Agregar opción de configuración solo si el usuario actual es admin
        is_admin = self.current_user and self.current_user.get('username', '').lower() == 'admin'
        if is_admin:
            user_menu_popup.add_separator()
            user_menu_popup.add_command(label="⚙️ Configuración Avanzada", command=self.show_settings)
        
        self.user_menu['menu'] = user_menu_popup
        self.user_menu.pack(side=tk.RIGHT, padx=10)

        # Barra de progreso global
        self.global_progress = ttk.Progressbar(
        status_frame, 
        orient="horizontal",
        length=200,
        mode="determinate"
        )
        self.global_progress.pack(side=tk.RIGHT, padx=10)
        self.global_progress.pack_forget()  # Ocultar inicialmente


    def setup_tooltips(self):
        if hasattr(self, 'num_cliente'):
            self.help_tooltips.add_tooltip(self.num_cliente, "Número de cliente (1-11 dígitos)")
        if hasattr(self, 'cod_producto'):
            self.help_tooltips.add_tooltip(self.cod_producto, "Código de producto (buscar en base de datos)")
        if hasattr(self, 'user_menu'):
            self.help_tooltips.add_tooltip(self.user_menu, "Menú de usuario con opciones de configuración")

    def show_settings(self):
    # Si ya existe una ventana, la traemos al frente
        if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Configuración Avanzada")
        self.settings_window.geometry("600x400")
    
        # Configurar protocolo de cierre
        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_close)
    
        notebook = ttk.Notebook(self.settings_window)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Pestaña de Conexión
        conn_frame = ttk.Frame(notebook)
        notebook.add(conn_frame, text="Conexión BD")
        self.create_connection_tab(conn_frame)
        
        # Pestaña de API
        api_frame = ttk.Frame(notebook)
        notebook.add(api_frame, text="API WhatsApp")
        self.create_api_tab(api_frame)
    
        # Pestaña de Módulos: gestionar usuarios y privilegios
        modules_frame = ttk.Frame(notebook)
        notebook.add(modules_frame, text="Gestión de Usuarios")
        self._create_user_management_tab(modules_frame)

        # Pestaña de Depuración
        debug_frame = ttk.Frame(notebook)
        notebook.add(debug_frame, text="Depuración")

        self.debug_vars = {}
        for idx, (key, label) in enumerate([
            ("tra", "Habilitar logs de depuración de T.R.A"),
            ("stock", "Habilitar logs de depuración de Stock"),
            ("mbrp", "Habilitar logs de depuración de MBRP"),
            ("db", "Habilitar logs de depuración de Base de Datos"),
        ]):
            var = tk.BooleanVar(value=self.debug_flags.get(key, False) if hasattr(self, 'debug_flags') else False)
            cb = ttk.Checkbutton(debug_frame, text=label, variable=var)
            cb.grid(row=idx, column=0, sticky="w", padx=10, pady=5)
            self.debug_vars[key] = var

        ttk.Button(
            debug_frame,
            text="Guardar Depuración",
            command=self._save_debug_config
        ).grid(row=4, column=0, sticky="e", pady=10, padx=10)
        
        # Pestaña de Caché y Limpieza
        cache_frame = ttk.Frame(notebook)
        notebook.add(cache_frame, text="Caché y Limpieza")
        self._create_cache_cleanup_tab(cache_frame)

    def _create_cache_cleanup_tab(self, parent):
        """Pestaña para gestionar y limpiar cachés."""
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Gestionar Cachés del Sistema", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=10)
        
        # Información de cachés
        info_frame = ttk.LabelFrame(frame, text="Cachés Disponibles", padding=10)
        info_frame.pack(fill=tk.X, padx=5, pady=10)
        
        import os
        caches = [
            ("productos_jerarquia_cache.json", "Jerarquía de Productos"),
            ("jerarquia_cache.json", "Jerarquía TRA/MBRP"),
            ("stock_depositos_preference.json", "Preferencias de Depósitos"),
        ]
        
        cache_info = ttk.Frame(info_frame)
        cache_info.pack(fill=tk.BOTH, expand=True)
        
        for cache_file, desc in caches:
            cache_row = ttk.Frame(cache_info)
            cache_row.pack(fill=tk.X, pady=5)
            
            exists = os.path.exists(cache_file)
            status = "✔️" if exists else "❌"
            size = f"{os.path.getsize(cache_file) / 1024:.1f} KB" if exists else "No existe"
            
            ttk.Label(cache_row, text=f"{status} {desc}").pack(side=tk.LEFT, padx=5)
            ttk.Label(cache_row, text=size, foreground="gray").pack(side=tk.RIGHT, padx=5)
        
        # Botones de limpieza
        action_frame = ttk.LabelFrame(frame, text="Limpiar Caché", padding=10)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        btn1 = ttk.Button(
            action_frame,
            text="🗑️ Limpiar Jerarquía de Productos",
            command=lambda: self._clear_cache_file("productos_jerarquia_cache.json")
        )
        btn1.pack(fill=tk.X, pady=5)
        
        btn2 = ttk.Button(
            action_frame,
            text="🗑️ Limpiar Caché TRA/MBRP",
            command=lambda: self._clear_cache_file("jerarquia_cache.json")
        )
        btn2.pack(fill=tk.X, pady=5)
        
        btn3 = ttk.Button(
            action_frame,
            text="🗑️ Limpiar Preferencias de Depósitos",
            command=lambda: self._clear_cache_file("stock_depositos_preference.json")
        )
        btn3.pack(fill=tk.X, pady=5)
        
        # Botón para limpiar TODO
        btn_all = ttk.Button(
            action_frame,
            text="🗑️ LIMPIAR TODO",
            command=self._clear_all_caches
        )
        btn_all.pack(fill=tk.X, pady=10)
        
        # Nota informativa
        info_text = ttk.Frame(frame)
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        ttk.Label(
            info_text,
            text="⚠️ Nota: Limpiar el caché forzará que el sistema recargue los datos desde la base de datos.\n"
                 "Esto puede tomar más tiempo la próxima vez que cargues los módulos.",
            foreground="orange",
            wraplength=500,
            justify=tk.LEFT
        ).pack(fill=tk.BOTH, expand=True)
    
    def _clear_cache_file(self, filename):
        """Limpia un archivo de caché específíco."""
        try:
            import os
            if os.path.exists(filename):
                os.remove(filename)
                self.log(f"✅ Caché '{filename}' eliminado", "SUCCESS")
                messagebox.showinfo("Listo", f"✅ Caché '{filename}' eliminado exitosamente")
            else:
                messagebox.showinfo("Info", f"ℹ️ El archivo '{filename}' no existe")
        except Exception as e:
            self.log(f"❌ Error eliminando caché: {e}", "ERROR")
            messagebox.showerror("Error", f"❌ No se pudo eliminar el caché:\n{e}")
    
    def _clear_all_caches(self):
        """Limpia todos los cachés del sistema."""
        if not messagebox.askyesno("Confirmar", 
                                   "🗑️ ¿Está seguro de que desea limpiar TODO el caché?\n\n"
                                   "Esto incluirá:\n"
                                   "• Jerarquía de Productos\n"
                                   "• Caché TRA/MBRP\n"
                                   "• Preferencias de Depósitos"):
            return
        
        import os
        caches = [
            "productos_jerarquia_cache.json",
            "jerarquia_cache.json",
            "stock_depositos_preference.json",
        ]
        
        count = 0
        for cache_file in caches:
            try:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    count += 1
            except Exception as e:
                self.log(f"❌ Error eliminando {cache_file}: {e}", "ERROR")
        
        self.log(f"✅ {count} archivo(s) de caché eliminados", "SUCCESS")
        messagebox.showinfo("Listo", f"✅ Se eliminaron {count} archivo(s) de caché exitosamente")
    
    def _create_user_management_tab(self, parent):
        """Pestaña para gestionar usuarios y sus módulos (sólo admin)."""
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Permiso requerido: ADMIN.usuarios (fallback: usuario 'admin')
        allowed = False
        try:
            if hasattr(self, 'permissions') and self.current_user:
                allowed = self.permissions.tiene_permiso(self.current_user['id'], 'ADMIN', 'usuarios')
            if self.current_user and self.current_user.get('username', '').lower() == 'admin':
                allowed = True
        except Exception:
            allowed = self.current_user and self.current_user.get('username', '').lower() == 'admin'
        
        if not allowed:
            ttk.Label(frame, text="No tienes permiso para gestionar usuarios.", foreground="orange").pack(pady=20)
            return
        
        ttk.Label(frame, text="Gestionar módulos de usuarios", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=10)
        
        # Selector de usuario
        sel_frame = ttk.Frame(frame)
        sel_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Label(sel_frame, text="Seleccionar usuario:").pack(side=tk.LEFT, padx=5)
        
        try:
            rows = self.db_manager.fetch_data("SELECT id, username FROM pal_usuarios WHERE activo = 1 ORDER BY username")
            self.usuarios_list = [(int(r[0]), str(r[1])) for r in (rows or [])]
        except Exception:
            self.usuarios_list = []
        
        self.user_combo = ttk.Combobox(sel_frame, values=[u[1] for u in self.usuarios_list], state="readonly", width=25)
        self.user_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        if self.usuarios_list:
            self.user_combo.current(0)
            self.user_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_modules_list())
        
        # Frame para módulos
        modules_frame = ttk.LabelFrame(frame, text="Módulos habilitados", padding=10)
        modules_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        self.user_mod_vars = {}
        for idx, modulo_db in enumerate(sorted(DB_MODULE_TO_FLAG.keys())):
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(modules_frame, text=f"{modulo_db}", variable=var)
            cb.grid(row=idx, column=0, sticky="w", padx=10, pady=5)
            self.user_mod_vars[modulo_db] = var
        
        # Botones de acción
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Button(btn_frame, text="Guardar Módulos", command=self._save_user_modules_admin).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Recargar", command=self._refresh_modules_list).pack(side=tk.LEFT, padx=5)
        
        # Cargar módulos del primer usuario
        if self.usuarios_list:
            self._refresh_modules_list()
    
    def _refresh_modules_list(self):
        """Recarga los módulos del usuario seleccionado desde la BD."""
        try:
            sel_username = self.user_combo.get()
            user_id = next((u[0] for u in self.usuarios_list if u[1] == sel_username), None)
            if not user_id:
                return
            
            # Obtener módulos habilitados del usuario
            rows = self.db_manager.fetch_data(
                "SELECT modulo FROM pal_usuarios_modulos WHERE usuario_id = ? AND habilitado = 1",
                (user_id,)
            )
            enabled = {str(r[0]) for r in (rows or [])}
            
            # Actualizar checkboxes
            for modulo_db, var in self.user_mod_vars.items():
                var.set(modulo_db in enabled)
        except Exception as e:
            self.log(f"Error recargando módulos: {e}", "WARNING")
    
    def _save_user_modules_admin(self):
        """Guarda los módulos del usuario seleccionado en la BD."""
        try:
            # Permiso requerido
            can_manage = False
            try:
                if hasattr(self, 'permissions') and self.current_user:
                    can_manage = self.permissions.tiene_permiso(self.current_user['id'], 'ADMIN', 'usuarios')
                if self.current_user and self.current_user.get('username', '').lower() == 'admin':
                    can_manage = True
            except Exception:
                can_manage = False
            if not can_manage:
                messagebox.showwarning("Permiso denegado", "No tienes permiso para modificar módulos de usuarios")
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='PERMISSION_DENIED', usuario_id=self.current_user['id'], modulo='ADMIN', detalle='modificar_modulos')
                except Exception:
                    pass
                return
            
            sel_username = self.user_combo.get()
            user_id = next((u[0] for u in self.usuarios_list if u[1] == sel_username), None)
            if not user_id:
                messagebox.showwarning("Error", "Selecciona un usuario")
                return
            
            # Guardar cada módulo
            for modulo_db, var in self.user_mod_vars.items():
                habilitado = 1 if var.get() else 0
                # Upsert
                self.db_manager.execute_query(
                    """
                    IF NOT EXISTS (SELECT 1 FROM pal_usuarios_modulos WHERE usuario_id = ? AND modulo = ?)
                        INSERT INTO pal_usuarios_modulos (usuario_id, modulo, habilitado) VALUES (?, ?, ?)
                    ELSE
                        UPDATE pal_usuarios_modulos SET habilitado = ? WHERE usuario_id = ? AND modulo = ?
                    """,
                    (user_id, modulo_db, user_id, modulo_db, habilitado, habilitado, user_id, modulo_db)
                )
            
            messagebox.showinfo("Listo", f"Módulos de '{sel_username}' guardados")
            self.log(f"Módulos de '{sel_username}' actualizados", "SUCCESS")
            try:
                if hasattr(self, 'audit_db'):
                    self.audit_db.log_action(
                        accion='USER_MODULES_UPDATE', usuario_id=self.current_user['id'], modulo='ADMIN', detalle=f"user={sel_username}")
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")
            self.log(f"Error guardando módulos: {e}", "ERROR")
    
    def _create_admin_users_tab(self, parent):
        """Pestaña de administración de usuarios con crear/editar/eliminar."""
        main_frame = ttk.Frame(parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Secciones: Left (listado) y Right (formulario)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # LEFT: Listado de usuarios
        ttk.Label(left_frame, text="Usuarios del Sistema", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=5)
        
        # Treeview con usuarios
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.admin_users_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "username", "nombre", "activo"),
            height=12,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.admin_users_tree.yview)
        
        self.admin_users_tree.column("#0", width=0)
        self.admin_users_tree.column("id", width=30)
        self.admin_users_tree.column("username", width=100)
        self.admin_users_tree.column("nombre", width=150)
        self.admin_users_tree.column("activo", width=60)
        
        self.admin_users_tree.heading("#0", text="")
        self.admin_users_tree.heading("id", text="ID")
        self.admin_users_tree.heading("username", text="Usuario")
        self.admin_users_tree.heading("nombre", text="Nombre Completo")
        self.admin_users_tree.heading("activo", text="Activo")
        
        self.admin_users_tree.pack(fill=tk.BOTH, expand=True)
        self.admin_users_tree.bind("<<TreeviewSelect>>", lambda e: self._load_user_details())
        
        # Botones de acción
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="Recargar", command=self._reload_users_list).pack(side=tk.LEFT, padx=5)
        
        # RIGHT: Formulario de usuario
        ttk.Label(right_frame, text="Detalles del Usuario", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=5)
        
        form_frame = ttk.LabelFrame(right_frame, text="Información", padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(form_frame, text="Usuario:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.admin_user_username = ttk.Entry(form_frame, width=25)
        self.admin_user_username.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        ttk.Label(form_frame, text="Nombre Completo:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.admin_user_nombre = ttk.Entry(form_frame, width=25)
        self.admin_user_nombre.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        ttk.Label(form_frame, text="Email:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.admin_user_email = ttk.Entry(form_frame, width=25)
        self.admin_user_email.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        ttk.Label(form_frame, text="Contraseña:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.admin_user_password = ttk.Entry(form_frame, width=25, show="*")
        self.admin_user_password.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        
        ttk.Label(form_frame, text="(dejar en blanco para no cambiar)", foreground="gray").grid(row=4, column=1, sticky="w", padx=5)
        
        ttk.Label(form_frame, text="Activo:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        self.admin_user_activo = tk.BooleanVar(value=True)
        ttk.Checkbutton(form_frame, variable=self.admin_user_activo).grid(row=5, column=1, sticky="w", padx=5, pady=5)
        
        form_frame.columnconfigure(1, weight=1)
        
        # Módulos
        modules_frame = ttk.LabelFrame(right_frame, text="Módulos Habilitados", padding=10)
        modules_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.admin_user_mod_vars = {}
        for idx, modulo_db in enumerate(sorted(DB_MODULE_TO_FLAG.keys())):
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(modules_frame, text=modulo_db, variable=var)
            cb.grid(row=idx, column=0, sticky="w", padx=5, pady=2)
            self.admin_user_mod_vars[modulo_db] = var
        
        # Botones de acción
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="Nuevo Usuario", command=self._new_admin_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Guardar", command=self._save_admin_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Eliminar", command=self._delete_admin_user).pack(side=tk.LEFT, padx=5)
        
        # Cargar lista inicial
        self._reload_users_list()
    
    def _reload_users_list(self):
        """Recarga la lista de usuarios desde la BD."""
        try:
            self.admin_users_tree.delete(*self.admin_users_tree.get_children())
            rows = self.db_manager.fetch_data("SELECT id, username, nombre_completo, activo FROM pal_usuarios ORDER BY username")
            for r in (rows or []):
                user_id, username, nombre, activo = r
                activo_str = "✓" if activo else "❌"
                self.admin_users_tree.insert("", tk.END, values=(user_id, username, nombre, activo_str))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar usuarios: {e}")
    
    def _load_user_details(self):
        """Carga detalles del usuario seleccionado en el formulario."""
        try:
            sel = self.admin_users_tree.selection()
            if not sel:
                self._clear_user_form()
                return
            
            item = sel[0]
            values = self.admin_users_tree.item(item, "values")
            user_id = int(values[0])
            
            # Obtener datos del usuario
            rows = self.db_manager.fetch_data(
                "SELECT username, nombre_completo, email, activo FROM pal_usuarios WHERE id = ?",
                (user_id,)
            )
            if rows:
                username, nombre, email, activo = rows[0]
                self.admin_user_username.delete(0, tk.END)
                self.admin_user_username.insert(0, username)
                self.admin_user_nombre.delete(0, tk.END)
                self.admin_user_nombre.insert(0, nombre or "")
                self.admin_user_email.delete(0, tk.END)
                self.admin_user_email.insert(0, email or "")
                self.admin_user_password.delete(0, tk.END)  # No cargar password
                self.admin_user_activo.set(bool(activo))
                
                # Cargar módulos
                mod_rows = self.db_manager.fetch_data(
                    "SELECT modulo FROM pal_usuarios_modulos WHERE usuario_id = ? AND habilitado = 1",
                    (user_id,)
                )
                enabled_mods = {str(r[0]) for r in (mod_rows or [])}
                for modulo_db, var in self.admin_user_mod_vars.items():
                    var.set(modulo_db in enabled_mods)
                
                self.current_admin_user_id = user_id
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar detalles: {e}")
    
    def _clear_user_form(self):
        """Limpia el formulario de usuario."""
        self.admin_user_username.delete(0, tk.END)
        self.admin_user_nombre.delete(0, tk.END)
        self.admin_user_email.delete(0, tk.END)
        self.admin_user_password.delete(0, tk.END)
        self.admin_user_activo.set(True)
        for var in self.admin_user_mod_vars.values():
            var.set(False)
        self.current_admin_user_id = None
    
    def _new_admin_user(self):
        """Prepara formulario para crear nuevo usuario."""
        self._clear_user_form()
        self.admin_users_tree.selection_remove(self.admin_users_tree.selection())
        self.admin_user_username.focus()
    
    def _save_admin_user(self):
        """Guarda o crea usuario según lo indicado en el formulario."""
        try:
            # Permiso requerido
            can_manage = False
            try:
                if hasattr(self, 'permissions') and self.current_user:
                    can_manage = self.permissions.tiene_permiso(self.current_user['id'], 'ADMIN', 'usuarios')
                if self.current_user and self.current_user.get('username', '').lower() == 'admin':
                    can_manage = True
            except Exception:
                can_manage = False
            if not can_manage:
                messagebox.showwarning("Permiso denegado", "No tienes permiso para crear/editar usuarios")
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='PERMISSION_DENIED', usuario_id=self.current_user['id'], modulo='ADMIN', detalle='guardar_usuario')
                except Exception:
                    pass
                return
            
            # PROTECCIÓN: Solo el usuario 'admin' puede modificar su propia cuenta
            username = self.admin_user_username.get().strip()
            is_editing_admin = (hasattr(self, 'current_admin_user_id') and self.current_admin_user_id is not None and
                               username.lower() == 'admin')
            
            if is_editing_admin and self.current_user and self.current_user.get('username', '').lower() != 'admin':
                usuario_actual = self.current_user.get('username', 'DESCONOCIDO')
                
                messagebox.showerror(
                    "Acceso denegado",
                    "⚠️ PROTECCIÓN DE SEGURIDAD\n\nSolo el usuario 'admin' puede modificar su propia cuenta.\n\n" +
                    "Por seguridad, el acceso al usuario 'admin' está restringido."
                )
                
                self.log(
                    f"[SECURITY] Intento de modificar usuario admin desde: {usuario_actual}",
                    "ERROR"
                )
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='SECURITY_VIOLATION_ADMIN_MODIFY', usuario_id=self.current_user['id'], modulo='ADMIN',
                            detalle=f'Usuario {usuario_actual} intentó modificar cuenta admin', exitoso=False)
                except Exception:
                    pass
                return
            
            nombre = self.admin_user_nombre.get().strip()
            email = self.admin_user_email.get().strip() or None
            password = self.admin_user_password.get().strip()
            activo = 1 if self.admin_user_activo.get() else 0
            
            if not username or not nombre:
                messagebox.showwarning("Error", "Usuario y nombre son obligatorios")
                return
            
            is_new = not hasattr(self, 'current_admin_user_id') or self.current_admin_user_id is None
            user_id = None
            
            if is_new:
                # Crear nuevo usuario
                if not password:
                    messagebox.showwarning("Error", "La contraseña es obligatoria para nuevos usuarios")
                    return
                from pal.core.user_management import UserManager
                um = UserManager(self.db_manager)
                try:
                    user_id = um.crear_usuario(username, password, nombre, email)
                    messagebox.showinfo("Listo", f"Usuario '{username}' creado exitosamente")
                    try:
                        if hasattr(self, 'audit_db'):
                            self.audit_db.log_action(
                                accion='USER_CREATE', usuario_id=self.current_user['id'], modulo='ADMIN', detalle=f"username={username}")
                    except Exception:
                        pass
                except Exception as create_err:
                    messagebox.showerror("Error", f"No se pudo crear usuario: {str(create_err)}")
                    self.log(f"Error creando usuario: {create_err}", "ERROR")
                    return
            else:
                # Actualizar usuario existente
                user_id = self.current_admin_user_id
                self.db_manager.execute_query(
                    "UPDATE pal_usuarios SET nombre_completo = ?, email = ?, activo = ? WHERE id = ?",
                    (nombre, email, activo, user_id)
                )
                if password:
                    # Actualizar contraseña
                    salt = bcrypt.gensalt(rounds=12)
                    pwd_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
                    self.db_manager.execute_query(
                        "UPDATE pal_usuarios SET password_hash = ? WHERE id = ?",
                        (pwd_hash, user_id)
                    )
                messagebox.showinfo("Listo", f"Usuario '{username}' actualizado exitosamente")
                try:
                    if hasattr(self, 'audit_db'):
                        self.audit_db.log_action(
                            accion='USER_UPDATE', usuario_id=self.current_user['id'], modulo='ADMIN', detalle=f"id={user_id}")
                except Exception:
                    pass
            
            # Guardar módulos (solo si user_id es válido)
            if user_id:
                for modulo_db, var in self.admin_user_mod_vars.items():
                    habilitado = 1 if var.get() else 0
                    self.db_manager.execute_query(
                        """
                        IF NOT EXISTS (SELECT 1 FROM pal_usuarios_modulos WHERE usuario_id = ? AND modulo = ?)
                            INSERT INTO pal_usuarios_modulos (usuario_id, modulo, habilitado) VALUES (?, ?, ?)
                        ELSE
                            UPDATE pal_usuarios_modulos SET habilitado = ? WHERE usuario_id = ? AND modulo = ?
                        """,
                        (user_id, modulo_db, user_id, modulo_db, habilitado, habilitado, user_id, modulo_db)
                    )
                
                self.log(f"Usuario '{username}' guardado", "SUCCESS")
                self._reload_users_list()
                self._clear_user_form()
            else:
                messagebox.showerror("Error", "No se asignó un ID válido al usuario")
                self.log(f"Error: user_id inválido para '{username}'", "ERROR")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar usuario: {e}")
            self.log(f"Error guardando usuario: {e}", "ERROR")
    
    def _delete_admin_user(self):
        """Elimina (desactiva) el usuario seleccionado."""
        try:
            # Permiso requerido
            can_manage = False
            try:
                if hasattr(self, 'permissions') and self.current_user:
                    can_manage = self.permissions.tiene_permiso(self.current_user['id'], 'ADMIN', 'usuarios')
                if self.current_user and self.current_user.get('username', '').lower() == 'admin':
                    can_manage = True
            except Exception:
                can_manage = False
            if not can_manage:
                messagebox.showwarning("Permiso denegado", "No tienes permiso para desactivar usuarios")
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='PERMISSION_DENIED', usuario_id=self.current_user['id'], modulo='ADMIN', detalle='desactivar_usuario')
                except Exception:
                    pass
                return
            
            if not hasattr(self, 'current_admin_user_id') or self.current_admin_user_id is None:
                messagebox.showwarning("Error", "Selecciona un usuario para eliminar")
                return
            
            username = self.admin_user_username.get()
            
            # PROTECCIÓN: Impedir que se desactive el usuario 'admin'
            if username.lower() == 'admin':
                usuario_actual = self.current_user.get('username', 'DESCONOCIDO') if self.current_user else 'DESCONOCIDO'
                
                messagebox.showerror(
                    "Acceso denegado",
                    "⚠️ PROTECCIÓN DE SEGURIDAD\n\nNo se puede desactivar el usuario 'admin'.\n\n" +
                    "Este usuario es esencial para el sistema."
                )
                
                self.log(
                    f"[SECURITY] Intento de desactivar usuario admin desde: {usuario_actual}",
                    "ERROR"
                )
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='SECURITY_VIOLATION_ADMIN_DELETE', usuario_id=self.current_user['id'], modulo='ADMIN',
                            detalle=f'Usuario {usuario_actual} intentó desactivar cuenta admin', exitoso=False)
                except Exception:
                    pass
                return
            if messagebox.askyesno("Confirmar", f"¿Desactivar usuario '{username}'?"):
                self.db_manager.execute_query(
                    "UPDATE pal_usuarios SET activo = 0 WHERE id = ?",
                    (self.current_admin_user_id,)
                )
                messagebox.showinfo("Listo", f"Usuario '{username}' desactivado")
                self.log(f"Usuario '{username}' desactivado", "INFO")
                try:
                    if hasattr(self, 'audit_db'):
                        self.audit_db.log_action(
                            accion='USER_DEACTIVATE', usuario_id=self.current_user['id'], modulo='ADMIN', detalle=f"user={username}")
                except Exception:
                    pass
                self._reload_users_list()
                self._clear_user_form()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo desactivar usuario: {e}")
    
    # =========================
    # Roles y Permisos (Fase 5)
    # =========================
    def _create_roles_permissions_tab(self, parent):
        container = ttk.Frame(parent, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        # Split left (roles) / right (details + permisos + asignación a usuarios)
        left = ttk.Frame(container)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10))
        right = ttk.Frame(container)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # LEFT: Roles list
        ttk.Label(left, text="Roles", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.roles_tree = ttk.Treeview(
            tree_frame,
            columns=("id","nombre","sistema"),
            height=14,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.roles_tree.yview)
        self.roles_tree.column("#0", width=0)
        self.roles_tree.column("id", width=40)
        self.roles_tree.column("nombre", width=160)
        self.roles_tree.column("sistema", width=70)
        self.roles_tree.heading("#0", text="")
        self.roles_tree.heading("id", text="ID")
        self.roles_tree.heading("nombre", text="Nombre")
        self.roles_tree.heading("sistema", text="Sistema")
        self.roles_tree.pack(fill=tk.BOTH, expand=True)
        self.roles_tree.bind("<<TreeviewSelect>>", lambda e: self._on_role_select())

        btns = ttk.Frame(left)
        btns.pack(fill=tk.X, pady=5)
        ttk.Button(btns, text="Nuevo", command=self._new_role).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Guardar", command=self._save_role).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Eliminar", command=self._delete_role).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Recargar", command=self._reload_roles_list).pack(side=tk.LEFT, padx=2)

        # RIGHT: Details and permissions
        details = ttk.LabelFrame(right, text="Detalle del Rol", padding=10)
        details.pack(fill=tk.X)
        ttk.Label(details, text="Nombre:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.role_name_entry = ttk.Entry(details, width=30)
        self.role_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Label(details, text="Descripción:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.role_desc_entry = ttk.Entry(details, width=50)
        self.role_desc_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        details.columnconfigure(1, weight=1)

        # Permissions catalog (by module)
        self.perm_vars_by_id = {}
        self.perm_catalog_by_module = {}
        perms_rows = self.db_manager.fetch_data("SELECT id, codigo, modulo, descripcion FROM pal_permisos ORDER BY modulo, codigo") or []
        for pid, codigo, modulo, desc in perms_rows:
            m = str(modulo)
            self.perm_catalog_by_module.setdefault(m, []).append((int(pid), str(codigo), str(desc or "")))

        # Scrollable permissions container
        perms_container = ttk.LabelFrame(right, text="Permisos por módulo", padding=5)
        perms_container.pack(fill=tk.BOTH, expand=True, pady=10)

        canvas = tk.Canvas(perms_container, borderwidth=0, highlightthickness=0)
        vscroll = ttk.Scrollbar(perms_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        perms_inner = ttk.Frame(canvas)
        inner_window = canvas.create_window((0, 0), window=perms_inner, anchor="nw")

        def _on_perms_inner_configure(event=None):
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.itemconfigure(inner_window, width=canvas.winfo_width())
            except Exception:
                pass
        def _on_canvas_configure(event=None):
            try:
                canvas.itemconfigure(inner_window, width=canvas.winfo_width())
            except Exception:
                pass
        perms_inner.bind("<Configure>", _on_perms_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Optional: mouse wheel scrolling
        def _on_mousewheel(event):
            try:
                delta = -1 * (event.delta // 120)
                canvas.yview_scroll(delta, "units")
            except Exception:
                pass
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Build permission sections inside scrollable frame
        self.perm_section_frames = {}
        row_idx = 0
        for modulo, plist in sorted(self.perm_catalog_by_module.items()):
            sect = ttk.LabelFrame(perms_inner, text=modulo, padding=8)
            sect.grid(row=row_idx, column=0, sticky="ew", padx=5, pady=5)
            row_idx += 1
            # Checkboxes for this module
            col = 0
            for pid, codigo, desc in plist:
                var = tk.BooleanVar(value=False)
                cb = ttk.Checkbutton(sect, text=codigo.split('.')[-1], variable=var)
                cb.grid(row=0, column=col, sticky="w", padx=6, pady=4)
                self.perm_vars_by_id[pid] = var
                col += 1
        for i in range(row_idx):
            perms_inner.grid_rowconfigure(i, weight=0)
        perms_inner.grid_columnconfigure(0, weight=1)

        # Fixed action bar for saving permissions
        perm_actions = ttk.Frame(right)
        perm_actions.pack(fill=tk.X, pady=(0,5))
        ttk.Button(perm_actions, text="Guardar Permisos del Rol", command=self._save_role_permissions).pack(side=tk.RIGHT)

        # User-role assignment
        assign = ttk.LabelFrame(right, text="Asignación de Roles a Usuario", padding=10)
        assign.pack(fill=tk.BOTH, expand=False, pady=10)
        ttk.Label(assign, text="Usuario:").grid(row=0, column=0, sticky="w", padx=5)
        self.assign_user_combo = ttk.Combobox(assign, state="readonly", width=25)
        self.assign_user_combo.grid(row=0, column=1, sticky="w", padx=5)
        self.assign_user_combo.bind("<<ComboboxSelected>>", lambda e: self._load_user_roles_selector())

        # Roles checkboxes for selected user
        self.user_role_vars = {}
        self.user_roles_frame = ttk.Frame(assign)
        self.user_roles_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        ttk.Button(assign, text="Guardar Roles de Usuario", command=self._save_user_roles_assignment).grid(row=2, column=1, sticky="e", padx=5, pady=5)

        # Initialize data
        self.current_role_id = None
        self._reload_roles_list()
        self._reload_users_combo_for_assignment()

    def _reload_roles_list(self):
        try:
            rows = self.db_manager.fetch_data("SELECT id, nombre, es_sistema FROM pal_roles ORDER BY nombre") or []
            # Clear
            for item in self.roles_tree.get_children():
                self.roles_tree.delete(item)
            for rid, nombre, es_sistema in rows:
                self.roles_tree.insert("", tk.END, values=(int(rid), str(nombre), "Sí" if bool(es_sistema) else "No"))
        except Exception as e:
            self.log(f"Error cargando roles: {e}", "ERROR")

    def _on_role_select(self):
        try:
            sel = self.roles_tree.selection()
            if not sel:
                return
            values = self.roles_tree.item(sel[0], "values")
            role_id = int(values[0])
            self.current_role_id = role_id
            # Load details
            row = self.db_manager.fetch_data("SELECT nombre, descripcion FROM pal_roles WHERE id = ?", (role_id,))
            if row:
                self.role_name_entry.delete(0, tk.END)
                self.role_name_entry.insert(0, str(row[0][0] or ""))
                self.role_desc_entry.delete(0, tk.END)
                self.role_desc_entry.insert(0, str(row[0][1] or ""))
            # Load permissions for role
            for var in self.perm_vars_by_id.values():
                var.set(False)
            perm_rows = self.db_manager.fetch_data("SELECT permiso_id FROM pal_roles_permisos WHERE rol_id = ?", (role_id,)) or []
            for (pid,) in perm_rows:
                if int(pid) in self.perm_vars_by_id:
                    self.perm_vars_by_id[int(pid)].set(True)
        except Exception as e:
            self.log(f"Error cargando rol: {e}", "ERROR")

    def _new_role(self):
        try:
            self.current_role_id = None
            self.role_name_entry.delete(0, tk.END)
            self.role_desc_entry.delete(0, tk.END)
            for var in self.perm_vars_by_id.values():
                var.set(False)
        except Exception:
            pass

    def _save_role(self):
        try:
            nombre = self.role_name_entry.get().strip()
            descripcion = self.role_desc_entry.get().strip() or None
            if not nombre:
                messagebox.showwarning("Error", "El nombre del rol es obligatorio")
                return
            if self.current_role_id is None:
                # Crear
                self.db_manager.execute_query(
                    "INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (?, ?, 0)",
                    (nombre, descripcion)
                )
                self.current_role_id = int(self.db_manager.fetch_data("SELECT id FROM pal_roles WHERE nombre = ?", (nombre,))[0][0])
            else:
                # Actualizar
                self.db_manager.execute_query(
                    "UPDATE pal_roles SET nombre = ?, descripcion = ? WHERE id = ?",
                    (nombre, descripcion, self.current_role_id)
                )
            self._reload_roles_list()
            messagebox.showinfo("Listo", "Rol guardado")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el rol: {e}")

    def _delete_role(self):
        try:
            if not self.current_role_id:
                messagebox.showwarning("Error", "Selecciona un rol")
                return
            row = self.db_manager.fetch_data("SELECT es_sistema, nombre FROM pal_roles WHERE id = ?", (self.current_role_id,))
            if not row:
                return
            es_sistema, nombre = bool(row[0][0]), str(row[0][1])
            if es_sistema:
                messagebox.showwarning("No permitido", "No se puede eliminar un rol del sistema")
                return
            if not messagebox.askyesno("Confirmar", f"¿Eliminar rol '{nombre}'?"):
                return
            # Eliminar asignaciones y rol
            self.db_manager.execute_query("DELETE FROM pal_roles_permisos WHERE rol_id = ?", (self.current_role_id,))
            self.db_manager.execute_query("DELETE FROM pal_usuarios_roles WHERE rol_id = ?", (self.current_role_id,))
            self.db_manager.execute_query("DELETE FROM pal_roles WHERE id = ?", (self.current_role_id,))
            self.current_role_id = None
            self._reload_roles_list()
            self._new_role()
            messagebox.showinfo("Listo", "Rol eliminado")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar el rol: {e}")

    def _save_role_permissions(self):
        try:
            if not self.current_role_id:
                messagebox.showwarning("Error", "Selecciona o crea un rol antes de guardar permisos")
                return
            # Reemplazar conjunto de permisos del rol
            self.db_manager.execute_query("DELETE FROM pal_roles_permisos WHERE rol_id = ?", (self.current_role_id,))
            selected_perm_ids = [pid for pid, var in self.perm_vars_by_id.items() if var.get()]
            for pid in selected_perm_ids:
                self.db_manager.execute_query(
                    "IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = ? AND permiso_id = ?)\n"
                    "INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (?, ?)\n",
                    (self.current_role_id, pid, self.current_role_id, pid)
                )
            messagebox.showinfo("Listo", "Permisos del rol guardados")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron guardar permisos: {e}")

    def _reload_users_combo_for_assignment(self):
        try:
            rows = self.db_manager.fetch_data("SELECT id, username FROM pal_usuarios WHERE activo = 1 ORDER BY username") or []
            self.assign_users = [(int(r[0]), str(r[1])) for r in rows]
            self.assign_user_combo['values'] = [u[1] for u in self.assign_users]
            if self.assign_users:
                self.assign_user_combo.current(0)
                self._load_user_roles_selector()
        except Exception as e:
            self.log(f"Error cargando usuarios: {e}", "WARNING")

    def _load_user_roles_selector(self):
        try:
            # Clear existing
            for child in self.user_roles_frame.winfo_children():
                child.destroy()
            self.user_role_vars = {}
            sel_username = self.assign_user_combo.get()
            user_id = next((u[0] for u in getattr(self, 'assign_users', []) if u[1] == sel_username), None)
            if not user_id:
                return
            # Load roles and current assignments
            roles = self.db_manager.fetch_data("SELECT id, nombre FROM pal_roles ORDER BY nombre") or []
            assigned = self.db_manager.fetch_data("SELECT rol_id FROM pal_usuarios_roles WHERE usuario_id = ?", (user_id,)) or []
            assigned_set = {int(r[0]) for r in assigned}
            # Create checkboxes
            col = 0
            row = 0
            for rid, nombre in roles:
                var = tk.BooleanVar(value=int(rid) in assigned_set)
                cb = ttk.Checkbutton(self.user_roles_frame, text=str(nombre), variable=var)
                cb.grid(row=row, column=col, sticky="w", padx=6, pady=4)
                self.user_role_vars[int(rid)] = var
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
        except Exception as e:
            self.log(f"Error cargando roles de usuario: {e}", "WARNING")

    def _save_user_roles_assignment(self):
        try:
            sel_username = self.assign_user_combo.get()
            user_id = next((u[0] for u in getattr(self, 'assign_users', []) if u[1] == sel_username), None)
            if not user_id:
                messagebox.showwarning("Error", "Selecciona un usuario")
                return
            # Replace role set
            self.db_manager.execute_query("DELETE FROM pal_usuarios_roles WHERE usuario_id = ?", (user_id,))
            selected_role_ids = [rid for rid, var in self.user_role_vars.items() if var.get()]
            for rid in selected_role_ids:
                self.db_manager.execute_query(
                    "IF NOT EXISTS (SELECT 1 FROM pal_usuarios_roles WHERE usuario_id = ? AND rol_id = ?)\n"
                    "INSERT INTO pal_usuarios_roles (usuario_id, rol_id) VALUES (?, ?)\n",
                    (user_id, rid, user_id, rid)
                )
            # Limpiar cache permisos del usuario si el servicio está disponible
            try:
                if hasattr(self, 'permissions'):
                    self.permissions.limpiar_cache_usuario(user_id)
            except Exception:
                pass
            messagebox.showinfo("Listo", f"Roles de '{sel_username}' actualizados")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron guardar roles del usuario: {e}")
    
    def _save_modules_config(self):
        """Deprecated: módulos ahora se controlan por BD (pal_usuarios_modulos)."""
        pass

    # =========================
    # Auditoría (Fase 6)
    # =========================
    def _create_audit_tab(self, parent):
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Filtros
        filters = ttk.Frame(frame)
        filters.pack(fill=tk.X)
        ttk.Label(filters, text="Usuario:").pack(side=tk.LEFT)
        self.audit_user_combo = ttk.Combobox(filters, state="readonly", width=25)
        self.audit_user_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(filters, text="Recargar", command=self._reload_audit_logs).pack(side=tk.LEFT, padx=5)

        # Cargar usuarios para filtro
        try:
            rows = self.db_manager.fetch_data("SELECT id, username FROM pal_usuarios ORDER BY username") or []
            self.audit_users = [(int(r[0]), str(r[1])) for r in rows]
            self.audit_user_combo['values'] = [u[1] for u in self.audit_users]
        except Exception:
            self.audit_users = []

        # Tabla
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        cols = ("Fecha", "Usuario", "Acción", "Módulo", "Éxito", "IP", "Detalle")
        self.audit_tree = ttk.Treeview(table_frame, columns=cols, show='headings', height=12)
        
        # Configurar estilos de colores para filas intercaladas
        style = ttk.Style()
        style.configure('Treeview', rowheight=25)
        self.audit_tree.tag_configure('oddrow', background='#F0F0F0', foreground='#000000')
        self.audit_tree.tag_configure('evenrow', background='#FFFFFF', foreground='#000000')
        self.audit_tree.tag_configure('error_row', background='#FFE6E6', foreground='#CC0000')
        self.audit_tree.tag_configure('success_row', background='#E6F3E6', foreground='#006600')
        
        for c in cols:
            self.audit_tree.heading(c, text=c)
            self.audit_tree.column(c, width=120 if c != "Detalle" else 300, anchor='w')
        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.audit_tree.yview)
        self.audit_tree.configure(yscrollcommand=vsb.set)
        self.audit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._reload_audit_logs()

    def _reload_audit_logs(self):
        try:
            # Limpiar
            for item in self.audit_tree.get_children():
                self.audit_tree.delete(item)
            # Filtro de usuario
            sel_user = self.audit_user_combo.get() if hasattr(self, 'audit_user_combo') else ''
            user_id = next((u[0] for u in getattr(self, 'audit_users', []) if u[1] == sel_user), None)
            if user_id:
                query = (
                    "SELECT TOP 500 a.fecha, u.username, a.accion, a.modulo, a.exitoso, a.ip_address, a.detalle "
                    "FROM pal_auditoria_accesos a LEFT JOIN pal_usuarios u ON u.id = a.usuario_id "
                    "WHERE a.usuario_id = ? ORDER BY a.fecha DESC"
                )
                rows = self.db_manager.fetch_data(query, (user_id,)) or []
            else:
                query = (
                    "SELECT TOP 500 a.fecha, u.username, a.accion, a.modulo, a.exitoso, a.ip_address, a.detalle "
                    "FROM pal_auditoria_accesos a LEFT JOIN pal_usuarios u ON u.id = a.usuario_id "
                    "ORDER BY a.fecha DESC"
                )
                rows = self.db_manager.fetch_data(query) or []
            
            # Insertar filas con colores intercalados
            for idx, r in enumerate(rows):
                fecha, username, accion, modulo, exitoso, ip, detalle = r
                
                # Determinar tag de color
                # Prioridad: error_row > success_row > oddrow/evenrow
                tags = ()
                if not exitoso:  # Filas de error en rojo
                    tags = ('error_row',)
                elif exitoso:  # Filas de éxito en verde
                    tags = ('success_row',)
                else:  # Colores intercalados por defecto
                    tags = ('oddrow' if idx % 2 == 0 else 'evenrow',)
                
                self.audit_tree.insert("", tk.END, values=(
                    str(fecha), str(username or ''), str(accion or ''), str(modulo or ''),
                    'Sí' if bool(exitoso) else 'No', str(ip or ''), str(detalle or '')
                ), tags=tags)
        except Exception as e:
            try:
                self.log(f"Error cargando auditoría: {e}", "ERROR")
            except Exception:
                pass

    def _save_debug_config(self):
        try:
            flags = {k: v.get() for k, v in self.debug_vars.items()}
            save_debug_config(flags)
            # Actualizar flags en runtime
            self.debug_flags = flags
            self.tra_debug = flags.get('tra', False)
            self.stock_debug = flags.get('stock', False)
            try:
                setattr(self.db_manager, 'debug_enabled', flags.get('db', False))
            except Exception:
                pass
            self.log("Configuración de depuración guardada", "SUCCESS")
        except Exception as e:
            self.log(f"Error guardando depuración: {e}", "ERROR")

    def on_settings_close(self):
        try:
            if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
                self.settings_window.destroy()
        except Exception:
            pass
        finally:
            self.settings_window = None

    def connect_to_database(self):
        """Alias for connect_db to maintain compatibility"""
        self.show_settings()

    def _require_login(self) -> bool:
        try:
            if not self.auth:
                return False
            # Mostrar diálogo de login hasta éxito o cancelación
            from pal.ui.login import LoginDialog
            dlg = LoginDialog(self.root)
            self.root.wait_window(dlg.top)
            if not dlg.result:
                self.update_status('error', message="Login cancelado")
                return False
            username, password = dlg.result
            resp = self.auth.login(username, password, ip_address=None)
            if not resp.get('success'):
                from tkinter import messagebox
                messagebox.showerror("Login fallido", resp.get('message', 'Error'))
                return self._require_login()
            self.session_token = resp['token']
            self.current_user = resp['user']
            self.log(f"Sesión iniciada como {self.current_user['username']}", "INFO")
            return True
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Error durante login: {e}")
            return False

    def _reset_session_on_db_change(self):
        """Reset de sesión cuando se cambia de base de datos."""
        try:
            self.log("[DB CHANGE] Reseteando sesión...", "INFO")
            # Cerrar sesión actual
            if hasattr(self, 'session_token') and self.session_token and hasattr(self, 'auth'):
                try:
                    self.auth.logout(self.session_token)
                except Exception:
                    pass
            # Resetear variables de sesión
            self.session_token = None
            self.current_user = None
            self.auth = None
            self.permissions = None
            # Limpiar caché
            self.cached_ventas_tra = []
            self.cached_ventas_mbrp = []
            self.cached_alertas = []
            self.log("[DB CHANGE] Sesión reseteada correctamente", "SUCCESS")
        except Exception as e:
            self.log(f"[DB CHANGE] Error durante reset: {e}", "WARNING")

    def _ensure_security_schema_interactive(self):
        """Verifica tablas pal_* y ofrece crearlas si faltan."""
        try:
            missing = []
            try:
                missing = self.db_manager.check_security_schema()
            except Exception as e:
                self.log(f"No se pudo verificar esquema de seguridad: {e}", "ERROR")
                return

            if missing:
                from tkinter import messagebox
                msg = (
                    "¡Oh no!\n\n" 
                    "No existen las tablas necesarias para el funcionamiento normal:\n\n"
                    + "\n".join(f"• {t}" for t in missing)
                    + "\n\n¿Quieres crearlas ahora?"
                )
                if messagebox.askyesno("Crear tablas necesarias", msg):
                    try:
                        self.update_status('action', message="Creando tablas PAL...")
                        self.db_manager.ensure_security_tables()
                        self.update_status('connected')
                        messagebox.showinfo("Listo", "Tablas creadas correctamente.\n\nAhora inicia sesión con:\nUsuario: admin\nContraseña: 123")
                        self.log("Esquema pal_* creado/actualizado", "SUCCESS")
                    except Exception as e:
                        self.update_status('error', message=str(e))
                        messagebox.showerror(
                            "Error creando tablas",
                            f"No se pudieron crear las tablas necesarias.\n\nDetalle: {e}"
                        )
                        self.log(f"Error creando esquema pal_*: {e}", "ERROR")
        except Exception as e:
            self.log(f"Error en verificación de esquema: {e}", "ERROR")

    def connect_db(self):
        try:
            
            server = self.server_entry.get().strip()
            database = self.db_entry.get().strip()
            user = self.user_entry.get().strip()
            password = self.pwd_entry.get().strip()
            token = self.token_entry.get().strip()

            if not server:
                messagebox.showwarning("Error", "El campo Servidor es obligatorio")
                return
    
            if not password:
                password = self.cred_manager.get_temp_password() or ''
    
            if password:
                self.cred_manager.store_temp_password(password)

            # Detectar cambio de base de datos
            old_settings = self.load_connection_settings()
            db_changed = (
                old_settings and (
                    old_settings.get('server') != server or 
                    old_settings.get('database') != database or 
                    old_settings.get('user') != user
                )
            )
            
            if db_changed:
                self.log(f"[DB CHANGE] Cambio de BD: {old_settings.get('database')} → {database}", "INFO")
                self._reset_session_on_db_change()

            if self.db_manager.connect(server, database, user, password):
                self.save_connection_settings(server, database, user, token)
                self.update_status('connected', server=server, api_token=token)
                # Inicializar servicios de seguridad
                from pal.core.audit_db import AuditDB
                self.audit_db = AuditDB(self.db_manager)
                self.auth = AuthManager(self.db_manager)
                self._ensure_security_schema_interactive()
                # Requerir login
                if not self._require_login():
                    return
                self.settings_window.destroy()
                self.log("Conexión a BD exitosa", "SUCCESS")
                try:
                    if hasattr(self, 'audit_db'):
                        self.audit_db.log_action(accion='DB_CONNECTED', usuario_id=self.current_user['id'] if self.current_user else None, detalle=server, modulo='ADMIN')
                except Exception:
                    pass
                self.show_temp_notification("Conexión exitosa")
                self.search_records()
            
        except Exception as e:
            self.log(f"Error de conexión: {str(e)}", "ERROR")
            error_msg = str(e)
            self.audit_log.log_event(
            "DB_CONNECTION_ERROR",
            os.getlogin(),
            "FAILED",
            ErrorCode.DB_CONNECTION_FAILED
        )
            self.update_status('error', message=error_msg)
            try:
                if hasattr(self, 'audit_db'):
                    self.audit_db.log_action(
                        accion='DB_CONNECTION_ERROR', usuario_id=self.current_user['id'] if self.current_user else None, detalle=error_msg, exitoso=False, modulo='ADMIN')
            except Exception:
                pass
            self.show_temp_notification("Error de conexión", duration=5000)

    def create_connection_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Servidor:").grid(row=0, column=0, sticky="w")
        self.server_entry = ttk.Entry(frame)
        self.server_entry.grid(row=0, column=1, sticky="ew", pady=5)
        
        ttk.Label(frame, text="Base de Datos:").grid(row=1, column=0, sticky="w")
        self.db_entry = ttk.Entry(frame)
        self.db_entry.grid(row=1, column=1, sticky="ew", pady=5)
        
        ttk.Label(frame, text="Usuario:").grid(row=2, column=0, sticky="w")
        self.user_entry = ttk.Entry(frame)
        self.user_entry.grid(row=2, column=1, sticky="ew", pady=5)
        
        ttk.Label(frame, text="Contraseña:").grid(row=3, column=0, sticky="w")
        self.pwd_entry = ttk.Entry(frame, show="*")
        self.pwd_entry.grid(row=3, column=1, sticky="ew", pady=5)

        # Botones en la parte inferior
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20, sticky="e")
    
        ttk.Button(btn_frame, text="Guardar", 
            command=self.connect_db).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", 
            command=lambda: (self.settings_window.destroy() if self.settings_window else None)).pack(side=tk.RIGHT)
        
        # Cargar configuración existente
        settings = self.load_connection_settings()
        if settings:
            self.server_entry.insert(0, settings['server'])
            self.db_entry.insert(0, settings['database'])
            self.user_entry.insert(0, settings['user'])
    
    def update_status(self, status_type: str, message: str = "", server: str = "", api_token: Optional[str] = None):
        """Actualizar la barra de estado principal Y el dashboard"""
        status_config = {
            'connected': {
                'text': f"BD: Conectado" if server else "BD: Conectado",
                'color': "green",
                'dashboard_text': "Conectado ✓",
                'dashboard_color': "#10B981"
            },
            'error': {
                'text': f"Error: {message[:50]}..." if len(message) > 50 else f"Error: {message}",
                'color': "red",
                'dashboard_text': "Error ✗",
                'dashboard_color': "#EF4444"
            },
            'action': {
                'text': message,
                'color': "blue",
                'dashboard_text': "Procesando...",
                'dashboard_color': "#3B82F6"
            },
            'disconnected': {
                'text': "BD: Desconectado",
                'color': "orange",
                'dashboard_text': "Desconectado ✗",
                'dashboard_color': "#EF4444"
            }
        }
        
        config = status_config.get(status_type, {
            'text': "Estado desconocido", 
            'color': "gray",
            'dashboard_text': "Desconocido",
            'dashboard_color': "#6B7280"
        })
        
        # Actualizar footer status
        self.db_status.config(text=config['text'], foreground=config['color'])
        
        # Actualizar dashboard status (si existe)
        try:
            if hasattr(self, 'dashboard_connection_status'):
                self.dashboard_connection_status.config(
                    text=config['dashboard_text'], 
                    foreground=config['dashboard_color']
                )
        except Exception:
            pass  # Dashboard aún no está inicializado
        
        # Mantener estado API independiente
        if not hasattr(self, 'api_state'):
            self.api_state = "inactive"
    
        # Actualizar solo si hay cambio explícito
        if status_type == 'api_connected':
            self.api_state = "active"
            self.api_status.config(text="API: Lista", foreground="green")
        elif status_type == 'api_error':
            self.api_state = "error"
            self.api_status.config(text="API: Error", foreground="red")

        # Habilitar/Deshabilitar UI dependiente de BD
        try:
            if status_type == 'connected':
                self._set_ui_connected(True)
            elif status_type in ('disconnected', 'error'):
                self._set_ui_connected(False)
        except Exception:
            pass

    def show_temp_notification(self, message: str, duration: int = 3000):
        """Mostrar notificación temporal en la esquina inferior derecha"""
        notification = tk.Toplevel(self.root)
        notification.wm_overrideredirect(True)
        notification.geometry(f"300x60+{self.root.winfo_x()+700}+{self.root.winfo_y()+600}")
    
        ttk.Label(notification, text=message, wraplength=280).pack(pady=10)
        notification.after(duration, notification.destroy)
    
    def save_api_settings(self):
        try:
            new_token = self.token_entry.get().strip()
        # Si el usuario ingresó algo, se guarda el nuevo token; de lo contrario se conserva el anterior
            if new_token:
                self.cred_manager.store_whatsapp_token(new_token)
                self.show_temp_notification("Token guardado")
                self.cred_manager.store_whatsapp_token(new_token)
                # Actualizar estado inmediatamente
                self.update_status('connected', api_token=new_token)
            else:
                self.show_temp_notification("No se detectaron cambios en el token")
            self.settings_window.destroy()
        except Exception as e:
            self.notification_manager.show_error("Error", f"Error guardando token: {str(e)}")

    def create_api_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Token WhatsApp:").grid(row=0, column=0, sticky="w")
        self.token_entry = ttk.Entry(frame, show="*")
        self.token_entry.grid(row=0, column=1, sticky="ew", pady=5)

        # Botones
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=20, sticky="e")
    
        ttk.Button(btn_frame, text="Guardar", 
            command=self.save_api_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, 
          text="Cancelar", 
          command=lambda: (self.settings_window.destroy() if self.settings_window else None)).pack(side=tk.RIGHT)
        
        # Cargar token existente
        try:
            token = self.cred_manager.get_whatsapp_token()
            if token:
                self.token_entry.insert(0, token)
        except Exception as e:
            self.notification_manager.show_error("Error cargando token")

    def _splash_login_submit(self, username: str, password: str) -> tuple[bool, str]:
        """
        Validar credenciales desde el splash screen.
        Retorna (success: bool, message: str)
        """
        try:
            if not self.auth or not self.db_manager.conn:
                return False, "Base de datos no conectada"
            
            # Validar credenciales
            resp = self.auth.login(username, password, ip_address=None)
            if not resp.get('success'):
                try:
                    if hasattr(self, 'audit_db'):
                        self.audit_db.log_access(
                            accion='LOGIN', usuario_id=None, exitoso=False, detalle=f"user={username}"
                        )
                except Exception:
                    pass
                return False, resp.get('message', 'Credenciales inválidas')
            
            # Guardar sesión
            self.session_token = resp['token']
            self.current_user = resp['user']
            
            self.log(f"✅ Sesión iniciada como {username}", "SUCCESS")
            try:
                if hasattr(self, 'audit_db'):
                    self.audit_db.log_access(accion='LOGIN', usuario_id=self.current_user['id'], exitoso=True)
            except Exception:
                pass
            
            # Forzar cambio de contraseña si admin usó la predeterminada (en hilo principal)
            if username.lower() == 'admin' and password == '123':
                # Programar en hilo principal después de que la UI esté lista
                self.root.after(500, self._prompt_change_admin_password)
            
            # Verificar y crear esquema si es necesario
            try:
                missing = self.db_manager.check_security_schema()
                if missing:
                    self.db_manager.ensure_security_tables()
            except Exception as e:
                self.log(f"Nota: {e}", "INFO")
            
            # Cargar permisos del usuario y configurar UI
            from pal.core.permissions import PermissionsManager
            self.permissions = PermissionsManager(self.db_manager)
            user_id = self.current_user['id']
            db_mods = self.permissions.obtener_modulos_disponibles(user_id) or []
            
            # Mapear nombres de BD a flags de app
            flags_enabled = {DB_MODULE_TO_FLAG[m] for m in db_mods if m in DB_MODULE_TO_FLAG}
            
            # Actualizar módulos habilitados según permisos del usuario
            for flag in ['stock', 'tra', 'mbrp', 'envio_mensajes', 'calendario', 'estadisticas', 'admin']:
                self.modules_enabled[flag] = flag in flags_enabled
            
            self.log(f"Módulos disponibles: {', '.join(db_mods) or 'ninguno'}", "INFO")
            
            # Recrear workspace con módulos actualizados (importante para que aparezcan nuevas tabs)
            try:
                if hasattr(self, 'main_notebook') and self.main_notebook.winfo_exists():
                    self.main_notebook.destroy()
                self.create_main_workspace()
                # Cargar lista de registros al iniciar si la pestaña existe
                try:
                    if hasattr(self, 'search_records'):
                        self.search_records()
                except Exception:
                    pass
            except Exception as e:
                self.log(f"Error recreando workspace: {e}", "WARNING")
            
            # Inicializar módulos en segundo plano
            threading.Thread(target=self._inicializar_modulos_paralelo, daemon=True).start()
            
            return True, "Login exitoso"
            
        except Exception as e:
            self.log(f"Error en login: {e}", "ERROR")
            return False, f"Error: {str(e)[:50]}"
    
    def _prompt_change_admin_password(self):
        """
        Solicita cambio de contraseña para admin en el hilo principal.
        Ejecutado mediante root.after() para evitar problemas de threading.
        """
        try:
            while True:
                p1 = simpledialog.askstring(
                    "Cambiar contraseña", 
                    "Nueva contraseña para admin (dejado en blanco cancela):", 
                    show='*', 
                    parent=self.root
                )
                if p1 is None or p1 == '':
                    self.log("Cambio de contraseña cancelado", "INFO")
                    return
                
                p2 = simpledialog.askstring(
                    "Cambiar contraseña", 
                    "Confirmar contraseña:", 
                    show='*', 
                    parent=self.root
                )
                if p2 is None or p2 == '':
                    self.log("Cambio de contraseña cancelado", "INFO")
                    return
                
                if p1 != p2:
                    messagebox.showerror("Error", "Las contraseñas no coinciden. Intente nuevamente.")
                    continue
                
                if len(p1) < 4:
                    messagebox.showerror("Error", "La contraseña debe tener al menos 4 caracteres")
                    continue
                
                # Intentar actualizar contraseña
                if self.auth and self.current_user:
                    ok = self.auth.cambiar_password(self.current_user['id'], '123', p1)
                    if ok:
                        messagebox.showinfo("Éxito", "Contraseña actualizada exitosamente")
                        self.log("✅ Contraseña admin actualizada", "SUCCESS")
                        return
                    else:
                        messagebox.showerror("Error", "No se pudo actualizar la contraseña. Intente nuevamente.")
                        continue
                else:
                    messagebox.showerror("Error", "Sistema no listo para cambiar contraseña")
                    return
                    
        except Exception as e:
            self.log(f"Error en cambio de contraseña: {e}", "ERROR")
            messagebox.showerror("Error", f"Error al cambiar contraseña: {str(e)[:100]}")
    
    def _inicializar_modulos_paralelo(self):
        """
        Carga los módulos habilitados en segundo plano después del login.
        Se ejecuta en thread daemon para no bloquear la UI.
        """
        try:
            # Stock
            if self.modules_enabled.get("stock", False):
                self.log("📦 Inicializando Stock...", "INFO")
                self.root.after(100, lambda: self.actualizar_alertas_stock(force_refresh=True))
            
            # TRA
            if self.modules_enabled.get("tra", False):
                self.log("📈 Inicializando TRA...", "INFO")
                # Se cargarán bajo demanda en la pestaña
            
            # MBRP
            if self.modules_enabled.get("mbrp", False):
                self.log("📉 Inicializando MBRP...", "INFO")
                # Se cargarán bajo demanda en la pestaña
            
            # Habilitar UI dependiente
            self.root.after(200, lambda: self._set_ui_connected(True))
            self.log("✅ Módulos inicializados", "SUCCESS")
            
        except Exception as e:
            self.log(f"Error inicializando módulos: {e}", "ERROR")
    
    def logout(self):
        """Cierra la sesión actual y muestra pantalla de login."""
        try:
            # Cerrar sesión en BD
            if self.auth and self.session_token:
                self.auth.logout(self.session_token)
            
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_access(accion='LOGOUT', usuario_id=self.current_user['id'], exitoso=True)
            except Exception:
                pass
            
            self.session_token = None
            self.current_user = None
            self.permissions = None
            
            self.log("Sesión cerrada", "INFO")
            
            # Ocultar ventana principal
            self.root.withdraw()
            
            # Crear pantalla de login similar al splash
            self._show_login_screen()
            
        except Exception as e:
            from tkinter import messagebox
            self.log(f"Error durante logout: {e}", "ERROR")
            messagebox.showerror("Error", f"No se pudo cerrar sesión: {e}")
            self.root.deiconify()  # Mostrar ventana de nuevo en caso de error
    
    def _show_login_screen(self):
        """Muestra una pantalla de login independiente después de logout."""
        from pal.ui.splash import SplashScreen
        
        # Crear splash de login
        login_splash = SplashScreen(self.root)
        login_splash.title("Iniciar Sesión")
        
        # Configurar como pantalla de login (sin progreso ni loops)
        login_splash.progress.pack_forget()  # Ocultar barra de progreso
        login_splash.progress_value = 100  # Evitar que la animación se reinicie
        
        # Resetear eventos para que NO se cierre automáticamente
        login_splash.minimum_time_elapsed.clear()
        login_splash.app_initialized.clear()
        login_splash.login_success.clear()
        
        # Habilitar login inmediatamente
        def _handle_login(username, password):
            success, message = self._splash_login_submit(username, password)
            if success:
                # Marcar login exitoso y cerrar
                login_splash.login_success.set()
                login_splash.after(100, lambda: [
                    login_splash.destroy(),
                    self.root.deiconify()
                ])
            return success, message
        
        login_splash.enable_login(_handle_login)
        
        # Esperar cierre del splash
        self.root.wait_window(login_splash)
        
        # Si el usuario cerró la ventana sin hacer login, cerrar app
        if not self.current_user:
            self.log("Login cancelado - cerrando aplicación", "INFO")
            self.root.quit()

    class NotificationManager:
        def __init__(self, root):
            self.root = root
        
        def show_success(self, message):
            self._show_notification("✓ Éxito", message, "#d4edda")
        
        def show_error(self, message, details=None):
            # Support both old style (message only) and new style (message, details)
            if details:
                full_message = f"{message}: {details}"
            else:
                full_message = message
            self._show_notification("⚠ Error", full_message, "#f8d7da")
        
        def _show_notification(self, title, message, color):
            notification = tk.Toplevel(self.root)
            notification.wm_overrideredirect(True)
            notification.geometry(f"+{self.root.winfo_rootx()+self.root.winfo_width()-300}+{self.root.winfo_rooty()+50}")
        
            frame = ttk.Frame(notification, relief="solid", borderwidth=1)
            frame.pack(padx=10, pady=10)
        
            ttk.Label(frame, text=title, foreground="#155724", font=("Arial", 9, "bold")).pack()
            ttk.Label(frame, text=message).pack()
        
            notification.after(3000, notification.destroy)

    class HelpTooltips:
        def __init__(self, root):
            self.root = root
            self.tooltip_window = None
        
        def add_tooltip(self, widget, text):
            widget.bind("<Enter>", lambda e: self.show_tooltip(widget, text) or 0)  # Return 0 for WNDPROC
            widget.bind("<Leave>", lambda e: self.hide_tooltip() or 0)  # Return 0 for WNDPROC
        
        def show_tooltip(self, widget, text):
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
        
            self.tooltip_window = tk.Toplevel(widget)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
            label = ttk.Label(self.tooltip_window, text=text, background="#ffffe0",
                        relief="solid", borderwidth=1, padding=5)
            label.pack()
            return 0  # Return integer for WNDPROC
        
        def hide_tooltip(self):
            if self.tooltip_window:
                self.tooltip_window.destroy()
            return 0  # Return integer for WNDPROC



    def toggle_buttons(self, estado: str):
        """Habilitar/deshabilitar botones principales"""
        if not hasattr(self, 'buttons') or not self.buttons:
            return  # Prevenir error si no hay botones registrados
    
        for nombre, boton in self.buttons.items():
            try:
                boton.config(state=estado)
                # Cambiar color para mejor feedback visual
                boton.config(style="TButton" if estado == 'normal' else "Disabled.TButton")
            except Exception:
                pass

    def _set_ui_connected(self, connected: bool):
        """Habilita/deshabilita elementos de UI dependientes de BD y módulos."""
        if not hasattr(self, 'buttons'):
            self.buttons = {}
        # Reglas por módulo requerido
        required_module = {
            'btn_envio_masivo': 'envio_mensajes',
            'btn_programar_envio': 'envio_mensajes',
            'btn_export_csv': 'stock',
            'btn_stock_reload': 'stock',
            'btn_tra_cargar': 'tra',
            'btn_calendar_refresh': 'calendario',
            # CRUD registros no dependen de módulo, solo de BD
            'btn_buscar': None,
            'btn_guardar': None,
            'btn_actualizar': None,
            'btn_eliminar': None,
        }
        for key, btn in self.buttons.items():
            try:
                mod = required_module.get(key)
                enable = connected and (mod is None or self.modules_enabled.get(mod, False))
                btn.config(state='normal' if enable else 'disabled')
                btn.config(style='TButton' if enable else 'Disabled.TButton')
            except Exception:
                continue

        

    def toggle_password(self):
        if self.show_pwd_var.get():
            self.pwd_entry.config(show="")
        else:
            self.pwd_entry.config(show="*")

    def save_connection_settings(self, server: str, database: str, user: str, token: str = None):
        """Guarda la configuración en el archivo .ini"""
        try:
            config = configparser.ConfigParser()
            
            # Si existe el archivo, cargamos su contenido primero
            if os.path.exists(CONFIG_FILE):
                config.read(CONFIG_FILE)
            
            # Crear sección si no existe
            if 'Database' not in config:
                config.add_section('Database')
                
            # Actualizar valores
            config['Database']['server'] = self.cred_manager.encrypt(server)
            config['Database']['database'] = self.cred_manager.encrypt(database)
            config['Database']['user'] = self.cred_manager.encrypt(user)
            
            # Escribir archivo
            with open(CONFIG_FILE, 'w') as configfile:
                config.write(configfile)
            
            # Guardar token si existe
            if token:
                self.cred_manager.store_whatsapp_token(token)
                
            self.show_temp_notification("Configuración guardada ✅")
            
        except Exception as e:
            self.audit_log.log_event(
                "SAVE_CONFIG_FAILED",
                os.getlogin(),
                "FAILED",
                ErrorCode.INVALID_CONFIG
            )
            try:
                if hasattr(self, 'audit_db'):
                    self.audit_db.log_action(
                        accion='SAVE_CONFIG_FAILED', usuario_id=self.current_user['id'] if self.current_user else None, modulo='ADMIN', detalle=str(e), exitoso=False)
            except Exception:
                pass
            messagebox.showerror("Error", f"No se pudo guardar: {str(e)}")
    
    def validate_input(self):
        num = self.num_cliente.get().strip()
        cod = self.cod_producto.get().strip()
        inputs = {
            "Numero": num,
            "Codigo": cod
        }

        if not num or not cod:
            self.audit_log.log_event(
                "VALIDATION_ERROR", os.getlogin(), "FAILED", 
                ErrorCode.INVALID_CLIENT_NUMBER
            )
            messagebox.showwarning("Error", "Complete todos los campos")

            return False

        #Validar formato numerico

        if not re.match(r'^\d{1,11}$', num):
            self.audit_log.log_event(
                "INVALID_CLIENT_NUMBER", os.getlogin(), "FAILED",
                ErrorCode.INVALID_CLIENT_NUMBER
            )
            messagebox.showwarning("Error", str(ErrorCode.INVALID_CLIENT_NUMBER))
            return False
        
        dangerous_patterns = [r";.*--", r"/\*.*\*/", r"xp_", r"exec\(", r"union.*select"]
        for field, value in inputs.items():
            if any(re.search(pattern, value, re.IGNORECASE) for pattern in dangerous_patterns):
                self.audit_log.log_event(
                    f"DANGEROUS_INPUT_{field}", os.getlogin(), "FAILED",
                    ErrorCode.DANGEROUS_INPUT
                )
                self.notification_manager.show_warning("Error", str(ErrorCode.DANGEROUS_INPUT))
                return False
              
        return True 

    def clear_inputs(self):
        self.num_cliente.delete(0, tk.END)
        self.cod_producto.delete(0, tk.END)
        self.actualizar_descripcion("")

    def save_record(self):
        if not self.validate_input():
            return

        try:
            self.db_manager.execute_query(
                "INSERT INTO pal_clientes (numero_cliente, C_CODIGO) VALUES (?, ?)",
                (self.num_cliente.get(), self.cod_producto.get())
            )
            
            self.show_temp_notification("¡Guardado exitosamente!")
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_action(
                        accion='RECORD_CREATE', usuario_id=self.current_user['id'], modulo='REGISTROS', 
                        detalle=f"numero={self.num_cliente.get()} codigo={self.cod_producto.get()}")
            except Exception:
                pass

            # Restablecer el estado a 'Conectado' después de 3 segundos
            self.root.after(3000, lambda: self.update_status('connected'))

            self.search_records()
            self.clear_inputs()
        except Exception as e:
            self.notification_manager.show_success("Error", str(e))
            self.show_temp_notification("Error al guardar", duration=5000)
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_action(
                        accion='RECORD_CREATE', usuario_id=self.current_user['id'], modulo='REGISTROS', detalle=str(e), exitoso=False)
            except Exception:
                pass

    def search_records(self):
        # PRIMERO: Verificar que el módulo MENSAJES esté habilitado (donde está REGISTROS)
        # Si no está habilitado, retornar silenciosamente (no es un error del usuario)
        if not self.modules_enabled.get("envio_mensajes", False):
            return
        
        if not self.db_manager.conn:
            self.notification_manager.show_error("Error", "No hay conexión a la base de datos")
            self.show_settings()
            return
        
        # Validar que el widget tree exista y sea accesible
        if not hasattr(self, 'tree') or not self.tree or not self.tree.winfo_exists():
            return
        
        try:
            self.tree.delete(*self.tree.get_children())
            num = self.num_cliente.get().strip()
            cod = self.cod_producto.get().strip()

            query = "SELECT id, numero_cliente, C_CODIGO FROM pal_clientes"
            conditions = []
            params = []
            
            if num:
                conditions.append("numero_cliente LIKE ?")
                params.append(f"%{num}%")
            
            if cod:
                conditions.append("C_CODIGO LIKE ?")
                params.append(f"%{cod}%")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            records = self.db_manager.fetch_data(query, params)
            for row in records:
                self.tree.insert("", tk.END, values=row)
                            
            
                
        except Exception as e:
            self.notification_manager.show_error("Error", str(e))
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_action(
                        accion='RECORD_SEARCH_ERROR', usuario_id=self.current_user['id'], modulo='REGISTROS', detalle=str(e), exitoso=False)
            except Exception:
                pass

    def enviar_a_todos(self):
        self.log("Iniciando proceso de envío masivo...", "INFO")
        if self.enviando: return
        self.toggle_buttons('disabled')
            
    
        try:
            records = self.db_manager.fetch_data("SELECT numero_cliente, C_CODIGO FROM pal_clientes")
            
            # Agrupar clientes
            clientes_con_error = set()

            clientes_dict = {}
            for numero, codigo in records:
                if numero not in clientes_dict:
                    clientes_dict[numero] = []
                clientes_dict[numero].append(codigo)
        
            self.log(f"Enviando a {numero}", "DEBUG")
            self.clientes_lista = list(clientes_dict.items())
            self.total = len(self.clientes_lista)
        
            if not self.clientes_lista:
                messagebox.showinfo("Info", "No hay clientes para notificar")
                return

            self.actual = 0
            self.enviando = True
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_action(
                        accion='MSG_MASS_START', usuario_id=self.current_user['id'], modulo='MENSAJES')
            except Exception:
                pass
        
            # Configurar UI de progreso
            self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
            self.progress.pack(pady=10)
            self.lbl_progreso = ttk.Label(self.root, text="Preparando...")
            self.lbl_progreso.pack()
            self.progress["maximum"] = self.total

            self.root.after(1000, self.procesar_envio_masivo)
            
        except Exception as e:
            self.log(f"Error en envío masivo: {str(e)}", "ERROR")
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_action(
                        accion='MSG_MASS_ERROR', usuario_id=self.current_user['id'], modulo='MENSAJES', detalle=str(e), exitoso=False)
            except Exception:
                pass
            self.toggle_buttons('normal')
            messagebox.showerror("Error", f"Error obteniendo clientes: {str(e)}")
            self.enviando = False
        
        
        
        
        
    def _background_load_alertas_stock(self):
        """Carga todas las alertas en segundo plano, en bloques, y refresca UI al llegar datos.
        Usa chunks adaptativos para optimizar latencia y rendimiento.
        Soporta múltiples depósitos seleccionados.
        """
        from pal.core.chunks import AdaptiveChunkController
        total_loaded = 0
        chunk_count = 0
        load_start_time = time.perf_counter()
        
        try:
            # Obtener depósitos seleccionados o usar valor por defecto
            depositos = getattr(self, 'stock_depositos_seleccionados', ['0301'])
            if not depositos:
                depositos = ['0301']
            
            self.stock_debug_log(f"Cargando alertas para depósitos: {', '.join(depositos)}")
            
            start = 1
            controller = AdaptiveChunkController(initial=500, min_size=100, max_size=2000, target_latency=2.0)
            # Usar dict para evitar duplicados por código
            existentes = {r[0]: r for r in (self.cached_alertas or [])}
            initial_count = len(existentes)
            
            self.stock_debug_log(f"Iniciando carga paralela de stock con {initial_count} registros existentes")
            
            consecutive_failures = 0
            max_consecutive_failures = 3
            
            while True:
                chunk_size = controller.size
                chunk_start_time = time.perf_counter()
                # Usar función para múltiples depósitos
                rows = self.db_manager.obtener_alertas_stock_multiples(start_row=start, fetch_size=chunk_size, depositos=depositos)
                chunk_query_time = time.perf_counter() - chunk_start_time
                
                if not rows:
                    consecutive_failures += 1
                    self.stock_debug_log(f"Chunk {chunk_count + 1}: Sin datos (fallo {consecutive_failures}/{max_consecutive_failures}) - consulta en {chunk_query_time:.2f}s")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        self.stock_debug_log(f"Deteniendo carga tras {consecutive_failures} fallos consecutivos")
                        break
                    
                    # Incrementar start para saltar posibles huecos
                    start += chunk_size
                    time.sleep(1)  # Pausa más larga tras error
                    continue
                else:
                    consecutive_failures = 0  # Reset counter on success
                
                chunk_count += 1
                new_records = 0
                duplicates = 0
                
                for r in rows:
                    codigo_str = str(r[0])
                    if codigo_str in existentes:
                        duplicates += 1
                    else:
                        new_records += 1
                    existentes[codigo_str] = r
                
                self.cached_alertas = list(existentes.values())
                total_loaded += len(rows)
                
                # Log detallado del chunk
                chunk_time = time.perf_counter() - chunk_start_time
                total_time = time.perf_counter() - load_start_time
                records_per_sec = total_loaded / total_time if total_time > 0 else 0
                
                self.stock_debug_log(
                    f"Chunk {chunk_count}: {len(rows)} filas | "
                    f"Nuevos: {new_records} | Duplicados: {duplicates} | "
                    f"Total acum: {len(existentes)} | "
                    f"Tiempo: {chunk_time:.2f}s | "
                    f"Velocidad: {records_per_sec:.1f} reg/s"
                )
                
                # Refrescar vista en hilo principal cada 3 chunks o al final
                if chunk_count % 3 == 0 or len(rows) < chunk_size:
                    try:
                        self.root.after(0, self._update_ui_after_chunk, len(existentes), chunk_count)
                    except Exception as e:
                        self.stock_debug_log(f"Error actualizando UI: {e}")
                
                # Avanzar ventana
                start += len(rows)
                
                # Ajuste adaptativo del tamaño del próximo chunk
                controller.update(chunk_query_time, len(rows))
                
                # Pausa adaptativa breve
                time.sleep(controller.recommend_sleep(chunk_query_time))
                
                # Si el chunk es menor que el tamaño esperado, probablemente sea el último
                if len(rows) < chunk_size:
                    self.stock_debug_log(f"Último chunk detectado ({len(rows)} < {chunk_size})")
                    break
            
            # Estadísticas finales
            total_time = time.perf_counter() - load_start_time
            avg_time_per_chunk = total_time / chunk_count if chunk_count > 0 else 0
            final_count = len(existentes)
            net_new = final_count - initial_count
            
            # Verificar si la carga fue exitosa
            if final_count < 1000:  # Menos de 1000 registros indica problema
                self.log(
                    f"Carga incompleta detectada: solo {final_count} registros. Reintentando en 30 segundos...",
                    "WARNING"
                )
                # Programar reintento automático
                threading.Timer(30.0, self._retry_stock_loading).start()
            else:
                self.log(
                    f"✅ [DEBUG] Carga paralela completada: "
                    f"{chunk_count} chunks | "
                    f"{final_count} registros totales | "
                    f"{net_new} nuevos | "
                    f"Tiempo total: {total_time:.2f}s | "
                    f"Promedio/chunk: {avg_time_per_chunk:.2f}s", 
                    "SUCCESS"
                )
            
            # Actualización final de UI
            try:
                self.root.after(0, self._finalize_stock_loading, final_count)
            except Exception as e:
                self.log(f"Error en actualización final: {e}", "ERROR")
            
        except Exception as e:
            self.log(f"❌ [DEBUG] Error en carga paralela de alertas: {e}", "ERROR")
            # Log adicional para debugging
            import traceback
            self.log(f"❌ [DEBUG] Traceback: {traceback.format_exc()}", "ERROR")
    
    def _update_ui_after_chunk(self, total_records, chunk_number):
        """Actualiza la UI después de cargar un chunk de datos"""
        try:
            # Evitar errores si la UI fue destruida
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                return
            if not hasattr(self, 'stock_tree') or not self.stock_tree or not self.stock_tree.winfo_exists():
                return
            # Actualizar filtros si es necesario
            self.aplicar_filtro_stock()
            
            # Log de progreso en UI
            estimated_pages = math.ceil(total_records / self.page_size)
            self.log(f"📈 [UI] Chunk {chunk_number}: {total_records} registros | ~{estimated_pages} páginas estimadas", "DEBUG")
            
        except Exception as e:
            self.log(f"Error actualizando UI después del chunk: {e}", "ERROR")
    
    def _finalize_stock_loading(self, final_count):
        """Finaliza el proceso de carga de stock y actualiza estadísticas finales"""
        try:
            # Aplicar filtros finales
            self.aplicar_filtro_stock()
            
            # Calcular páginas totales
            total_pages = math.ceil(final_count / self.page_size)
            
            # Log final con estadísticas
            self.log(
                f"🏆 [FINAL] Carga completa: {final_count} registros | "
                f"{total_pages} páginas totales | "
                f"Tamaño de página: {self.page_size}", 
                "SUCCESS"
            )
            
            # Actualizar controles de paginación si existen
            if hasattr(self, 'pagination_label'):
                current_total_pages = math.ceil(len(self.cached_alertas) / self.page_size)
                self.pagination_label.config(text=f"Página {self.current_page}/{current_total_pages}")
            
        except Exception as e:
            self.log(f"Error finalizando carga de stock: {e}", "ERROR")
    
    def _get_total_stock_count(self):
        """Obtiene el total de registros de alertas disponibles en la BD para debug"""
        try:
            query = """
                SELECT COUNT(*) as total
                FROM (
                    SELECT c_codarticulo
                    FROM MA_DEPOPROD d
                        INNER JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.C_CODIGO
                        WHERE c_coddeposito = '0301'
                        GROUP BY c_codarticulo
                        HAVING SUM(n_cantidad) < 21
                ) as subquery
            """
            result = self.db_manager.fetch_data(query)
            return result[0][0] if result and result[0] else 0
        except Exception as e:
            self.log(f"Error obteniendo total de registros: {e}", "ERROR")
            return 0
    
    def _retry_stock_loading(self):
        """Reintenta la carga de stock automáticamente tras un fallo"""
        try:
            self.log("🔄 [AUTO-RETRY] Reintentando carga de stock automáticamente...", "INFO")
            
            # Resetear estado para permitir nueva carga
            self.stock_full_loading_started = False
            
            # Limpiar datos parciales
            if len(self.cached_alertas) < 1000:
                self.cached_alertas = []
            
            # Forzar recarga
            self.actualizar_alertas_stock(force_refresh=True)
            
        except Exception as e:
            self.log(f"❌ [AUTO-RETRY] Error en reintento automático: {e}", "ERROR")
    
    def _background_load_ventas_tra(self):
        """Carga todas las ventas TRA en segundo plano, de forma incremental y con chunk adaptativo.
        Realiza actualizaciones mínimas de UI mediante root.after para mantener la app responsiva.
        """
        try:
            if not hasattr(self, 'tra_fecha_inicio') or not hasattr(self, 'tra_fecha_fin') or not hasattr(self, 'tra_sede_codigo'):
                self.log("Faltan parámetros para carga TRA, cancelando carga paralela", "WARNING")
                return

            # Parámetros de chunk adaptativo
            chunk_size = 1000
            min_chunk = 200
            max_chunk = 5000
            target_ms = 150.0

            # Acumulador de neto escaneado para debug
            total_neto_scaneado = 0.0

            start = 1
            processed = 0
            ui_last_refreshed_at = 0
            chunk_index = 0
            first_refresh_done = False

            # Garantizar contenedor de datos
            if not hasattr(self, 'cached_ventas_tra') or self.cached_ventas_tra is None:
                self.cached_ventas_tra = []
            # Conjunto para evitar duplicados por código
            try:
                seen_codes = set(str(r[0]) for r in self.cached_ventas_tra)
            except Exception:
                seen_codes = set()

            self.tra_debug_log("Iniciando carga completa de datos TRA en background (adaptativa)...")

            while True:
                t0 = time.perf_counter()
                rows = self.db_manager.obtener_ventas_por_producto_chunk(
                    fecha_inicio=self.tra_fecha_inicio,
                    fecha_fin=self.tra_fecha_fin,
                    sede_codigo=self.tra_sede_codigo,
                    start_row=start,
                    fetch_size=int(chunk_size)
                )
                dt_ms = (time.perf_counter() - t0) * 1000.0

                if not rows:
                    break

                # Agregar filas sin clasificar (6 campos), evitando duplicados por código
                try:
                    nuevos = []
                    sum_neto_nuevos = 0.0
                    for r in rows:
                        try:
                            cod = str(r[0])
                        except Exception:
                            cod = None
                        if not cod or cod in seen_codes:
                            continue
                        seen_codes.add(cod)
                        nuevos.append(r)
                        # Sumar neto solo de nuevos registros
                        try:
                            sum_neto_nuevos += float(r[5] or 0)
                        except Exception:
                            pass
                    if nuevos:
                        self.cached_ventas_tra.extend(nuevos)
                        total_neto_scaneado += sum_neto_nuevos
                except Exception:
                    # Si falla por concurrencia (raro), recrear lista con filtro de duplicados
                    cleaned = []
                    sum_neto_cleaned = 0.0
                    for r in rows:
                        try:
                            cod = str(r[0])
                        except Exception:
                            cod = None
                        if not cod or cod in seen_codes:
                            continue
                        seen_codes.add(cod)
                        cleaned.append(r)
                        try:
                            sum_neto_cleaned += float(r[5] or 0)
                        except Exception:
                            pass
                    self.cached_ventas_tra = list(self.cached_ventas_tra) + cleaned
                    total_neto_scaneado += sum_neto_cleaned

                processed += len(rows)
                chunk_index += 1
                start += int(chunk_size)

                # Ajustar chunk de forma proporcional, limitado a rangos
                try:
                    factor = target_ms / max(1.0, dt_ms)
                    factor = max(0.5, min(2.0, factor))
                    chunk_size = int(max(min_chunk, min(max_chunk, chunk_size * factor)))
                except Exception:
                    pass

                # Actualización mínima de UI: siempre al primer chunk, luego cada ~3000 filas
                def _ui_update_slim(total=processed, last= len(rows), next_size=int(chunk_size)):
                    try:
                        self.tra_debug_log(f"+{last} (total {total}) en {dt_ms:.0f}ms, next_chunk={next_size}")
                        # Actualizar estado textual
                        try:
                            self.api_status.config(text=f"Cargando TRA: {total} filas...", foreground="#004C97")
                        except Exception:
                            pass
                        # Primer chunk: refrescar vistas para feedback temprano
                        nonlocal first_refresh_done
                        if not first_refresh_done:
                            first_refresh_done = True
                            self.aplicar_filtro_tra()
                        else:
                            # Refrescar de forma más espaciada
                            if total - _ui_update_slim.last_shown >= 3000:
                                _ui_update_slim.last_shown = total
                                self.aplicar_filtro_tra()
                    except Exception:
                        pass
                # stateful attr on function
                if not hasattr(_ui_update_slim, 'last_shown'):
                    _ui_update_slim.last_shown = 0
                self.root.after(0, _ui_update_slim)

                # Pequeña pausa cooperativa (evitar saturar BD/CPU)
                time.sleep(0.05)

            # Clasificación de rotación al finalizar (fuera de UI)
            if self.cached_ventas_tra:
                try:
                    from pal.services.tra import clasificar_rotacion
                    raw_snapshot = list(self.cached_ventas_tra)
                    self.tra_debug_log(f"Clasificando rotación para {len(raw_snapshot)} registros...")
                    classified = clasificar_rotacion(raw_snapshot)
                    self.cached_ventas_tra = classified
                except Exception as e:
                    self.log(f"Error clasificando rotación TRA: {e}", "ERROR")

            # Guardar total de neto escaneado en atributo para inspección/debug
            try:
                self.tra_total_neto_scaneado = float(total_neto_scaneado)
            except Exception:
                self.tra_total_neto_scaneado = 0.0

            def _ui_finish(total=len(self.cached_ventas_tra) if self.cached_ventas_tra else 0, neto=self.tra_total_neto_scaneado, scanned=processed):
                try:
                    self.aplicar_filtro_tra()
                    # Log de cierre con resumen de escaneo
                    self.tra_debug_log(f"TRA: Escaneadas {scanned} filas | Neto total escaneado: {neto:.2f}")
                    self.log(f"Carga paralela de ventas TRA completada: {total} registros | Neto total escaneado: {neto:.2f}", "SUCCESS")
                    try:
                        self.api_status.config(text="API: Lista", foreground="green")
                    except Exception:
                        pass
                    try:
                        self.global_progress.stop()
                        self.global_progress.pack_forget()
                    except Exception:
                        pass
                except Exception:
                    pass
            self.root.after(0, _ui_finish)
        except Exception as e:
            self.log(f"Error en carga paralela de ventas TRA: {e}", "ERROR")
            try:
                self.root.after(0, lambda: (self.global_progress.stop(), self.global_progress.pack_forget()))
            except Exception:
                pass
    def delete_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Error", "Seleccione un registro para eliminar")
            return

        if messagebox.askyesno("Confirmar", "¿Está seguro de eliminar este registro?"):
            try:
 
                record_id_raw = self.tree.item(selected[0])['values'][0]
                print(f"Valor obtenido del Treeview: {record_id_raw} - Tipo: {type(record_id_raw)}")

                

                record_id_clean = re.sub(r"[^\d]", "", str(record_id_raw))  # Elimina todo excepto números

                if not record_id_clean.isdigit():

                   raise ValueError(f"El ID no es un número válido: {record_id_raw}")

                record_id = int(record_id_clean)  # Convertimos a entero limpio
                print(f"ID después de limpieza: {record_id}")

                self.audit_log.log_event(
                    action=f"DELETE_ID:{record_id}",
                    user=os.getlogin(),
                    status="SUCCESS" 
                )

                # Restablecer el estado a 'Conectado' después de 3 segundos
                self.root.after(3000, lambda: self.update_status('connected'))

                self.db_manager.execute_query("DELETE FROM pal_clientes WHERE id = ?", (record_id,))
                self.update_status('action', message="Registro eliminado")
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='RECORD_DELETE', usuario_id=self.current_user['id'], modulo='REGISTROS', detalle=f"id={record_id}")
                except Exception:
                    pass
                self.search_records()
                self.clear_inputs() 
            except Exception as e:
                messagebox.showerror("Error", str(e))
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='RECORD_DELETE', usuario_id=self.current_user['id'], modulo='REGISTROS', detalle=str(e), exitoso=False)
                except Exception:
                    pass

    def crear_botones_masivos(self):
        frame_masivo = ttk.Frame(self.root)
        frame_masivo.pack(pady=10)
    
        self.btn_masivo = ttk.Button(frame_masivo, 
                               text="▶ Iniciar envío masivo", 
                               command=self.toggle_envio_masivo)
        self.btn_masivo.pack(side=tk.LEFT, padx=5)
    
        self.lbl_progreso = ttk.Label(frame_masivo, text="Envíos: 0/0")
        self.lbl_progreso.pack(side=tk.LEFT, padx=5)
    
        self.progress = ttk.Progressbar(frame_masivo, 
                                  orient=tk.HORIZONTAL, 
                                  length=200, 
                                  mode='determinate')

    def update_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Error", "Seleccione un registro para actualizar")
            return

        if not self.validate_input():
            return

        try:
            record_id_raw = self.tree.item(selected[0])['values'][0]
            print(f"valor obtenido del Treeview: {record_id_raw} - Tipo: {type(record_id_raw)}")

            record_id_clean = re.sub(r"[^\d]", "", str(record_id_raw))  # Elimina todo excepto números
            
            if not record_id_clean.isdigit():
                raise ValueError(f"El ID no es un número válido: {record_id_raw}")
            
            record_id = int(record_id_clean)  # Convertimos a entero limpio
            print(f"ID después de limpieza: {record_id}")
        

            self.db_manager.execute_query(
                "UPDATE pal_clientes SET numero_cliente = ?, C_CODIGO = ? WHERE id = ?",
                (self.num_cliente.get(), self.cod_producto.get(), record_id)
            )
            self.update_status('action', message="Registro actualizado")
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_action(
                        accion='RECORD_UPDATE', usuario_id=self.current_user['id'], modulo='REGISTROS', 
                        detalle=f"id={record_id}")
            except Exception:
                pass

            # Restablecer el estado a 'Conectado' después de 3 segundos
            self.root.after(3000, lambda: self.update_status('connected'))

            self.search_records()
            self.clear_inputs()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_action(
                        accion='RECORD_UPDATE', usuario_id=self.current_user['id'], modulo='REGISTROS', detalle=str(e), exitoso=False)
            except Exception:
                pass

    def buscar_descripcion(self, event=None):
        """Obtiene la descripción y actualiza el campo correspondiente"""
        # Ensure return value for WNDPROC
        codigo = self.cod_producto.get().strip()
        clean_codigo = re.sub(r'\D', '', codigo)  # Limpieza del código
    
        try:
            if not clean_codigo:
                self.actualizar_descripcion("Código no ingresado")
                return
            # Actualizar campo de código con versión limpia
            if clean_codigo != codigo:
                self.cod_producto.delete(0, tk.END)
                self.cod_producto.insert(0, clean_codigo)
        
            # Usar método reutilizable
            descripcion = self.obtener_descripcion_producto(clean_codigo)
            if descripcion:
                self.actualizar_descripcion(descripcion)
                print(f"Descripción: {descripcion}")
            else:
                self.actualizar_descripcion("Descripción no encontrada")

            # Validar stock usando el método reutilizable
            if self.validar_stock_producto(clean_codigo):
                stock_result = self.db_manager.fetch_data(
                    "SELECT n_cantidad FROM MA_DEPOPROD WHERE c_codarticulo = ? AND c_coddeposito = '0301'",
                    (clean_codigo,)
                )
                cantidad = int(stock_result[0][0]) if stock_result else 0
                self.show_temp_notification(f"Stock disponible: {cantidad} unidades ✅")
            else:
                self.show_temp_notification("No disponible o igual a 0 ❌")
            
        except Exception as e:
            self.actualizar_descripcion("Error en consulta")
            messagebox.showerror("Error", f"Error obteniendo datos: {str(e)}")
        return 0  # Return integer for WNDPROC
    
                       
    def _records_on_click(self, event):
        """Selecciona fila en el Treeview de Registros con un solo click"""
        try:
            if not hasattr(self, 'tree') or not self.tree or not self.tree.winfo_exists():
                return 0
            region = self.tree.identify_region(event.x, event.y)
            if region in ('cell', 'tree'):
                item = self.tree.identify_row(event.y)
                if item:
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    self.tree.see(item)
        except Exception:
            pass
        return 0

    def on_tree_double_click(self, event):
        """Manejo de doble click en la tabla con limpieza de datos"""
        # Return 0 at end for WNDPROC
        selected = self.tree.selection()
        if selected:
            try:
                # Obtener y limpiar datos del registro seleccionado
                values = self.tree.item(selected[0])['values']
                
                # Limpiar número de cliente
                clean_numero = re.sub(r'\D', '', str(values[1]))
                self.num_cliente.delete(0, tk.END)
                self.num_cliente.insert(0, clean_numero)
                
                # Limpiar código de producto
                clean_codigo = re.sub(r'\D', '', str(values[2]))
                self.cod_producto.delete(0, tk.END)
                self.cod_producto.insert(0, clean_codigo)
                
                # Actualizar descripción automáticamente
                self.buscar_descripcion()
                
            except IndexError:
                messagebox.showerror("Error", "El registro seleccionado es inválido")
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar datos: {str(e)}")
        return 0  # Return integer for WNDPROC
    

    def mostrar_ventana_programacion(self):
        try:
            win = tk.Toplevel(self.root)
            win.title("Programar Envío")
            win.transient(self.root)
            win.grab_set()
            win.resizable(False, False)
            frm = ttk.Frame(win, padding=10)
            frm.pack(fill=tk.BOTH, expand=True)

            # Número de cliente
            ttk.Label(frm, text="Número Cliente:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
            num_entry = ttk.Entry(frm, width=20)
            num_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)

            # Fecha (Calendar) + Hora/Minuto (Spinbox)
            ttk.Label(frm, text="Fecha:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
            from tkcalendar import Calendar
            from datetime import datetime, timedelta
            default_date = datetime.now() + timedelta(minutes=2)
            cal = Calendar(frm, selectmode='day', year=default_date.year, month=default_date.month, day=default_date.day)
            cal.grid(row=1, column=1, sticky='w', padx=5, pady=5)

            ttk.Label(frm, text="Hora:").grid(row=1, column=2, sticky='e', padx=(15,5))
            spin_hora = ttk.Spinbox(frm, from_=0, to=23, width=4)
            spin_hora.insert(0, f"{default_date.hour:02d}")
            spin_hora.grid(row=1, column=3, sticky='w')
            ttk.Label(frm, text=":").grid(row=1, column=4, sticky='w')
            spin_minuto = ttk.Spinbox(frm, from_=0, to=59, width=4)
            spin_minuto.insert(0, f"{default_date.minute:02d}")
            spin_minuto.grid(row=1, column=5, sticky='w', padx=(0,5))

            # Tipo de envío
            ttk.Label(frm, text="Tipo:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
            tipo_var = tk.StringVar(value='DISPONIBILIDAD')
            tipo_combo = ttk.Combobox(frm, textvariable=tipo_var, values=['DISPONIBILIDAD', 'ENTREGA'], state='readonly', width=18)
            tipo_combo.grid(row=2, column=1, sticky='w', padx=5, pady=5)

            # Código de producto (solo para DISPONIBILIDAD)
            ttk.Label(frm, text="Código Producto:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
            cod_entry = ttk.Entry(frm, width=20)
            cod_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)

            def _toggle_codigo(*args):
                if tipo_var.get() == 'DISPONIBILIDAD':
                    cod_entry.config(state='normal')
                else:
                    cod_entry.delete(0, tk.END)
                    cod_entry.config(state='disabled')
            try:
                tipo_var.trace_add('write', lambda *a: _toggle_codigo())
            except Exception:
                pass
            _toggle_codigo()

            def confirmar():
                from datetime import datetime
                numero = num_entry.get().strip()
                if not numero:
                    messagebox.showwarning("Error", "Ingrese el número de cliente")
                    return
                try:
                    # Obtener fecha del Calendar de forma robusta
                    try:
                        d = cal.selection_get()  # datetime.date
                    except Exception:
                        d = cal.get_date()
                        d = datetime.fromisoformat(str(d)).date()
                    h = int(spin_hora.get() or 0)
                    m = int(spin_minuto.get() or 0)
                    if not (0 <= h <= 23 and 0 <= m <= 59):
                        raise ValueError
                    fecha = datetime(d.year, d.month, d.day, h, m)
                except Exception:
                    messagebox.showwarning("Error", "Fecha/Hora inválida")
                    return

                tipo = tipo_var.get().strip().upper() or 'DISPONIBILIDAD'
                codigo = (cod_entry.get().strip() or None)
                if tipo == 'DISPONIBILIDAD' and not codigo:
                    messagebox.showwarning("Error", "Ingrese el código de producto para DISPONIBILIDAD")
                    return

                # Programar
                try:
                    if not hasattr(self, 'envios_programados'):
                        from pal.services.envios import EnvioProgramado
                        self.envios_programados = EnvioProgramado(self.db_manager)
                    ok = self.envios_programados.programar_envio(numero, fecha, tipo_envio=tipo, codigo_producto=codigo)
                    if ok:
                        messagebox.showinfo("Listo", "Envío programado")
                        try:
                            if hasattr(self, 'audit_db') and self.current_user:
                                self.audit_db.log_action(accion='MSG_SCHEDULE', usuario_id=self.current_user['id'], modulo='MENSAJES', detalle=f"cliente={numero} fecha={fecha} tipo={tipo}")
                        except Exception:
                            pass
                        win.destroy()
                    else:
                        messagebox.showerror("Error", "No se pudo programar el envío")
                except Exception as e:
                    messagebox.showerror("Error", f"Fallo programando: {e}")

            btns = ttk.Frame(frm)
            btns.grid(row=4, column=0, columnspan=6, sticky='e', pady=10)
            ttk.Button(btns, text="Programar", command=confirmar).pack(side=tk.RIGHT, padx=5)
            ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side=tk.RIGHT)
            frm.columnconfigure(1, weight=1)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el programador: {e}")

    def notificar(self):

        try:
            codigo = self.cod_producto.get().strip()
            clean_codigo = re.sub(r'\D', '', codigo)  # Limpieza del código
        
            if not clean_codigo:
                messagebox.showwarning("Error", "Código no ingresado")
                return
        
            # Actualizar campo de código con versión limpia
            if clean_codigo != codigo:
                self.cod_producto.delete(0, tk.END)
                self.cod_producto.insert(0, clean_codigo)
    
            # Consultar cantidad
            query_cantidad = "SELECT n_cantidad FROM dbo.MA_DEPOPROD WHERE c_codarticulo = ? AND c_coddeposito = '0301'"
            result_cantidad = self.db_manager.fetch_data(query_cantidad, (clean_codigo,))
            if not result_cantidad or result_cantidad[0][0] <= 0:
                self.show_temp_notification("Cantidad no disponible o igual a 0")
                return
            
            # Consultar descripción
            query_descripcion = "SELECT C_DESCRI FROM dbo.MA_PRODUCTOS WHERE C_CODIGO = ?"
            result_descripcion = self.db_manager.fetch_data(query_descripcion, (clean_codigo,))
            if not result_descripcion:
                messagebox.showinfo("Error", "Descripción no encontrada")
                return
        
            descripcion = result_descripcion[0][0]
    
            # Consultar número de cliente
            query_numero_cliente = "SELECT numero_cliente FROM pal_clientes WHERE C_CODIGO = ?"
            result_numero_cliente = self.db_manager.fetch_data(query_numero_cliente, (clean_codigo,))
            if not result_numero_cliente:
                messagebox.showinfo("Error", "Número de cliente no encontrado")
                return
        
            numero_cliente = result_numero_cliente[0][0]

            self.enviar_mensaje_whatsapp(numero_cliente, [descripcion])
            self.show_temp_notification("Enviado Exitosamente")
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_action(
                        accion='MSG_SEND', usuario_id=self.current_user['id'], modulo='MENSAJES', detalle=f"cliente={numero_cliente}")
            except Exception:
                pass
    
        except Exception as e:
            messagebox.showerror("Error", f"Error obteniendo descripción o cantidad: {str(e)}")
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_action(
                        accion='MSG_SEND', usuario_id=self.current_user['id'], modulo='MENSAJES', detalle=str(e), exitoso=False)
            except Exception:
                pass

    def procesar_envio_programado(self, id_envio, numero_cliente):
        """Envía un mensaje programado usando plantillas de WhatsApp y actualiza el estado"""
        try:
            # 1. Obtener datos extendidos del envío
            envio_data = self.db_manager.fetch_data(
                "SELECT tipo_envio, codigo_producto FROM pal_envios_programados WHERE id = ?", 
                (id_envio,)
            )
            
            if not envio_data:
                self.log(f"Envío {id_envio}: no encontrado", "ERROR")
                return False
            else:
                tipo_envio, codigo_producto = envio_data[0]

            tipo_envio, codigo_producto = envio_data[0]
            productos = None

            # 2. Configurar plantillas según tipo de envío
            if tipo_envio == "DISPONIBILIDAD": 

                # Validar datos del producto
                if not codigo_producto:
                    self.log(f"Envío {id_envio}: Sin código de producto", "ERROR")
                    return False
                
                # Obtener descripción del producto
                descripcion = self.db_manager.fetch_data(
                    "SELECT C_DESCRI FROM MA_PRODUCTOS WHERE C_CODIGO = ?",
                    (codigo_producto,)
                )
            
                if not descripcion:
                    self.log(f"Producto {codigo_producto} no encontrado", "ERROR")
                    return False

                productos = [descripcion[0][0]]  # Adaptado al parámetro "productos" del método

            elif tipo_envio == "ENTREGA":
                pass  # Nombre exacto de tu plantilla en Meta

            # 3. Envío para tipos conocidos
            if self.enviar_mensaje_whatsapp(
                numero_cliente=numero_cliente,
                productos=productos,
                tipo_envio=tipo_envio
            ):
                self.db_manager.execute_query(
                    "UPDATE pal_envios_programados SET estado = 'ENVIADO' WHERE id = ?",
                    (id_envio,)
                )
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='MSG_SCHEDULED_SENT', usuario_id=self.current_user['id'], modulo='MENSAJES', detalle=f"id={id_envio}")
                except Exception:
                    pass
                return True

            return False

        except Exception as e:
            self.log(f"Error en envío {id_envio}: {str(e)}", "ERROR")
            self.audit_log.log_event(
                "ENVIO_PROGRAMADO_ERROR",
                os.getlogin(),
                "FAILED",
                error_code=ErrorCode.WHATSAPP_API_FAILURE
            )
            try:
                if hasattr(self, 'audit_db') and self.current_user:
                    self.audit_db.log_action(
                        accion='MSG_SCHEDULED_ERROR', usuario_id=self.current_user['id'], modulo='MENSAJES', detalle=str(e), exitoso=False)
            except Exception:
                pass
            return False
        finally:
            self.log(f"Finalizado el procesamiento del envío {id_envio} para el cliente {numero_cliente}", "INFO")

    def procesar_envio_masivo(self,):

        try:
            if self.actual == 0:
                # Crear tabla temporal si no existe
                self.db_manager.execute_query("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_temp_envio')
                CREATE TABLE pal_temp_envio (
                    numero_cliente NVARCHAR(50),
                    codigo_producto NVARCHAR(15),  -- Nuevo campo
                    descripcion NVARCHAR(255),
                    timestamp DATETIME DEFAULT GETDATE()  -- Nuevo campo
                    )
                """)
        
            # Insertar datos en la tabla temporal antes del envío
                for numero, codigos in self.clientes_lista:
                    for codigo in codigos:
                        cantidad_result = self.db_manager.fetch_data(
                            "SELECT n_cantidad FROM MA_DEPOPROD WHERE c_codarticulo = ? AND c_coddeposito = '0301'",
                            (codigo,)
                        )
                        if cantidad_result and cantidad_result[0][0] > 0:
                            desc_result = self.db_manager.fetch_data(
                                "SELECT C_DESCRI FROM MA_PRODUCTOS WHERE C_CODIGO = ?",
                                (codigo,)
                            )
                            if desc_result:
                                self.db_manager.execute_query(
                                    "INSERT INTO pal_temp_envio (numero_cliente, descripcion) VALUES (?, ?)",
                                    (numero, desc_result[0][0])
                                )
        finally:
            if self.actual >= self.total or self.enviando == False:
                self.toggle_buttons('normal')
                self.enviando = False
                if hasattr(self, 'progress') and self.progress and self.progress.winfo_exists():
                    self.progress.destroy()
                if hasattr(self, 'lbl_progreso') and self.lbl_progreso and self.lbl_progreso.winfo_exists():
                    self.lbl_progreso.destroy()
                self.log("Proceso de envío completado", "SUCCESS")
                try:
                    if hasattr(self, 'audit_db') and self.current_user:
                        self.audit_db.log_action(
                            accion='MSG_MASS_COMPLETE', usuario_id=self.current_user['id'], modulo='MENSAJES')
                except Exception:
                    pass

        numero = self.clientes_lista[self.actual][0]
    
        # Obtener todos los productos del cliente desde la tabla temporal
        productos_result = self.db_manager.fetch_data(
            "SELECT descripcion FROM pal_temp_envio WHERE numero_cliente = ?", (numero,)
        )
        productos = [row[0] for row in productos_result]
    
        # Registrar en logs todas las descripciones obtenidas
        self.audit_log.log_event("ENVIO_MASIVO_LOG", os.getlogin(), f"Cliente: {numero}, Productos: {productos}")
    
        if productos:
            self.enviar_mensaje_whatsapp(numero, productos)  # Enviar como un solo mensaje
            mensaje_estado = f"Enviando {self.actual + 1}/{self.total} | Cliente: {numero}"
        else:
            mensaje_estado = f"Omitido {self.actual + 1}/{self.total} | Sin stock: {numero}"
    
        # Eliminar los productos del cliente de la tabla temporal después de enviar el mensaje
        self.db_manager.execute_query("DELETE FROM pal_temp_envio WHERE numero_cliente = ?", (numero,))
    
        # Actualizar progreso
        self.actual += 1
        self.progress["value"] = self.actual
        self.lbl_progreso.config(text=mensaje_estado)
        self.root.after(7000, self.procesar_envio_masivo)

    def enviar_mensaje_whatsapp(self, numero_cliente: str, productos: list = None, tipo_envio: str = None) -> bool:
        """Envía mensaje por WhatsApp usando plantilla con lista de productos"""
        try:
            # Determinar plantilla según el tipo de envío
            if tipo_envio == "ENTREGA":
                template_name = "recordatorio_entrega"
                texto_plantilla = "📦 Tu entrega está programada para mañana. ¡Estaremos listos!"
            elif tipo_envio == "DISPONIBILIDAD":
                template_name = "sede"
                texto_plantilla = "🏪 ¡Tu producto ya está disponible en nuestra sede! Visítanos."
            else:
                # Lógica para notificaciones de stock
                template_name = "alerta_stock"
                
                # Validar productos para stock
                if productos is None:
                    codigo = self.obtener_codigo_producto_cliente(numero_cliente)
                    if not codigo:
                        self.log(f"Cliente {numero_cliente} sin producto asociado", "ERROR")
                        return False
                    
                    descripcion = self.obtener_descripcion_producto(codigo)
                    productos = [descripcion] if descripcion else []
    
                # Procesar lista de productos solo para stock
                MAX_ITEMS = 10
                MAX_LENGTH = 45
                SEPARADOR = " • "
                
                items_procesados = []
                for idx, producto in enumerate(productos[:MAX_ITEMS], 1):
                    producto_limpio = re.sub(r'[\n\t]', ' ', str(producto))
                    if len(producto_limpio) > MAX_LENGTH:
                        producto_limpio = producto_limpio[:MAX_LENGTH-3] + "..."
                    items_procesados.append(f"{idx}. {producto_limpio}")
                
                texto_plantilla = SEPARADOR.join(items_procesados)
                if len(productos) > MAX_ITEMS:
                    texto_plantilla += f"{SEPARADOR}... (+{len(productos) - MAX_ITEMS} productos más)"
    
            raw = numero_cliente or ""
            digits = re.sub(r'\D', '', raw)  # solo dígitos

            # Prefijos nacionales válidos
            prefijos = ('0412', '0424', '0414', '0416', '0426')

            if digits.startswith('0'):
                # Caso local: debe ser 11 dígitos y prefijo en la lista
                if not (len(digits) == 11 and digits.startswith(prefijos)):
                    self.log(f"Número local inválido, omitiendo: {raw}", "ERROR")
                    return False
                # Convertir 0XXXXXXXXXX → 58XXXXXXXXXX
                numero_formateado = '58' + digits[1:]
            else:
                # Caso internacional: dejar tal cual
                numero_formateado = digits

            # Validar token
            whatsapp_token = self.cred_manager.get_whatsapp_token()
            if not whatsapp_token:
                self.update_status('api_error', message="Token no configurado")
                self.audit_log.log_event(
                    "WHATSAPP_API_ERROR", 
                    os.getlogin(), 
                    "FAILED",
                    ErrorCode.INVALID_API_TOKEN
                )
                messagebox.showerror("Error", str(ErrorCode.INVALID_API_TOKEN))
                self.show_settings()
                return False
    
    
            # Configurar payload
            payload = {
                "messaging_product": "whatsapp",
                "to": numero_formateado,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "es"},
                    "components": [{
                        "type": "body",
                        "parameters": [{"type": "text", "text": texto_plantilla}]
                    }]
                }
            }
    
            # Enviar solicitud
            response = requests.post(
                "https://graph.facebook.com/v21.0/490677417472051/messages",
                headers={"Authorization": f"Bearer {whatsapp_token}", "Content-Type": "application/json"},
                json=payload
            )
    
            # Manejar respuesta
            if response.status_code == 200:
                self.log(f"Mensaje enviado a {numero_formateado}", "SUCCESS")
                self.audit_log.log_event(
                    "ENVIO_EXITOSO",
                    os.getlogin(),
                    f"Cliente: {numero_formateado} | Tipo: {tipo_envio or 'Stock'}"
                )
                return True
            
            # Manejar errores de API
            error_data = response.json().get('error', {})
            error_msg = error_data.get('message', 'Error desconocido')
            self.log(f"Error API: {error_msg}", "ERROR")
            messagebox.showerror("Error API", f"{error_msg}")
            return False
    
        except Exception as e:
            self.log(f"Error crítico: {str(e)}", "ERROR")
            self.audit_log.log_event(
                "ERROR_ENVIO",
                os.getlogin(),
                "CRITICAL",
                error_code=ErrorCode.WHATSAPP_API_FAILURE
            )
            return False
        
    def _save_modules_config(self):
        # Tomar valores de los BooleanVar y guardar en ini
        new_cfg = {k: v.get() for k, v in self.mod_vars.items()}
        save_modules_config(new_cfg)
        messagebox.showinfo(
            "Módulos Actualizados",
            "Los cambios se guardaron correctamente.\nReinicie la aplicación para que tengan efecto."
        )

    def actualizar_descripcion(self, texto: str):
        self.descripcion.config(state='normal')
        self.descripcion.delete(0, tk.END)
        self.descripcion.insert(0, texto)
        self.descripcion.config(state='readonly')
        self.descripcion.update_idletasks()

    # Helpers de Registros
    def obtener_descripcion_producto(self, codigo: str) -> str | None:
        try:
            rows = self.db_manager.fetch_data(
                "SELECT C_DESCRI FROM dbo.MA_PRODUCTOS WHERE C_CODIGO = ?",
                (str(codigo),)
            )
            if rows and rows[0] and rows[0][0]:
                return str(rows[0][0])
            return None
        except Exception:
            return None

    def validar_stock_producto(self, codigo: str) -> bool:
        try:
            rows = self.db_manager.fetch_data(
                "SELECT ISNULL(n_cantidad,0) FROM dbo.MA_DEPOPROD WHERE c_codarticulo = ? AND c_coddeposito = '0301'",
                (str(codigo),)
            )
            cantidad = int(rows[0][0]) if rows and rows[0] else 0
            return cantidad > 0
        except Exception:
            return False

    # ====================
    # MBRP (Baja Rotación)
    # ====================
    def cargar_mbrp_base(self):
        try:
            # Validar rango
            fecha_inicio = self.mbrp_fecha_inicio_entry.get_date()
            fecha_fin = self.mbrp_fecha_fin_entry.get_date()
            sede = (self.mbrp_sede_var.get() or '').split(' - ')[0]
            
            self.log(f"[MBRP] Iniciando carga: {fecha_inicio} a {fecha_fin}, Sede: {sede}", "INFO")

            # Evitar cargas simultáneas
            if getattr(self, 'mbrp_loader_thread', None) is not None and self.mbrp_loader_thread.is_alive():
                self.log("MBRP: Carga en curso; ignorando clic", "WARNING")
                return

            # Reset datos y cachés
            self.cached_ventas_mbrp = []
            self.mbrp_fecha_inicio = fecha_inicio
            self.mbrp_fecha_fin = fecha_fin
            self.mbrp_sede_codigo = sede
            
            # Invalidar caché de últimas ventas al cargar nuevos datos
            if hasattr(self, '_mbrp_ultimas_ventas_cache'):
                self._mbrp_ultimas_ventas_cache = {}
                self._mbrp_ultimas_ventas_time = 0
                self.log("[MBRP] Caché de últimas ventas invalidado", "DEBUG")

            # Estado UI
            try:
                self.api_status.config(text="MBRP: Iniciando carga...", foreground="#004C97")
                self.global_progress.pack(side=tk.RIGHT, padx=10)
                self.global_progress.config(mode="indeterminate")
                self.global_progress.start(5)
            except Exception:
                pass

            # Fila de carga
            if hasattr(self, 'mbrp_tree'):
                self.mbrp_tree.delete(*self.mbrp_tree.get_children())
                self.mbrp_tree.insert("", tk.END, values=(
                    "...", "Cargando productos de baja rotación...", "...", "...", "...", "...", "..."
                ), tags=("loading",))

            # Lanzar hilo
            from threading import Thread
            self.mbrp_loader_thread = Thread(target=self._background_load_ventas_mbrp, daemon=True, name="mbrp_loader")
            self.mbrp_loader_thread.start()
        except Exception as e:
            self.log(f"Error iniciando MBRP: {e}", "ERROR")

    def _background_load_ventas_mbrp(self):
        try:
            if not all([self.mbrp_fecha_inicio, self.mbrp_fecha_fin, self.mbrp_sede_codigo]):
                self.log("MBRP: Faltan parámetros", "ERROR")
                return

            # Carga por chunks (reutiliza infra de TRA)
            start = 1
            # Adaptive chunk size controller
            from pal.core.chunks import AdaptiveChunkController
            controller = AdaptiveChunkController(initial=500, min_size=100, max_size=2000, target_latency=2.0)
            chunk_size = controller.size
            seen = set()
            acumulados = []
            
            self.log(f"[MBRP] Iniciando carga adaptativa (chunk inicial: {chunk_size})", "INFO")

            chunk_count = 0
            while True:
                chunk_count += 1
                
                chunk_t0 = time.perf_counter()
                rows = self.db_manager.obtener_ventas_por_producto_chunk(
                    fecha_inicio=self.mbrp_fecha_inicio,
                    fecha_fin=self.mbrp_fecha_fin,
                    sede_codigo=self.mbrp_sede_codigo,
                    start_row=start,
                    fetch_size=chunk_size,
                )
                chunk_time = time.perf_counter() - chunk_t0
                if not rows:
                    self.log(f"[MBRP] Carga finalizada en chunk {chunk_count}", "INFO")
                    break
                    
                productos_nuevos = 0
                productos_duplicados = 0
                for r in rows:
                    codigo = str(r[0])
                    if codigo in seen:
                        productos_duplicados += 1
                        continue
                    seen.add(codigo)
                    acumulados.append(r)
                    productos_nuevos += 1
                
                # Solo loggear cada 5 chunks, al inicio, o al final
                should_log = chunk_count <= 2 or chunk_count % 5 == 0 or len(rows) < chunk_size
                if should_log:
                    self.mbrp_debug_log(
                        f"Chunk {chunk_count}: {len(rows)} filas | Nuevos: {productos_nuevos} | "
                        f"Total: {len(acumulados)} | Latencia: {chunk_time:.2f}s",
                        level="INFO",
                        throttle_key="chunk_progress",
                        throttle_seconds=3.0
                    )
                
                start += chunk_size
                time.sleep(0.05)

            self.log(f"[MBRP] Carga completada: {len(acumulados)} productos únicos", "SUCCESS")
            
            # Clasificar y filtrar por rotación usando lógica específica para MBRP
            from pal.services.mbrp import clasificar_rotacion_mbrp, filtrar_productos_baja_rotacion
            try:
                self.log("[MBRP] Clasificando y filtrando productos de baja rotación...", "INFO")
                self.log(f"[MBRP] Datos acumulados antes de filtrar: {len(acumulados)} productos", "DEBUG")
                
                if acumulados:
                    primera = acumulados[0]
                    self.log(f"[MBRP] Primera fila acumulada: {primera} (len={len(primera)})", "DEBUG")
                
                # PASO 1: Primero filtrar por IM (usa datos sin clasificar)
                # Filtrar productos con Índice de Movilidad bajo (umbral 30%)
                self.log(f"[MBRP] Iniciando filtrado con umbral_im=30.0...", "DEBUG")
                productos_baja_rotacion = filtrar_productos_baja_rotacion(acumulados, umbral_im=30.0)
                self.log(f"[MBRP] Filtrados: {len(productos_baja_rotacion)}/{len(acumulados)} productos (IM <= 30%)", "INFO")
                
                if not productos_baja_rotacion:
                    self.log(f"[MBRP] ADVERTENCIA: Filtrado retornó lista vacía", "WARNING")
                
                # PASO 2: Luego clasificar los productos filtrados
                # Usar clasificación MBRP que se enfoca en productos de baja rotación
                self.log(f"[MBRP] Iniciando clasificación de {len(productos_baja_rotacion)} productos...", "DEBUG")
                productos_clasificados = clasificar_rotacion_mbrp(productos_baja_rotacion)
                self.log(f"[MBRP] Clasificados: {len(productos_clasificados)} productos", "INFO")
                
                if not productos_clasificados:
                    self.log(f"[MBRP] ADVERTENCIA: Clasificación retornó lista vacía", "WARNING")
                
                self.cached_ventas_mbrp = productos_clasificados
                self.log(f"[MBRP] Cache MBRP actualizado: {len(self.cached_ventas_mbrp)} productos", "INFO")
            except Exception as e:
                self.log(f"Error en clasificación MBRP: {e}", "ERROR")
                import traceback
                self.log(f"Traceback: {traceback.format_exc()}", "DEBUG")
                # En caso de error, usar datos sin clasificar
                self.log(f"[MBRP] Usando datos sin clasificar como fallback: {len(acumulados)} productos", "WARNING")
                self.cached_ventas_mbrp = list(acumulados)

            # Actualizar UI
            def _finish():
                try:
                    self.log("[MBRP] _finish() iniciado", "DEBUG")
                    self.log(f"[MBRP] _finish() - cached_ventas_mbrp tiene {len(self.cached_ventas_mbrp)} productos", "DEBUG")
                    
                    self.aplicar_filtro_mbrp()
                    self.log("[MBRP] _finish() - aplicar_filtro_mbrp completado", "DEBUG")
                    
                    try:
                        self.api_status.config(text="MBRP: Completo", foreground="green")
                        self.log("[MBRP] _finish() - api_status actualizado", "DEBUG")
                    except Exception as e:
                        self.log(f"[MBRP] Error actualizando api_status: {e}", "WARNING")
                    
                    try:
                        self.global_progress.stop()
                        self.global_progress.pack_forget()
                        self.log("[MBRP] _finish() - progress bar detenido", "DEBUG")
                    except Exception as e:
                        self.log(f"[MBRP] Error deteniendo progress bar: {e}", "WARNING")
                    
                    self.log("[MBRP] _finish() completado correctamente", "SUCCESS")
                except Exception as e:
                    self.log(f"[MBRP] ERROR en _finish: {e}", "ERROR")
                    import traceback
                    tb = traceback.format_exc()
                    self.log(f"[MBRP] Traceback: {tb}", "DEBUG")
                    # Intentar detener progress bar de todas formas
                    try:
                        self.global_progress.stop()
                        self.global_progress.pack_forget()
                    except Exception:
                        pass
            self.root.after(0, _finish)
        except Exception as e:
            self.log(f"MBRP error en carga: {e}", "ERROR")
            try:
                self.root.after(0, lambda: (self.global_progress.stop(), self.global_progress.pack_forget()))
            except Exception:
                pass

    def aplicar_filtro_mbrp(self):
        try:
            if not hasattr(self, 'cached_ventas_mbrp') or not self.cached_ventas_mbrp:
                self.mbrp_debug_log(
                    "No hay datos MBRP en cache",
                    level="WARNING",
                    throttle_key="no_data",
                    throttle_seconds=5.0
                )
                return
            
            self.log(f"[MBRP] aplicar_filtro_mbrp() iniciado con {len(self.cached_ventas_mbrp)} productos en cache", "DEBUG")
            
            # Inicializar diccionarios si no existen
            if not hasattr(self, 'mbrp_dept_dict'):
                self.log("[MBRP] Inicializando mbrp_dept_dict vacío", "WARNING")
                self.mbrp_dept_dict = {}
            if not hasattr(self, 'mbrp_group_dict'):
                self.mbrp_group_dict = {}
            if not hasattr(self, 'mbrp_sub_dict'):
                self.mbrp_sub_dict = {}
            
            # Filtros jerárquicos (similar a TRA)
            dept_cod = self.mbrp_dept_dict.get(self.mbrp_dept_var.get()) if hasattr(self, 'mbrp_dept_var') else None
            group_cod = None
            sub_cod = None
            if dept_cod and hasattr(self, 'mbrp_group_var'):
                group_desc = self.mbrp_group_var.get()
                group_cod = self.mbrp_group_dict.get(dept_cod, {}).get(group_desc)
                if group_cod and hasattr(self, 'mbrp_sub_var'):
                    sub_desc = self.mbrp_sub_var.get()
                    # Usar string como key (formato: "dept|group")
                    key = f"{dept_cod}|{group_cod}"
                    sub_cod = self.mbrp_sub_dict.get(key, {}).get(sub_desc)

            texto = self.mbrp_search_var.get() if hasattr(self, 'mbrp_search_var') else ''
            
            self.log(
                f"[MBRP] Aplicando filtros - Dept: {dept_cod}, Group: {group_cod}, Sub: {sub_cod}, Texto: '{texto}'",
                "DEBUG"
            )

            from pal.services.tra import filter_ventas_tra, paginate_tra
            datos_filtrados = filter_ventas_tra(
                ventas=self.cached_ventas_mbrp,
                dept_code=dept_cod,
                group_code=group_cod,
                sub_code=sub_cod,
                search_text=texto,
                filter_rotacion='TODAS',
                favoritos=self._get_favoritos_local(),
            )
            
            self.log(
                f"[MBRP] Después de filter_ventas_tra: {len(datos_filtrados)} productos filtrados",
                "DEBUG"
            )

            if not hasattr(self, 'mbrp_current_page') or self.mbrp_current_page < 1:
                self.mbrp_current_page = 1
            if not hasattr(self, 'mbrp_page_size'):
                self.mbrp_page_size = 500
            datos_pagina, total_paginas, self.mbrp_current_page = paginate_tra(
                datos_filtrados, self.mbrp_current_page, self.mbrp_page_size
            )
            
            self.log(
                f"[MBRP] Página {self.mbrp_current_page}/{total_paginas} ({len(datos_pagina)} filas en página)",
                "DEBUG"
            )
            
            self.log(f"[MBRP] Llamando a mostrar_mbrp_paginado con {len(datos_pagina)} productos", "DEBUG")
            self.mostrar_mbrp_paginado(datos_pagina)
            self.log(f"[MBRP] mostrar_mbrp_paginado completado", "DEBUG")
            
            self.actualizar_controles_paginacion_mbrp(total_paginas)
        except Exception as e:
            self.log(f"[MBRP] ERROR en aplicar_filtro_mbrp: {e}", "ERROR")
            import traceback
            self.log(f"[MBRP] Traceback: {traceback.format_exc()}", "DEBUG")

    def mostrar_mbrp_paginado(self, datos):
        if not hasattr(self, 'mbrp_tree'):
            self.log("[MBRP] ERROR: mbrp_tree no existe", "ERROR")
            return
        try:
            self.mbrp_tree.delete(*self.mbrp_tree.get_children())
        except Exception as e:
            self.log(f"[MBRP] Error limpiando mbrp_tree: {e}", "ERROR")
            return
        
        if not datos:
            self.log("[MBRP] datos vacío en mostrar_mbrp_paginado", "DEBUG")
            return
            
        # Importar servicios MBRP
        from pal.services.mbrp import calcular_indice_movilidad, obtener_ultimas_ventas_bulk, calcular_dias_sin_venta
        
        # Cache de stock rápido
        codigos = [r[0] for r in datos]
        sede = self.mbrp_sede_codigo or '0301'
        stock_map = self.obtener_stock_actual_bulk(codigos, sede)
        
        # Calcular Índices de Movilidad para todos los productos
        indices_movilidad = calcular_indice_movilidad(self.cached_ventas_mbrp or datos)
        
        # Cache de últimas ventas con TTL de 60 segundos
        # Se invalida automáticamente al presionar "Cargar"
        if not hasattr(self, '_mbrp_ultimas_ventas_cache') or not hasattr(self, '_mbrp_ultimas_ventas_time'):
            self._mbrp_ultimas_ventas_cache = {}
            self._mbrp_ultimas_ventas_time = 0
        
        current_time = time.time()
        cache_ttl = 60  # 60 segundos (reducido de 5 minutos para mayor frescura de datos)
        
        # Verificar si los códigos de la página actual están en caché
        codigos_faltantes = [c for c in codigos if c not in self._mbrp_ultimas_ventas_cache]
        cache_expirado = (current_time - self._mbrp_ultimas_ventas_time) > cache_ttl
        
        # Consultar si: 1) caché expirado, 2) caché vacío, o 3) hay códigos faltantes
        if cache_expirado or not self._mbrp_ultimas_ventas_cache or codigos_faltantes:
            # Consultar todos los códigos de la página actual
            ultimas_ventas_nuevas = obtener_ultimas_ventas_bulk(self.db_manager, codigos, sede)
            
            # Actualizar caché (merge con datos existentes si no está expirado)
            if cache_expirado or not self._mbrp_ultimas_ventas_cache:
                self._mbrp_ultimas_ventas_cache = ultimas_ventas_nuevas
                self.mbrp_debug_log(f"Últimas ventas consultadas: {len(ultimas_ventas_nuevas)} productos (caché renovado)")
            else:
                # Merge incremental
                self._mbrp_ultimas_ventas_cache.update(ultimas_ventas_nuevas)
                self.mbrp_debug_log(f"Últimas ventas actualizadas: {len(ultimas_ventas_nuevas)} productos nuevos")
            
            self._mbrp_ultimas_ventas_time = current_time
            ultimas_ventas = self._mbrp_ultimas_ventas_cache
        else:
            ultimas_ventas = self._mbrp_ultimas_ventas_cache
            tiempo_restante = int(cache_ttl - (current_time - self._mbrp_ultimas_ventas_time))
            self.mbrp_debug_log(f"Usando caché de últimas ventas ({tiempo_restante}s restantes)")
        
        for idx, fila in enumerate(datos):
            try:
                codigo = str(fila[0])
                desc = fila[1]
                neto = fila[5]
                rotacion = fila[6] if len(fila) > 6 else 'BAJA'
                stock_actual = int(stock_map.get(codigo, 0) or 0)
                
                # Índice de Movilidad
                im_porcentaje = indices_movilidad.get(codigo, 0.0)
                
                # Calcular días desde última venta
                fecha_ultima_venta = ultimas_ventas.get(codigo)
                dias_sin_venta = calcular_dias_sin_venta(fecha_ultima_venta)
                
                # Formatear última venta para mostrar
                if dias_sin_venta == -1:
                    ultima_venta_texto = "Nunca"
                elif dias_sin_venta == 0:
                    ultima_venta_texto = "Hoy"
                elif dias_sin_venta == 1:
                    ultima_venta_texto = "1 día"
                else:
                    ultima_venta_texto = f"{dias_sin_venta} días"
                
                # Determinar tags de color por rotación e Índice de Movilidad con filas alternadas
                tag_base_rotacion = str(rotacion).lower()
                
                # Tag por Índice de Movilidad (prioridad sobre rotación)
                if im_porcentaje < 5.0:
                    tag_base = "im_critico"
                elif im_porcentaje <= 10.0:
                    tag_base = "im_muy_bajo" 
                elif im_porcentaje <= 20.0:
                    tag_base = "im_bajo"
                else:
                    tag_base = tag_base_rotacion  # Usar tag de rotación normal
                
                # Aplicar estilo alternado
                if idx % 2 == 0:
                    tag_final = tag_base  # Filas pares: colores claros
                else:
                    tag_final = f"{tag_base}_alt"  # Filas impares: colores oscuros
                
                self.mbrp_tree.insert(
                    "", tk.END,
                    values=(codigo, desc, rotacion, int(float(neto or 0)), stock_actual, f"{im_porcentaje}%", ultima_venta_texto),
                    tags=(tag_final,)
                )
            except Exception as e:
                self.log(f"Error procesando fila MBRP {fila}: {str(e)}", "ERROR")
                continue

    def actualizar_controles_paginacion_mbrp(self, total_paginas):
        if hasattr(self, 'mbrp_pagina_label'):
            self.mbrp_pagina_label.config(text=f"Página {self.mbrp_current_page}/{total_paginas}")
        if hasattr(self, 'mbrp_btn_prev'):
            self.mbrp_btn_prev['state'] = 'normal' if self.mbrp_current_page > 1 else 'disabled'
        if hasattr(self, 'mbrp_btn_next'):
            self.mbrp_btn_next['state'] = 'normal' if self.mbrp_current_page < total_paginas else 'disabled'

    def cambiar_pagina_mbrp(self, delta):
        self.mbrp_current_page += delta
        self.aplicar_filtro_mbrp()
    
    def actualizar_ultimas_ventas_mbrp(self):
        """
        Fuerza la actualización del caché de últimas ventas sin recargar todos los datos.
        Útil cuando se sabe que hubo ventas recientes.
        """
        if not hasattr(self, 'cached_ventas_mbrp') or not self.cached_ventas_mbrp:
            self.log("No hay datos MBRP cargados. Use 'Cargar' primero.", "WARNING")
            return
        
        try:
            # Invalidar caché
            if hasattr(self, '_mbrp_ultimas_ventas_cache'):
                self._mbrp_ultimas_ventas_cache = {}
                self._mbrp_ultimas_ventas_time = 0
            
            self.log("[MBRP] Actualizando últimas ventas...", "INFO")
            
            # Refrescar la vista actual (forzará nueva consulta)
            self.aplicar_filtro_mbrp()
            
            self.log("[MBRP] Últimas ventas actualizadas correctamente", "SUCCESS")
            
        except Exception as e:
            self.log(f"Error actualizando últimas ventas MBRP: {e}", "ERROR")

    def generar_reporte_mbrp(self):
        """Genera un reporte detallado de productos de baja rotación"""
        if not hasattr(self, 'cached_ventas_mbrp') or not self.cached_ventas_mbrp:
            messagebox.showwarning("Sin datos", "No hay datos MBRP disponibles. Cargue datos primero.")
            return
            
        try:
            from pal.services.mbrp import generar_reporte_baja_rotacion
            
            sede = self.mbrp_sede_codigo or '0301'
            reporte = generar_reporte_baja_rotacion(
                self.cached_ventas_mbrp, 
                self.db_manager, 
                sede
            )
            
            if "error" in reporte:
                messagebox.showerror("Error", f"Error generando reporte: {reporte['error']}")
                return
            
            # Crear ventana de reporte
            reporte_window = tk.Toplevel(self.root)
            reporte_window.title("Reporte MBRP - Productos de Baja Rotación")
            reporte_window.geometry("600x500")
            
            # Texto del reporte
            texto_frame = ttk.Frame(reporte_window)
            texto_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            texto = tk.Text(texto_frame, wrap=tk.WORD, font=('Consolas', 10))
            scrollbar = ttk.Scrollbar(texto_frame, orient=tk.VERTICAL, command=texto.yview)
            texto.configure(yscrollcommand=scrollbar.set)
            
            # Generar contenido del reporte
            contenido = f"""REPORTE MBRP - PRODUCTOS DE BAJA ROTACIÓN
{'='*50}

Período: {self.mbrp_fecha_inicio} - {self.mbrp_fecha_fin}
Sede: {sede}
Fecha reporte: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RESUMEN EJECUTIVO:
{'-'*20}
Total productos analizados: {reporte['total_productos']}
Sin movimiento (IM = 0%): {reporte['sin_movimiento']}
Baja rotación (IM ≤ 10%): {reporte['baja_rotacion']}
Rotación media (IM ≤ 30%): {reporte['media_rotacion']}
Alta rotación (IM > 30%): {reporte['alta_rotacion']}

Productos críticos identificados: {reporte['productos_criticos']}
Porcentaje de baja rotación: {reporte['porcentaje_baja_rotacion']}%

PRODUCTOS MÁS CRÍTICOS:
{'-'*30}
"""
            
            for i, producto in enumerate(reporte['detalle_criticos'], 1):
                contenido += f"{i}. {producto['codigo']} - {producto['descripcion'][:50]}\n"
                contenido += f"   IM: {producto['im']}% | Días sin venta: {producto['dias_sin_venta']}\n\n"
            
            contenido += "\nRECOMENDACIONES:\n"
            contenido += "-"*20 + "\n"
            contenido += "1. Revisar productos sin movimiento para posible descontinuación\n"
            contenido += "2. Implementar estrategias de liquidación para productos críticos\n"
            contenido += "3. Analizar causa raíz de baja rotación\n"
            contenido += "4. Considerar reposicionamiento o cambio de precio\n"
            
            texto.insert('1.0', contenido)
            texto.config(state='disabled')
            
            texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Botón para cerrar
            ttk.Button(reporte_window, text="Cerrar", command=reporte_window.destroy).pack(pady=10)
            
            self.log(f"Reporte MBRP generado: {reporte['productos_criticos']} productos críticos encontrados", "SUCCESS")
            
        except Exception as e:
            self.log(f"Error generando reporte MBRP: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Error generando reporte: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk() 
    root.withdraw()
    app = DatabaseApp(root)
    root.mainloop() 