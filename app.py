import pyodbc
import tkinter as tk
import csv
from tkinter import ttk, messagebox
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
import math
from tkcalendar import Calendar, DateEntry
from datetime import datetime, timedelta
import requests
from enum import Enum
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from win10toast import ToastNotifier




CONFIG_FILE = 'db_config.ini'
JERARQUIA_CACHE_FILE = "jerarquia_cache.json"
FAVORITOS_CACHE_FILE = 'favoritos_cache.json'
JERARQUIA_CACHE_TTL = timedelta(hours=15)
LOCATION_GROUPS = {
    'BARINAS': ['0101', '0108'],
    'GUANARE': ['0401', '0402'],
    'CDT': ['0106'],
}

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
                'estadisticas':   'True',
                'calendario':     'False',
                'stock':          'True'
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
    
class CacheDescripciones:
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl

    def obtener(self, codigo):
        item = self.cache.get(codigo)
        if item and (time.time() - item['timestamp']) < self.ttl:
            return item['descripcion']
        return None

    def guardar(self, codigo, descripcion):
        self.cache[codigo] = {
            'descripcion': descripcion,
            'timestamp': time.time()
        }

class EnvioProgramado:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def programar_envio(self, numero_cliente, fecha):
        try:
            self.db_manager.execute_query(
                "INSERT INTO envios_programados (numero_cliente, fecha_programada, estado) VALUES (?, ?, 'PENDIENTE')",
                (numero_cliente, fecha)
            )
            return True
        except Exception as e:
            print(f"Error programando envío: {str(e)}")
            return False

class ProgramadorEnvios:
    def __init__(self, db_manager, app):
        self.db_manager = db_manager
        self.app = app
        self.hilo = threading.Thread(target=self.verificar_envios, daemon=True)
        self.hilo.start()

    def verificar_envios(self):
        while True:
            try:
                if not self.db_manager.conn:
                    time.sleep(10)
                    continue

                ahora = datetime.now()
                pendientes = self.db_manager.fetch_data(
                    "SELECT id, numero_cliente FROM envios_programados "
                    "WHERE fecha_programada <= ? AND estado = 'PENDIENTE'",
                    (ahora,)
                )
                self.app.log(f"Envíos pendientes encontrados: {len(pendientes)}", "DEBUG")

                for envio in pendientes:
                    id_envio, numero_cliente = envio
                    self.app.procesar_envio_programado(id_envio, numero_cliente)

                    self.verificar_recordatorios()

            except Exception as e:
                self.app.log(f"Error en programador: {str(e)}", "ERROR")
            time.sleep(60)

  
    def verificar_recordatorios(self):
        ahora = datetime.now()
        recordatorios = self.db_manager.fetch_data(
        "SELECT id, numero_cliente, tipo_envio FROM envios_programados "
        "WHERE fecha_programada BETWEEN ? AND ? AND estado = 'PENDIENTE'",
        (ahora, ahora + timedelta(hours=24)))
    
        for id_envio, numero_cliente, tipo_envio in recordatorios:
            self.log(f"Enviando recordatorio ({tipo_envio}) a {numero_cliente}", "INFO")
            self.enviar_mensaje_whatsapp(numero_cliente, tipo_envio=tipo_envio)

class ErrorCode(Enum):
    # Errores de base de datos (1000-1999)
    DB_CONNECTION_FAILED = (1001, "Error de conexión a la base de datos")
    DB_QUERY_EXECUTION = (1002, "Error al ejecutar consulta SQL")
    DB_TABLE_CREATION = (1003, "Error creando tabla en la base de datos")
    DB_RECORD_NOT_FOUND = (1004, "Registro no encontrado")
    DB_DESCRIPTION_NOT_FOUND = (1005, "Descripción no encontrada")
    AL_CRITIC_ERROR = (1006, "")
    
    # Errores de validación (2000-2999)
    INVALID_CLIENT_NUMBER = (2001, "Número de cliente inválido")
    INVALID_PRODUCT_CODE = (2002, "Código de producto inválido")
    DANGEROUS_INPUT = (2003, "Entrada con caracteres potencialmente peligrosos")
    
    # Errores de cifrado (3000-3999)
    ENCRYPTION_FAILED = (3001, "Error al cifrar datos")
    DECRYPTION_FAILED = (3002, "Error al descifrar datos")
    KEY_GENERATION = (3003, "Error generando clave de cifrado")
    
    # Errores de API (4000-4999)
    WHATSAPP_API_FAILURE = (4001, "Error en comunicación con API de WhatsApp")
    INVALID_API_TOKEN = (4002, "Token de API inválido o expirado")
    
    # Autenticación y sesión (5000-5999)
    AUTH_FAILED = (5001, "Error de autenticación")
    SESSION_EXPIRED = (5002, "Sesión expirada por inactividad")
    
    # Configuración (6000-6999)
    MISSING_CONFIG = (6001, "Configuración faltante")
    INVALID_CONFIG = (6002, "Configuración inválida")

    def __init__(self, code, description):
        self.code = code
        self.description = description

    def __str__(self):
        return f"[{self.code}] {self.description}"
    
class SessionManager:
    def __init__(self, root: tk.Tk)-> None:
        self.root: tk.Tk= root
        self.last_activity = time.time()
        self.timeout = 900 # 15 minutos
        self.session_active: bool = False
        self.enviando = False
        self.progress = None
        self.lbl_progreso = None
        self.after_id: Optional[str] = None


        #Monitorear actividad
        
        root.bind("<Key>", self.update_activity)
        root.bind("<Button>", self.update_activity)
        root.bind("<Motion>", self.update_activity)

    def update_activity(self, event=None):
        self.last_activity = time.time()
        if not self.session_active:
            self.start_session()
        return 0  # Valor entero apropiado para WNDPROC en Windows

    def start_session(self):
        self.session_active = True   
        self.check_activity()        

    def check_activity(self):
            if self.session_active and (time.time() - self.last_activity) > self.timeout:
                self.expire_session()
            elif self.session_active:
                self.after_id = self.root.after(1000, self.check_activity) 
                    
    def expire_session(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        try:
            if keyring.get_password("DBClientApp", "temp_pass"):
                keyring.delete_password("DBClientApp", "temp_pass")
        except Exception as e:
            print(f"Error eliminando contraseña temporal: {str(e)}")
        
        messagebox.showinfo("Sesión Expirada", "La sesión ha expirado por inactividad")
        self.root.destroy()

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)

        handler = RotatingFileHandler(
            'audit.log',
            maxBytes=5*1024*1024, # 5MB
            backupCount= 3,
            encoding='utf-8'
        )

        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_event(self, action, user, status, error_code=None):
        log_entry = f"USER: {user} | ACTION: {action} | STATUS: {status}"
        if error_code:
            log_entry += f" | ERROR: {error_code.code} - {error_code.description}"
        self.logger.info(log_entry)

class SecureCredentialsManager:
    def __init__(self):
        self.service_name = "DBClientApp"
        self.key = self.get_or_create_key()

    def get_or_create_key(self):
        key = keyring.get_password(self.service_name, "encryption_key")
        if not key:    
            key = Fernet.generate_key().decode()
            keyring.set_password(self.service_name, "encryption_key", key)  
        return key.encode()

    def encrypt(self, data):
        try:
            return Fernet(self.key).encrypt(data.encode()).decode()
        except Exception as e:
            error_msg = f"{ErrorCode.ENCRYPTION_FAILED}: {str(e)}"
            raise Exception(error_msg) from e

    def decrypt(self, encrypted_data):
        try:
            return Fernet(self.key).decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            error_msg = f"{ErrorCode.DECRYPTION_FAILED}: {str(e)}"
            raise Exception(error_msg) from e

    def store_temp_password(self, password):
        if password:
            encrypted = self.encrypt(password)
            keyring.set_password(self.service_name, "temp_pass", encrypted)

    def get_temp_password(self):
        encrypted = keyring.get_password(self.service_name, "temp_pass")
        return self.decrypt(encrypted) if encrypted else None

    def get_whatsapp_token(self):
        encrypted_token = keyring.get_password(self.service_name, "whatsapp_token")
        return self.decrypt(encrypted_token) if encrypted_token else None

    def store_whatsapp_token(self, token):
        try:
            encrypted = self.encrypt(token) if token else ""
            keyring.set_password(self.service_name, "whatsapp_token", encrypted)
        except Exception as e:
            error_msg = f"{ErrorCode.ENCRYPTION_FAILED}: {str(e)}"
            raise Exception(error_msg) from e

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connected_server = ""
        self.config = configparser.ConfigParser()
        self.server = None
        self.database = None
        self.user = None
        self.password = None

    def table_exists(self, table_name: str) -> bool:
        """Verifica si una tabla existe en la base de datos con manejo de errores mejorado"""
        try:
            query = """
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = LOWER(?)
            """
            result = self.fetch_data(query, (table_name.lower(),))
            return result[0][0] > 0 if result else False
        except Exception as e:
            print(f"Error verificando tabla {table_name}: {str(e)}")
            return False

    def connect(self, server, database, user, password, retry_attempts=2):
        """
        Connect to the database with retry logic and better error handling
        
        Parameters:
            server (str): Database server address
            database (str): Database name
            user (str): Username for SQL authentication (empty for Windows auth)
            password (str): Password for SQL authentication
            retry_attempts (int): Number of connection retries before failing
            
        Returns:
            bool: True if connected successfully
            
        Raises:
            Exception: If connection fails after all retries
        """
        # Log connection attempt with sanitized info
        print(f"Attempting to connect to server: {server}, database: {database}, user: {user if user else 'Windows Auth'}")
        
        # Cadena inicial sin database para crear la BD si no existe
        initial_conn_str = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={server};"
            "Encrypt=no;"          
            "TrustServerCertificate=yes;"  # Changed to yes for better compatibility
            "Connection Timeout=30;"       # Increased timeout
        )
    
        if user:
            initial_conn_str += f"UID={user};PWD={password or ''};"
        else:
            initial_conn_str += "Trusted_Connection=yes;"

        # Track retries
        attempt = 0
        last_error = None
        
        while attempt <= retry_attempts:
            if attempt > 0:
                print(f"Retry attempt {attempt} of {retry_attempts}...")
                time.sleep(2)  # Add delay between retries
                
            # Intentar crear la base de datos si no existe
            try:
                #print(f"Connecting to server without specifying database...")
                temp_conn = pyodbc.connect(initial_conn_str)  # Sin database
                temp_cursor = temp_conn.cursor()
                #print(f"Creating database {database} if it doesn't exist...")
                temp_cursor.execute(f"""
                    IF NOT EXISTS (
                        SELECT name FROM sys.databases 
                        WHERE name = '{database}'
                    )
                    CREATE DATABASE {database}
                """)
                temp_conn.commit()
                temp_conn.close()
                # print(f"Database {database} is ready")
                # If we get here, break out of retry loop
                break
            except pyodbc.Error as e:
                last_error = e
                error_details = str(e).replace('\n', ' ')
                print(f"Connection attempt {attempt+1} failed: {error_details}")
                attempt += 1
                
                # Only raise exception if we've exhausted all retries
                if attempt > retry_attempts:
                    error_msg = f"{ErrorCode.DB_CONNECTION_FAILED}: {str(e)}"
                    raise Exception(error_msg) from e

        # Cadena de conexión final CON database
        final_conn_str = initial_conn_str + f"DATABASE={database};"

        try:
            self.conn = pyodbc.connect(final_conn_str)
            self.cursor = self.conn.cursor()
            self.connected_server = server
            # Store connection parameters for potential reconnection
            self.server = server
            self.database = database
            self.user = user
            self.password = password
            self.create_table()
            return True
        except pyodbc.Error as e:
            error_msg = f"{ErrorCode.DB_CONNECTION_FAILED}: {str(e)}"
            raise Exception(error_msg) from e


    def create_table(self):
        try:
            # Crear tabla clientes con índices
            self.cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='clientes' AND xtype='U')
                CREATE TABLE clientes (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    numero_cliente NVARCHAR(50) NOT NULL,
                    C_CODIGO NVARCHAR(15) NOT NULL
                );

                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_clientes_numero')
                CREATE INDEX idx_clientes_numero ON clientes (numero_cliente);
                
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_clientes_codigo')
                CREATE INDEX idx_clientes_codigo ON clientes (C_CODIGO);
            """)
            self.conn.commit()

            # Crear tabla envios_programados con índices
            self.cursor.execute("""
            IF NOT EXISTS (
                SELECT * FROM sys.tables 
                WHERE name = 'envios_programados' AND type = 'U'
            )
            CREATE TABLE envios_programados (
                id INT IDENTITY(1,1) PRIMARY KEY,
                numero_cliente NVARCHAR(50) NOT NULL,
                fecha_programada DATETIME NOT NULL,
                fecha_creacion DATETIME DEFAULT GETDATE(),
                estado NVARCHAR(20) DEFAULT 'PENDIENTE',
                tipo_envio NVARCHAR(20) NOT NULL 
                    CHECK (tipo_envio IN ('ENTREGA', 'DISPONIBILIDAD')),
                codigo_producto NVARCHAR(15) NULL  -- Nueva columna añadida
            );

            IF NOT EXISTS (
                SELECT * FROM sys.indexes 
                WHERE name = 'idx_envios_fecha_estado'
            )
            CREATE INDEX idx_envios_fecha_estado 
            ON envios_programados (fecha_programada, estado);

            IF NOT EXISTS (
                SELECT * FROM sys.indexes 
                WHERE name = 'idx_envios_numero'
            )
            CREATE INDEX idx_envios_numero 
            ON envios_programados (numero_cliente);

            IF NOT EXISTS (
                SELECT * FROM sys.indexes 
                WHERE name = 'idx_envios_producto'
            )
            CREATE INDEX idx_envios_producto 
            ON envios_programados (codigo_producto);  -- Nuevo índice añadido
        """)
            self.conn.commit()

        except pyodbc.Error as e:
            error_msg = f"{ErrorCode.DB_TABLE_CREATION}: {str(e)}"
            raise Exception(error_msg) from e
        
    def obtener_alertas_stock(self):
        try:
            query = """
                SELECT 
                    c_codarticulo AS codigo,
                    MAX(p.C_DESCRI) AS descripcion,
                    CAST(SUM(n_cantidad) AS INT) AS stock,  
                CASE
                    WHEN SUM(n_cantidad) BETWEEN 15 AND 20 THEN 'Leve'  
                    WHEN SUM(n_cantidad) BETWEEN 8 AND 14 THEN 'Media'
                    ELSE 'Crítica'
                END AS nivel
                FROM MA_DEPOPROD d
                    INNER JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.C_CODIGO
                    WHERE c_coddeposito = '0301'
                    GROUP BY c_codarticulo
                    HAVING SUM(n_cantidad) < 21  
                    ORDER BY stock ASC
                """
            return self.fetch_data(query)
        except Exception as e:
            print(f"{str(e)}")
            return []
        
    def toggle_favorito(self, codigo_producto):
        try:
            self.execute_query(
                """MERGE INTO favoritos_productos AS target
                USING (VALUES (?)) AS source(codigo)
                ON target.codigo = source.codigo
                WHEN MATCHED THEN
                   UPDATE SET favorito = ~favorito
                WHEN NOT MATCHED THEN
                   INSERT (codigo, favorito) VALUES (source.codigo, 1);""",
                (codigo_producto,)
            )
            return True
        except Exception as e:
            print(f"Error actualizando favorito: {str(e)}")
            return False

    def execute_query(self, query, params=None):
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.conn.commit()
            return True
        except pyodbc.Error as e:
            self.conn.rollback()
            error_msg = f"{ErrorCode.DB_QUERY_EXECUTION}: {str(e)}"
            raise Exception(error_msg) from e

    def fetch_data(self, query, params=None):
        try:
            if not self.conn:
                self.connect(self.server, self.database, self.user, self.password)
            
            # Añadir reintentos para errores transitorios
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.cursor.execute(query, params or ())
                    return self.cursor.fetchall()
                except pyodbc.OperationalError as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        self.connect(self.server, self.database, self.user, self.password)
                        continue
                    raise
                
        except pyodbc.Error as e:
            error_msg = f"""
            Error en consulta SQL:
            Query: {query}
            Params: {params}
            Error: {str(e)}
            """
            print(error_msg, "ERROR")
            raise


class DatabaseApp:
    def __init__(self, root):
        self.ultimas_notificaciones = set()
        
        # Inicialización de componentes críticos
        self.cred_manager = SecureCredentialsManager()
        self.enviando = False
        self.session = SessionManager(root)
        self.session.start_session()
        self.root = root
        self.modules_enabled = load_modules_config()
        self.audit_log = AuditLogger()
        self.db_manager = DatabaseManager()
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
        
        # Configuración de UI y bindings

        self.buttons = {}	
        self.setup_styles()
        self.setup_modern_ui()
        self.setup_bindings()
        self.cache = CacheDescripciones()

        if self.modules_enabled.get("envio_mensajes", False):
            self.programador = ProgramadorEnvios(self.db_manager, self)
            self.envios_programados = EnvioProgramado(self.db_manager)

        if self.modules_enabled.get("stock", False):
            self.monitor_thread = threading.Thread(target=self.monitorear_favoritos, daemon=True)
            self.monitor_thread.start()
        


        # Sistema de Paginacion ya inicializado arriba
        self.attempt_auto_connect()
        self.programar_actualizaciones_stock()

        # Sistema de notificaciones y ayuda
        self.notification_manager = self.NotificationManager(self.root)  
        self.help_tooltips = self.HelpTooltips(self.root)  
        self.setup_tooltips()
        #Notificaciones de Win10
        self.toaster = ToastNotifier()
         

        # forma de verificar hilos activos en segundo plano
        self.listar_hilos_activos()

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
        """Valida si un producto tiene stock en el depósito 0301."""
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
                "SELECT C_CODIGO FROM clientes WHERE numero_cliente = ?", 
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
            # Check for active database connection
            if not hasattr(self.db_manager, 'conn') or not self.db_manager.conn:
                print("No hay conexión activa a la base de datos para actualizar alertas")
                return
            # Forzar refresco si han pasado más de 30 minutos
            refresh_needed = (
                force_refresh or 
                not self.last_refresh or 
                (datetime.now() - self.last_refresh).seconds > 1800
            )
        
            if refresh_needed:
                self.cached_alertas = self.db_manager.obtener_alertas_stock()
                self.last_refresh = datetime.now()
                self.ultimas_notificaciones.clear()  # <-- Limpiar notificaciones
                self.log("Datos de alertas actualizados desde BD", "INFO")
        
        except Exception as e:
            print(f"Error al actualizar alertas: {str(e)}")
            self.log(f"Error crítico al actualizar alertas: {str(e)}", "ERROR")

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
        

    def actualizar_contador_paginacion(self, total_pages):
        self.pagination_label.config(text=f"Página {self.current_page}/{total_pages}")
        self.btn_prev['state'] = 'normal' if self.current_page > 1 else 'disabled'
        self.btn_next['state'] = 'normal' if self.current_page < total_pages else 'disabled'

    def monitorear_favoritos(self):
        """Monitorea favoritos usando el archivo JSON"""
        while True:
            try:
                if not self.db_manager.conn:
                    time.sleep(60)
                    continue
            
                # Obtener favoritos desde el JSON
                favoritos = self._get_favoritos_local()  # <- Cambio clave aquí
            
                # Mantener lógica original de alertas
                current_alerts = self.db_manager.obtener_alertas_stock()
            
                for codigo, desc, stock, nivel in current_alerts:
                    if codigo in favoritos:  # <- Solo verificar los favoritos del JSON
                        clave = (codigo, stock, nivel)
                        if clave not in self.ultimas_notificaciones:
                            self.mostrar_notificacion(codigo, stock, nivel)
                            self.ultimas_notificaciones.add(clave)
                        
                time.sleep(300)  # 5 minutos
            
            except Exception as e:
                self.log(f"Error monitoreo favoritos: {str(e)}", "ERROR")
                time.sleep(100)

    def obtener_existencias_por_ubicacion(self, codigo, depositos):
        # depositos es lista de strings, p. ej. ['0101','0108']
        placeholders = ','.join('?' for _ in depositos)
        sql = (
            f"SELECT SUM(n_cantidad) "
            f"FROM MA_DEPOPROD "
            f"WHERE c_codarticulo = ? AND c_coddeposito IN ({placeholders})"
        )
        params = [codigo] + depositos
        result = self.db_manager.fetch_data(sql, params)
        return int(result[0][0] or 0)

    def mostrar_notificacion(self, codigo, stock, nivel):
        """
        Muestra un toast con el nivel de alerta en el depósito principal
        y las existencias en las ubicaciones de transferencia.
        """
        # Base del mensaje
        mensaje = f"Código:{codigo}| Stock actual:{stock}|Nivel:{nivel} "

        # Para cada grupo de transferencia, hacemos un SELECT SUM(...)
        for region, deps in LOCATION_GROUPS.items():
            placeholders = ','.join('?' for _ in deps)
            sql = (
                f"SELECT SUM(n_cantidad) "
                f"FROM MA_DEPOPROD "
                f"WHERE c_codarticulo = ? AND c_coddeposito IN ({placeholders})"
            )
            params = [codigo] + deps
            try:
                result = self.db_manager.fetch_data(sql, params)
                existencias = result[0][0] or 0
                mensaje += f"{region}:{existencias} "
            except Exception as e:
                mensaje += f"{region}: error al consultar\n"

        # Mostrar toast
        self.toaster.show_toast(
            "CASAPRO STOCK",
            mensaje,
            duration=10,
            threaded=False
        )

    def exportar_csv(self):
        try:
            # 1. Mostrar diálogo para seleccionar ubicaciones
            dialog = tk.Toplevel(self.root)
            dialog.title("Seleccionar Ubicaciones")
            dialog.transient(self.root)
            dialog.grab_set()
        
            ubicaciones_vars = {
                ubicacion: tk.BooleanVar(value=True)
                for ubicacion in LOCATION_GROUPS
            }

            ttk.Label(dialog, text="Seleccione las ubicaciones a incluir:").pack(pady=10)
            for ubicacion in LOCATION_GROUPS:
                cb = ttk.Checkbutton(
                    dialog,
                    text=f"{ubicacion} ({len(LOCATION_GROUPS[ubicacion])} depósitos)",
                    variable=ubicaciones_vars[ubicacion]
                )
                cb.pack(anchor='w', padx=20)

            seleccionadas = []
            def confirmar():
                nonlocal seleccionadas
                seleccionadas = [u for u, var in ubicaciones_vars.items() if var.get()]
                dialog.destroy()
        
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=10)
            ttk.Button(btn_frame, text="Exportar", command=confirmar).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT)

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
            self.api_status.config(text="Exportando: 0%", foreground="#004C97")

            filename = f"reporte_stock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                encabezados = ['Código', 'Descripción', 'Nivel Alerta', 'Stock Principal', *seleccionadas]
                writer = csv.DictWriter(f, fieldnames=encabezados, delimiter=';')
                writer.writeheader()

                for i, item in enumerate(datos_exportar, 1):
                    row_data = {
                        'Código': item[0],
                        'Descripción': item[1].replace(';', ','),
                        'Nivel Alerta': item[3],
                        'Stock Principal': item[2]
                    }
                    for ubicacion in seleccionadas:
                        depositos = LOCATION_GROUPS[ubicacion]
                        existencia = self.obtener_existencias_por_ubicacion(item[0], depositos)
                        row_data[ubicacion] = existencia

                    writer.writerow(row_data)

                    if i % max(1, total_registros // 50) == 0 or i == total_registros:
                        progreso = int((i / total_registros) * 100)
                        self.global_progress['value'] = i
                        self.api_status.config(text=f"Exportando: {progreso}%")
                        self.root.update_idletasks()

            # 4. Mostrar resumen final
            self.api_status.config(text="API: Lista", foreground="green")
            messagebox.showinfo(
                "Exportación Exitosa",
                f"Reporte generado con éxito:\n\n"
                f"• Registros: {total_registros}\n"
                f"• Ubicaciones incluidas: {len(seleccionadas)}\n"
                f"• Depósitos consultados: {sum(len(LOCATION_GROUPS[u]) for u in seleccionadas)}\n"
                f"• Ruta: {os.path.abspath(filename)}"
            )

        except Exception as e:
            self.log(f"Error en exportación: {str(e)}", "ERROR")
            self.api_status.config(text="API: Error", foreground="red")
            messagebox.showerror("Error en Exportación", f"Error durante la exportación:\n{str(e)}")

        finally:
            self.global_progress.pack_forget()
            self.root.after(3000, lambda: self.api_status.config(
                text="API: Lista",
                foreground="green"
            ))
                
            
            
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

    def buscar_por_fecha(self):
        # Obtener fechas como objetos datetime.datetime (incluyendo hora)
        fecha_inicio = datetime.combine(self.fecha_inicio.get_date(), datetime.min.time())
        fecha_fin = datetime.combine(self.fecha_fin.get_date(), datetime.max.time())

        query = "SELECT * FROM envios_programados WHERE fecha_programada BETWEEN ? AND ?"
        params = (fecha_inicio, fecha_fin)  # Ahora son datetime.datetime

        records = self.db_manager.fetch_data(query, params)
        self.tree.delete(*self.tree.get_children())
        for row in records:
            self.tree.insert("", tk.END, values=row)

    def programar_actualizaciones_stock(self):
        def actualizar():
            while True:
                if hasattr(self, 'last_refresh'):  # <-- Verificar atributo
                    self.actualizar_alertas_stock()
                time.sleep(3600)  # <-- Actualizar cada hora
        threading.Thread(target=actualizar, daemon=True).start()
                        
    def create_gradient_header(self):
        """Genera un degradado suave de azul corporativo"""
        width = 1200  # Ancho de la ventana
        height = 50   # Altura del encabezado
    
        self.bg_image = tk.PhotoImage(width=width, height=height)
    
        # Colores base
        start_color = (0, 76, 151)    # #004C97
        end_color = (0, 45, 92)       # #002D5C
    
        # Generar degradado vertical
        for y in range(height):
        # Calcular interpolación de color
            r = start_color[0] + (end_color[0] - start_color[0]) * y // height
            g = start_color[1] + (end_color[1] - start_color[1]) * y // height
            b = start_color[2] + (end_color[2] - start_color[2]) * y // height
        
            # Crear línea horizontal con el color calculado
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.bg_image.put(color, (0, y, width, y+1))

        # Aplicar al frame del encabezado
        self.style.element_create("Header.TFrame", "image", self.bg_image)
        self.style.configure("Header.TFrame", background="#004C97")

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_create("modern", parent="alt", settings={
            "TFrame": {"configure": {"background": "#F5F6F8"}},
            "TNotebook": {"configure": {"background": "#FFFFFF"}},
            "TButton": {"configure": {"padding": 6, "font": ("Segoe UI", 10)}},
            "TNotebook.Tab": {
                "configure": {"padding": (15, 5), "background": "#e9ecef"},
                "map": {"background": [("selected", "#004C97")], "foreground": [("selected", "white")]}
            }
        })
        self.style.theme_use("modern")
        
        # Configuraciones específicas
        self.style.configure("Header.TFrame", background="white")
        self.style.configure("Sidebar.TFrame", background="#e9ecef")
        self.style.configure("Nav.TButton", 
                        font=("Segoe UI", 11), 
                        anchor="w",
                        padding=(20, 10),      #e9ecef
                        background="#e9ecef")    #004C97
        self.style.map("Nav.TButton",
                    background=[("active", "#004C97"), ("!active", "#e9ecef")],
                    foreground=[("active", "white")])
        

        

        self.style.configure("Disabled.TButton", 
                    foreground="#666666",
                    background="#e0e0e0")
        self.style.configure(
            "HeaderMenu.TMenubutton",
            background="#004C97",
            foreground="white",
            font=("Segoe UI", 12),
            relief="flat"
        )
        self.style.map("HeaderMenu.TMenubutton",
            background=[("active", "#0066CC")],  # Color al hacer hover
            foreground=[("active", "white")]
        )

    def setup_bindings(self):
        """Configurar eventos del teclado y widgets"""
        # Doble click en la tabla
        self.tree.bind("<Double-1>", lambda e: self.on_tree_double_click(e) or 0)
        
        # Validación en tiempo real del código de producto
        self.cod_producto.bind("<KeyRelease>", lambda e: self.buscar_descripcion(e) or 0)

    def setup_modern_ui(self):   
        self.root.title("Gestión de Clientes - Corporativo")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        self.create_header()
        self.create_sidebar()
        self.create_main_workspace()
        self.create_status_panel()

        style = ttk.Style()
        style.configure("TButton", background="#FFB81C", foreground="#004C97")
        style.map("TButton",
            background=[('active', '#e89f00')],
            foreground=[('active', '#003f7e')])
        
    def setup_stock_tab(self):
        if not self.modules_enabled.get("stock", False):
            return
        main_frame = ttk.Frame(self.stock_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ① --- Filtros jerárquicos ---
        hier_frame = ttk.Frame(main_frame)
        hier_frame.pack(fill=tk.X, pady=5)

        # Departamento
        ttk.Label(hier_frame, text="Departamento:").pack(side=tk.LEFT)
        self.dept_var = tk.StringVar(value='Todos')
        self.dept_combo = ttk.Combobox(hier_frame, textvariable=self.dept_var, state='readonly')
        self.dept_combo['values'] = ['Todos']
        self.dept_combo.pack(side=tk.LEFT, padx=5)
        self.dept_combo.bind('<<ComboboxSelected>>', lambda e: self.on_dept_selected())

        # Grupo
        ttk.Label(hier_frame, text="Grupo:").pack(side=tk.LEFT)
        self.group_var = tk.StringVar(value='Todos')
        self.group_combo = ttk.Combobox(hier_frame, textvariable=self.group_var, state='readonly')
        self.group_combo['values'] = ['Todos']
        self.group_combo.pack(side=tk.LEFT, padx=5)
        self.group_combo.bind('<<ComboboxSelected>>', lambda e: self.on_group_selected())

        # Subgrupo
        ttk.Label(hier_frame, text="Subgrupo:").pack(side=tk.LEFT)
        self.sub_var = tk.StringVar(value='Todos')
        self.sub_combo = ttk.Combobox(hier_frame, textvariable=self.sub_var, state='readonly')
        self.sub_combo['values'] = ['Todos']
        self.sub_combo.pack(side=tk.LEFT, padx=5)
        self.sub_combo.bind('<<ComboboxSelected>>', lambda e: self.aplicar_filtro_stock())
        # --------------------------------

        # Filtro de texto
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=5)
        ttk.Label(search_frame, text="Buscar Descripción:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        entry_search = ttk.Entry(search_frame, textvariable=self.search_var)
        entry_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_var.trace_add('write', lambda *args: self.aplicar_filtro_stock())

        # Controles superiores en dos filas
        top_controls = ttk.Frame(main_frame)
        top_controls.pack(fill=tk.X, pady=5)

        # Fila 1: Filtros de nivel
        filter_frame = ttk.Frame(top_controls)
        filter_frame.pack(fill=tk.X, pady=5)
        ttk.Label(filter_frame, text="Filtrar:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value='TODAS')
        self.current_filter = 'TODAS'

        filters = [
            ('Todas', 'TODAS'),
            ('Críticas (<8)', 'CRÍTICA'),
            ('Medias (8-14)', 'MEDIA'),
            ('Leves (15-20)', 'LEVE')
        ]

        for text, val in filters:
            ttk.Radiobutton(
                filter_frame,
                text=text,
                variable=self.filter_var,
                value=val,
                command=lambda v=val: (
                    setattr(self, 'current_page', 1),
                    setattr(self, 'current_filter', v),
                    self.aplicar_filtro_stock()
                )
            ).pack(side=tk.LEFT, padx=5)

        # Fila 2: Acciones y paginación
        action_frame = ttk.Frame(top_controls)
        action_frame.pack(fill=tk.X, pady=5)

        ttk.Button(action_frame, text="📥 Exportar CSV", command=self.exportar_csv).pack(side=tk.LEFT, padx=5)

        pagination_frame = ttk.Frame(action_frame)
        pagination_frame.pack(side=tk.RIGHT)
        self.btn_prev = ttk.Button(pagination_frame, text="◄ Anterior", command=lambda: self.cambiar_pagina(-1), width=10)
        self.btn_prev.pack(side=tk.LEFT)
        self.pagination_label = ttk.Label(pagination_frame, text="Página 1/1", width=15)
        self.pagination_label.pack(side=tk.LEFT, padx=5)
        self.btn_next = ttk.Button(pagination_frame, text="Siguiente ►", command=lambda: self.cambiar_pagina(1), width=10)
        self.btn_next.pack(side=tk.LEFT)

        # Árbol de datos
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns_config = {
            "Favorito": {"width": 50, "anchor": "center", "stretch": False},
            "Código": {"width": 100, "anchor": "center"},
            "Descripción": {"width": 350, "anchor": "w"},
            "Stock": {"width": 80, "anchor": "center"},
            "Nivel": {"width": 100, "anchor": "center"}
        }

        self.stock_tree = ttk.Treeview(tree_frame, columns=list(columns_config.keys()), show="headings", height=15)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.stock_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.stock_tree.xview)
        self.stock_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.stock_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Configurar columnas y encabezados
        for col, config in columns_config.items():
            self.stock_tree.heading(col, text=col)
            self.stock_tree.column(col, **config)

        # Estilos de filas
        self.stock_tree.tag_configure('leve', background='#abebc6')
        self.stock_tree.tag_configure('media', background='#DAF7A6')
        self.stock_tree.tag_configure('critica', background='#ff856b')
        self.stock_tree.tag_configure('favorito', background='#FFFFE0')
        self.stock_tree.tag_configure('hover', background='#f0f0f0')
        self.stock_tree.tag_configure('selected', background='#d0d0d0')

        self.stock_tree.bind('<Button-1>', self.on_favorito_click)
        self.stock_tree.bind('<Enter>', self.hover_row)
        self.stock_tree.bind('<Leave>', self.leave_row)
        self.stock_tree.bind('<<TreeviewSelect>>', self.select_row)

        # Carga inicial solo si hay conexión
        self.current_page = 1
        self.page_size = 250
        if hasattr(self.db_manager, 'conn') and self.db_manager.conn:
            self.aplicar_filtro_stock()
        else:
            print("No hay conexión activa a la base de datos para cargar alertas iniciales")

    def load_stock_filters(self):
        """Puebla Combobox tras conectar a BD usando descripciones como identificador visible"""
        try:
            deps = self.db_manager.fetch_data(
                "SELECT C_CODIGO, C_DESCRIPCIO FROM MA_DEPARTAMENTOS"
            )
            self.dept_dict = {desc: cod for cod, desc in deps if cod and desc}
            self.dept_combo['values'] = ['Todos'] + list(self.dept_dict.keys())
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
        self.aplicar_filtro_stock()
    
    def cargar_jerarquia_productos(self):
        """Filtra la jerarquía usando solo los códigos actualmente en alerta."""
        start = time.perf_counter()
        try:
            if not hasattr(self, 'all_jerarquia') or not self.all_jerarquia:
                self.log("Jerarquía vacía, iniciando carga completa", "WARNING")
                self._cargar_toda_jerarquia_productos()

            codigos_en_alerta = {r[0] for r in self.cached_alertas}
            self.producto_jerarquia = {cod: self.all_jerarquia[cod] for cod in codigos_en_alerta if cod in self.all_jerarquia}
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
            self.all_jerarquia = {fila[0]: (fila[1], fila[2], fila[3]) for fila in filas if all(fila)}
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
        self._cargar_toda_jerarquia_productos()
        self.cargar_jerarquia_productos()
        elapsed = time.perf_counter() - total_start
        self.log(f"🏁 Jerarquía inicializada en {elapsed:.2f}s", "INFO")
        # Actualizar UI en hilo principal
        try:
            self.root.after(0, self.aplicar_filtro_stock)
        except Exception:
            pass

    def aplicar_filtro_stock(self):
        # 1. Cargar datos desde caché (solo se actualiza con force_refresh o primera carga)
        if not hasattr(self, 'cached_alertas') or not self.cached_alertas:
            self.actualizar_alertas_stock(force_refresh=True)
    
        # 2. Obtener copia de los datos en caché para trabajar
        datos_filtrados = list(self.cached_alertas)
    
        # 3. Aplicar filtros jerárquicos (departamento/grupo/subgrupo)
        dept_code = self.dept_dict.get(self.dept_var.get())
        group_code = self.group_dict.get(self.group_var.get())
        sub_code = self.sub_dict.get(self.sub_var.get())
    
        if any([dept_code, group_code, sub_code]):
            datos_filtrados = [
                r for r in datos_filtrados 
                if self._coincide_jerarquia(r[0], dept_code, group_code, sub_code)
            ]
    
        # 4. Aplicar filtro de texto en descripción y código
        texto_busqueda = self.search_var.get().strip().lower()
        if texto_busqueda:
            datos_filtrados = [
                r for r in datos_filtrados 
                if texto_busqueda in (r[1].lower() + r[0].lower())
            ]
    
        # 5. Aplicar filtro de nivel de alerta
        filtro_nivel = self.filter_var.get().upper()
        if filtro_nivel != 'TODAS':
            datos_filtrados = [r for r in datos_filtrados if r[3].upper() == filtro_nivel]
    
        # 6. Ordenar por favoritos (sin modificar datos originales)
        favoritos = self._get_favoritos_local()
        datos_ordenados = sorted(
            datos_filtrados,
            key=lambda x: x[0] not in favoritos  # Favoritos primero
        )
    
        # 7. Calcular paginación
        total_items = len(datos_ordenados)
        total_paginas = max(1, math.ceil(total_items / self.page_size))
    
        # Asegurar que la página actual sea válida
        self.current_page = max(1, min(self.current_page, total_paginas))
    
        # 8. Obtener slice de datos para la página actual
        inicio = (self.current_page - 1) * self.page_size
        fin = inicio + self.page_size
        datos_pagina = datos_ordenados[inicio:fin]
    
        # 9. Actualizar interfaz
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
        
    def actualizar_controles_paginacion(self, total_paginas):
        """Actualiza los controles de paginación"""
        self.pagination_label.config(text=f"Página {self.current_page}/{total_paginas}")
        self.btn_prev['state'] = 'normal' if self.current_page > 1 else 'disabled'
        self.btn_next['state'] = 'normal' if self.current_page < total_paginas else 'disabled'    

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
        
    def aplicar_filtro(self):
        self.current_filter = self.filter_var.get()
        self.current_page = 1
        # Limpiar selección antes de actualizar
        self.stock_tree.selection_remove(self.stock_tree.selection())
        self.actualizar_alertas_stock()

    def cambiar_pagina(self, delta):
        self.current_page += delta
        self.aplicar_filtro_stock()
        

    def create_header(self):
        # Crear canvas para efectos avanzados
        header_canvas = tk.Canvas(
            self.root, 
            bg="#004C97",
            height=80,
            highlightthickness=0
        )
        header_canvas.pack(fill=tk.X)
    
        # Generar degradado
        for i in range(80):
            intensity = i / 80
            r = int(0 * (1 - intensity) + 0 * intensity)
            g = int(76 * (1 - intensity) + 45 * intensity)
            b = int(151 * (1 - intensity) + 92 * intensity)
            color = f"#{r:02x}{g:02x}{b:02x}"
            header_canvas.create_line(0, i, 2000, i, fill=color)
    
        # Añadir texto
        text_y = 80 // 2
        header_canvas.create_text(
            20, 
            text_y,
            text="Gestión de Clientes",
            fill="white",
            font=("Segoe UI", 14, "bold"),
            anchor="w"
        )
        
        # Menú de usuario
        self.user_menu = ttk.Menubutton(header_canvas, text="☰", style="HeaderMenu.TMenubutton")
        menu = tk.Menu(self.user_menu, tearoff=0)
        menu.add_command(label="Configuración", command=self.show_settings)
        menu.add_command(label="Salir", command=self.root.quit)
        self.user_menu['menu'] = menu
        self.user_menu.pack(side=tk.RIGHT, padx=20, pady=10)

    def create_sidebar(self):
        sidebar = ttk.Frame(self.root, width=250, style="Sidebar.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        nav_items = [
            ('📋 Registros', self.show_records_view),
            ('📨 Mensajería', self.show_messaging_view),
            ('⚙ Configuración', self.show_settings)
        ]
        
        for text, cmd in nav_items:
            btn = ttk.Button(sidebar, text=text, style="Nav.TButton", command=cmd)
            btn.pack(fill=tk.X, pady=2)

    def create_main_workspace(self):

        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        # Pestaña de Registros
        self.records_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.records_tab, text="Registros")
        self.setup_records_tab()


        # Pestaña de Mensajería
        if self.modules_enabled.get("envio_mensajes", False):
            self.messaging_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.messaging_tab, text="Mensajería")
            self.setup_messaging_tab()

        # Pestaña de Estadísticas
        if self.modules_enabled.get("estadisticas", False):
            self.stats_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.stats_tab, text="📊 Estadísticas")
            self.setup_stats_tab()  

        # Pestaña de Calendario
        if self.modules_enabled.get("calendario", False):
            self.calendar_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.calendar_tab, text="📅 Calendario")
            self.setup_calendar_tab()

        # Alerta de stock Supervisores
        if self.modules_enabled.get("stock", False):
            self.stock_tab = ttk.Frame(self.main_notebook)
            self.main_notebook.add(self.stock_tab, text="🚨 Alertas Stock")
            self.setup_stock_tab()
    
    def setup_stats_tab(self):
        self.stats_frame = ttk.Frame(self.stats_tab)
        self.stats_frame.pack(fill=tk.BOTH, expand=True)
    
        # Botón para actualizar gráficos
        ttk.Button(
            self.stats_frame, 
            text="Actualizar Gráficos", 
            command=self.mostrar_estadisticas
        ).pack(pady=10)
    
        # Contenedor para gráficos
        self.graph_container = ttk.Frame(self.stats_frame)
        self.graph_container.pack(fill=tk.BOTH, expand=True)

    def mostrar_estadisticas(self):
        # Limpiar gráficos anteriores
        for widget in self.graph_container.winfo_children():
            widget.destroy()
    
        # Gráfico 1: Envíos por estado
        data = self.db_manager.fetch_data(
            "SELECT tipo_envio, COUNT(*) FROM envios_programados GROUP BY tipo_envio"
        )
        if data:
            tipos, cantidades = zip(*data)
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.pie(cantidades, labels=tipos, autopct='%1.1f%%', colors=['#4CAF50', '#2196F3'])
            ax.set_title("Distribución de Tipos de Envío")
        
            canvas = FigureCanvasTkAgg(fig, self.graph_container)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            canvas.draw()

    def setup_calendar_tab(self):
        frame = ttk.Frame(self.calendar_tab)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Calendario
        self.cal = Calendar(
            frame,
            selectmode='day',
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day,
            date_pattern='y-mm-dd'
        )
        self.cal.pack(fill=tk.BOTH, expand=True, pady=10)

        # Botón para actualizar eventos
        ttk.Button(frame, text="Actualizar Eventos", command=self.cargar_eventos_calendario).pack(pady=5)

        # Área de detalles
        self.eventos_text = tk.Text(frame, height=10, wrap=tk.WORD)
        self.eventos_text.pack(fill=tk.BOTH, expand=True)

        # Cargar eventos iniciales
        self.cargar_eventos_calendario()
        self.cal.bind("<<CalendarSelected>>", lambda e: self.mostrar_eventos_fecha(e) or 0)

    def mostrar_eventos_fecha(self, event=None):
        fecha_seleccionada = self.cal.get_date()
        # Ensure return value for WNDPROC
        self.eventos_text.delete(1.0, tk.END)
    
        try:
            # Convertir fecha seleccionada a datetime (inicio y fin del día)
            fecha_inicio = datetime.strptime(fecha_seleccionada, "%Y-%m-%d")
            fecha_fin = fecha_inicio + timedelta(days=1)
        
            eventos = self.db_manager.fetch_data(
                "SELECT numero_cliente, fecha_programada, estado, tipo_envio "
                "FROM envios_programados "
                "WHERE fecha_programada >= ? AND fecha_programada < ?",  # <-- Nueva consulta
                (fecha_inicio, fecha_fin)  # <-- Parámetros como objetos datetime
            )
        
            if not eventos:
                self.eventos_text.insert(tk.END, "No hay eventos para esta fecha")
                return 0  # Return integer for WNDPROC if no events
            
            for num_cliente, fecha, estado, tipo in eventos:
                self.eventos_text.insert(tk.END, 
                    f"• Cliente: {num_cliente}\n"
                    f"  Tipo: {tipo}\n"
                    f"  Estado: {estado}\n"
                    f"  Hora: {fecha.strftime('%H:%M')}\n"
                    "------------------------\n")
                
        except Exception as e:
            self.eventos_text.insert(tk.END, f"Error obteniendo eventos: {str(e)}")
        
        return 0  # Return integer for WNDPROC
    def show_records_view(self):
        self.main_notebook.select(self.records_tab)

    def show_messaging_view(self):
        self.main_notebook.select(self.messaging_tab)

    def setup_messaging_tab(self):
        frame = ttk.Frame(self.messaging_tab)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
        # Botones superiores
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X)
    
        btn_masivo = ttk.Button(top_frame, 
                        text="▶ Iniciar envío masivo", 
                        command=self.enviar_a_todos)
        btn_masivo.pack(side=tk.LEFT)
        self.buttons['btn_envio_masivo'] = btn_masivo  # 
    
    
        ttk.Button(top_frame,
                text="🔄 Limpiar Logs",
                command=self.limpiar_logs).pack(side=tk.RIGHT)
    
        # Panel de logs con scroll
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
    
        self.logs_text = tk.Text(log_frame, wrap=tk.WORD, state='normal')
        vsb = ttk.Scrollbar(log_frame, command=self.logs_text.yview)
        self.logs_text.configure(yscrollcommand=vsb.set)
    
        # Configurar tags para colores
        self.logs_text.tag_config('DEBUG', foreground='gray')
        self.logs_text.tag_config('INFO', foreground='black')
        self.logs_text.tag_config('WARNING', foreground='orange')
        self.logs_text.tag_config('ERROR', foreground='red')
        self.logs_text.tag_config('SUCCESS', foreground='green')
    
        # Layout
        self.logs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
    
        # Contador de mensajes
        self.log_counter = 0
        self.max_logs = 200  # Máximo de líneas antes de limpiar

        programar_frame = ttk.Frame(frame)
        programar_frame.pack(fill=tk.X, pady=10)

        ttk.Button(programar_frame, 
                    text="⏰ Programar Envío", 
                    command=self.mostrar_ventana_programacion).pack(side=tk.LEFT)

    def mostrar_ventana_programacion(self):
        # Ventana para programar envío o disponibilidad
        ventana = tk.Toplevel(self.root)
        ventana.title("Programar Envío/Disponibilidad")
        ventana.geometry("400x470")

        # Selector de tipo de acción
        tipo_frame = ttk.LabelFrame(ventana, text="Tipo de Acción")
        tipo_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.tipo_envio_var = tk.StringVar(value="")
        ttk.Radiobutton(tipo_frame, text="Entrega", variable=self.tipo_envio_var,
                        value="ENTREGA", command=self._mostrar_opciones_envio).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(tipo_frame, text="Disponibilidad", variable=self.tipo_envio_var,
                        value="DISPONIBILIDAD", command=self._mostrar_opciones_envio).pack(side=tk.LEFT, padx=10)

        # Contenedor de opciones oculto hasta seleccionar tipo
        self.opciones_frame = ttk.Frame(ventana)
        self.opciones_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.opciones_frame.grid_remove()

        # Campo para ingresar uno o más números de teléfono (solo para 'Entrega')
        self.numeros_frame = ttk.LabelFrame(self.opciones_frame, text="Número(s) de Cliente")
        self.numeros_frame.grid(row=0, column=0, sticky="ew", pady=5)
        ttk.Label(self.numeros_frame, text="Teléfono(s) (separar con coma):").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_numeros = ttk.Entry(self.numeros_frame)
        self.entry_numeros.grid(row=1, column=0, sticky="ew", pady=5)

        # Frame para seleccionar fecha y hora (ambos tipos)
        self.calendar_frame = ttk.LabelFrame(self.opciones_frame, text="Fecha y Hora")
        self.calendar_frame.grid(row=1, column=0, sticky="ew", pady=5)
        ttk.Label(self.calendar_frame, text="Fecha:").grid(row=0, column=0, sticky="w", pady=5)
        self.calendario_sched = Calendar(self.calendar_frame, selectmode='day', date_pattern='mm/dd/y')
        self.calendario_sched.grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Label(self.calendar_frame, text="Hora:").grid(row=1, column=0, sticky="w", pady=5)
        self.spin_hora = ttk.Spinbox(self.calendar_frame, from_=0, to=23, width=5)
        self.spin_hora.grid(row=1, column=1, sticky="w")
        self.spin_minuto = ttk.Spinbox(self.calendar_frame, from_=0, to=59, width=5)
        self.spin_minuto.grid(row=1, column=1, sticky="e")

        # Botón para guardar programación
        ttk.Button(ventana, text="Programar", command=self.guardar_envio_programado) \
            .grid(row=2, column=0, pady=15)

    def _mostrar_opciones_envio(self):
        tipo = self.tipo_envio_var.get()
        if tipo:
            self.opciones_frame.grid()
            # Mostrar calendario siempre
            self.calendar_frame.grid()
            # Mostrar campo de números solo para envío
            if tipo == "ENTREGA":
                self.numeros_frame.grid()
            else:
                self.numeros_frame.grid_remove()
        else:
            self.opciones_frame.grid_remove()

    def guardar_envio_programado(self):
        try:
            tipo = self.tipo_envio_var.get()
            if not tipo:
                messagebox.showerror("Error", "Debe seleccionar un tipo de acción.")
                return

            # Construir fecha y hora
            fecha_str = self.calendario_sched.get_date()
            fecha_completa = datetime.strptime(
                f"{fecha_str} {self.spin_hora.get().zfill(2)}:{self.spin_minuto.get().zfill(2)}:00",
                "%m/%d/%Y %H:%M:%S"
            )

            if tipo == "ENTREGA":
                numeros_texto = self.entry_numeros.get().strip()
                if not numeros_texto:
                    messagebox.showerror("Error", "Ingrese al menos un número de teléfono.")
                    return
                numeros = [n.strip() for n in numeros_texto.split(',') if n.strip()]
                if not all(re.match(r"^\d{7,15}$", n) for n in numeros):
                    messagebox.showerror("Error", "Formato de número inválido. Use solo dígitos (7-15 caracteres).")
                    return
            
                for num in numeros:
                    self.db_manager.execute_query(
                        "INSERT INTO envios_programados (numero_cliente, fecha_programada, tipo_envio, estado) VALUES (?, ?, ?, 'PENDIENTE')",
                        (num, fecha_completa, tipo)
                    )
                messagebox.showinfo("Éxito", f"Envíos programados para {len(numeros)} número(s) como 'ENTREGA'.")

            elif tipo == "DISPONIBILIDAD":


                clientes = self.db_manager.fetch_data(
                    """SELECT c.numero_cliente, c.C_CODIGO 
                    FROM clientes c
                    WHERE c.C_CODIGO IS NOT NULL 
                    AND c.numero_cliente IS NOT NULL"""
                )
            
                if not clientes:
                    messagebox.showwarning("Sin clientes", "No hay clientes válidos con productos asociados")
                    return

                envios_creados = 0
                errores = 0
            
                for numero_cliente, codigo_producto in clientes:
                    try:
                        # Validar número de cliente
                        if not re.match(r'^58\d{10}$', f"58{numero_cliente.lstrip('0')}"):
                            raise ValueError(f"Número inválido: {numero_cliente}")
                    
                        # Verificar existencia del producto
                        if not self.db_manager.fetch_data(
                            "SELECT 1 FROM MA_PRODUCTOS WHERE C_CODIGO = ?",
                            (codigo_producto,)
                        ):
                            raise ValueError(f"Producto {codigo_producto} no existe")

                        # Verificar stock
                        stock_result = self.db_manager.fetch_data(
                            """SELECT n_cantidad 
                            FROM MA_DEPOPROD 
                            WHERE c_codarticulo = ? 
                            AND c_coddeposito = '0301'""",
                            (codigo_producto,)
                        )  
                    
                        if not stock_result or stock_result[0][0] <= 0:
                            continue  # Saltar clientes sin stock
                        
                        # Insertar registro
                        self.db_manager.execute_query(
                            """INSERT INTO envios_programados 
                            (numero_cliente, fecha_programada, tipo_envio, estado, codigo_producto)
                            VALUES (?, ?, ?, ?, ?)""",
                            (numero_cliente, fecha_completa, tipo, 'PENDIENTE', codigo_producto)
                        )
                        envios_creados += 1
                    
                    except Exception as e:
                        errores += 1
                        self.log(f"Error cliente {numero_cliente}: {str(e)}", "ERROR")

                messagebox.showinfo("Resumen", 
                    f"Envíos creados: {envios_creados}\n"
                    f"Errores: {errores}\n"
                    f"Clientes sin stock: {len(clientes) - envios_creados - errores}")

            else:
                messagebox.showerror("Error", "Tipo de envío no reconocido")

        except Exception as e:
            messagebox.showerror("Error de programación", str(e))


    def limpiar_logs(self):
        self.logs_text.delete('1.0', tk.END)
        self.logs_counter = 0

    def log(self, message: str, level: str = 'INFO'):
        """Registrar mensaje en el panel de debug"""
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'SUCCESS']
        if level not in levels  :
            level = 'INFO'
    
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
    
    # Rotar logs si excede el máximo
        if self.log_counter >= self.max_logs:
            self.limpiar_logs()
    
        self.logs_text.configure(state='normal')
        self.logs_text.insert(tk.END, log_entry, level)
        self.logs_text.see(tk.END)  # Auto-scroll
        self.logs_text.configure(state='disabled')
        self.log_counter += 1

    
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
    
    def attempt_auto_connect(self):
        """Intentar conexión automática con credenciales guardadas desencriptadas."""
        try:
            settings = self.load_connection_settings()
            if not settings:
                self.show_settings()
                return

            server = settings.get('server')
            database = settings.get('database')
            user = settings.get('user')
            # Se asume que la contraseña temporal ya se guarda/encripta correctamente
            password = self.cred_manager.get_temp_password()
            # Obtener token desde keyring
            api_token = self.cred_manager.get_whatsapp_token()

            if server and database:
                total_start = time.perf_counter()
                if self.db_manager.connect(server, database, user, password):
                    self.update_status('connected', server=server, api_token=api_token)
                    self.log("Conexión a BD exitosa", "SUCCESS")
                    self.search_records()

                    if self.modules_enabled.get("stock", False):
                        self.load_stock_filters()
                        self.actualizar_alertas_stock(force_refresh=True)

                        threading.Thread(target=self._init_jerarquia_async, daemon=True).start()

                    total_elapsed = time.perf_counter() - total_start
                    self.log(f"🏁 App inicializada en {total_elapsed:.2f}s", "INFO")

                return

            self.show_settings()
        except Exception as e:
            self.audit_log.log_event(
                "AUTO_CONNECT_FAILED",
                os.getlogin(),
                "FAILED",
                ErrorCode.DB_CONNECTION_FAILED
            )
            self.show_settings()

    def cargar_eventos_calendario(self):
        try:
            if not self.db_manager.conn:
                return
            eventos = self.db_manager.fetch_data(
                "SELECT fecha_programada, estado, tipo_envio FROM envios_programados"
            )
        
            self.cal.calevent_remove('all')
        
            for fecha_obj, estado, tipo in eventos:  # Recibir directamente el datetime
                fecha = fecha_obj.date()  # Convertir datetime a date
                tags = 'pendiente' if estado == 'PENDIENTE' else 'completado'
                self.cal.calevent_create(
                    fecha,
                    f"{tipo} - {estado}",
                    tags=tags
                )
        
            self.cal.tag_config('pendiente', background='#FFD700', foreground='black')
            self.cal.tag_config('completado', background='#90EE90', foreground='black')
        
        except Exception as e:
            self.log(f"Error cargando eventos: {str(e)}", "ERROR")

    def setup_records_tab(self):
        # Panel principal
        main_frame = ttk.Frame(self.records_tab)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel izquierdo (Formulario)
        form_frame = ttk.Frame(main_frame, width=300)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        # Campos de entrada
        self.create_input_fields(form_frame)
        
        # Panel derecho (Lista)
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        
        # Treeview
        self.create_records_list(list_frame)

    def create_input_fields(self, parent):
        # Campo Número Cliente
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, pady=5)
        ttk.Label(input_frame, text="Número Cliente:").pack(side=tk.LEFT)
        self.num_cliente = ttk.Entry(input_frame)
        self.num_cliente.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        
        # Campo Código Producto
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, pady=5)
        ttk.Label(input_frame, text="Código Producto:").pack(side=tk.LEFT)
        self.cod_producto = ttk.Entry(input_frame)
        self.cod_producto.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        
        # Descripción
        self.descripcion = ttk.Entry(parent, state="readonly")
        self.descripcion.pack(fill=tk.X, pady=5)
        
        # Botones de acción
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=10)
        
        actions = [
        # (Texto, Comando, Clave)
        ('🔍 Buscar', self.search_records, 'btn_buscar'),
        ('💾 Guardar', self.save_record, 'btn_guardar'),
        ('🔄 Actualizar', self.update_record, 'btn_actualizar'),
        ('🗑 Eliminar', self.delete_record, 'btn_eliminar')
        ]
    
    # Ahora cada iteración recibirá los 3 valores necesarios
        for text, cmd, key in actions:
            btn = ttk.Button(btn_frame, text=text, command=cmd)
            btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            self.buttons[key] = btn

        # Filtro por fecha
        fecha_frame = ttk.Frame(parent)
        fecha_frame.pack(fill=tk.X, pady=5)
    
        ttk.Label(fecha_frame, text="Desde:").pack(side=tk.LEFT)
        self.fecha_inicio = DateEntry(fecha_frame)
        self.fecha_inicio.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(fecha_frame, text="Hasta:").pack(side=tk.LEFT)
        self.fecha_fin = DateEntry(fecha_frame)
        self.fecha_fin.pack(side=tk.LEFT, padx=5)
    
        ttk.Button(
            fecha_frame, 
            text="Filtrar por Fecha", 
            command=self.buscar_por_fecha
        ).pack(side=tk.RIGHT)

    def create_records_list(self, parent):
        # Treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Número", "Código"), show="headings")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        # Configurar columnas
        self.tree.heading("ID", text="ID")
        self.tree.heading("Número", text="Número Cliente")
        self.tree.heading("Código", text="Código Producto")
        
        self.tree.column("ID", width=80, anchor=tk.CENTER)
        self.tree.column("Número", width=150)
        self.tree.column("Código", width=200)
        
        # Layout
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def create_status_panel(self):
        status_frame = ttk.Frame(self.root, style="Status.TFrame")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Indicadores de estado
        self.db_status = ttk.Label(status_frame, text="BD: Desconectado", foreground="red")
        self.db_status.pack(side=tk.LEFT, padx=10)
        
        self.api_status = ttk.Label(status_frame, text="API: Inactiva", foreground="orange")
        self.api_status.pack(side=tk.LEFT)
        
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
        self.help_tooltips.add_tooltip(self.num_cliente, "Número de cliente (1-11 dígitos)")
        self.help_tooltips.add_tooltip(self.cod_producto, "Código de producto (buscar en base de datos)")
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
    
        modules_frame = ttk.Frame(notebook)
        notebook.add(modules_frame, text="Módulos")

        self.mod_vars = {}
        for idx, (key, label) in enumerate([
            ("envio_mensajes", "Envío de Mensajes"),
            ("estadisticas",   "Estadísticas"),
            ("calendario",     "Calendario"),
            ("stock",          "Alertas Stock")
        ]):
            var = tk.BooleanVar(value=self.modules_enabled.get(key, False))
            cb  = ttk.Checkbutton(modules_frame, text=label, variable=var)
            cb.grid(row=idx, column=0, sticky="w", padx=10, pady=5)
            self.mod_vars[key] = var

    # Botón para guardar módulos
        ttk.Button(
            modules_frame,
            text="Guardar Módulos",
            command=self._save_modules_config
        ).grid(row=len(self.mod_vars), column=0, sticky="e", pady=10, padx=10)

    def on_settings_close(self):
        """Cierre seguro de la ventana"""
        if self.settings_window:
            self.settings_window.destroy()
        self.settings_window = None  # Limpiar referencia

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

            if self.db_manager.connect(server, database, user, password):
                self.save_connection_settings(server, database, user, token)
                self.update_status('connected', server=server, api_token=token)
                self.settings_window.destroy()
                self.log("Conexión a BD exitosa", "SUCCESS")
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
        """Actualizar la barra de estado principal"""
        status_config = {
            'connected': {
                'text': f"BD: Conectado" if server else "BD: Conectado",
                'color': "green"
            },
            'error': {
                'text': f"Error: {message[:50]}..." if len(message) > 50 else f"Error: {message}",
                'color': "red"
            },
            'action': {
                'text': message,
                'color': "blue"
            },
            'disconnected': {
                'text': "BD: Desconectado",
                'color': "orange"
            }
        }
        
        config = status_config.get(status_type, {'text': "Estado desconocido", 'color': "gray"})
        self.db_status.config(text=config['text'], foreground=config['color'])
        
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

    class NotificationManager:
        def __init__(self, root):
            self.root = root
        
        def show_success(self, message):
            self._show_notification("✓ Éxito", message, "#d4edda")
        
        def show_error(self, message):
            self._show_notification("⚠ Error", message, "#f8d7da")
        
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
            boton.config(state=estado)
        # Cambiar color para mejor feedback visual
            boton.config(style="TButton" if estado == 'normal' else "Disabled.TButton")

        

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
                "INSERT INTO clientes (numero_cliente, C_CODIGO) VALUES (?, ?)",
                (self.num_cliente.get(), self.cod_producto.get())
            )
            
            self.show_temp_notification("¡Guardado exitosamente!")

            # Restablecer el estado a 'Conectado' después de 3 segundos
            self.root.after(3000, lambda: self.update_status('connected'))

            self.search_records()
            self.clear_inputs()
        except Exception as e:
            self.notification_manager.show_success("Error", str(e))
            self.show_temp_notification("Error al guardar", duration=5000)

    def search_records(self):
        if not self.db_manager.conn:  # <-- Agrega esta validación
            self.notification_manager.show_error("Error", "No hay conexión a la base de datos")
      
            self.show_settings()  # Opcional: Abrir ventana de conexión
            return
        try:
            self.tree.delete(*self.tree.get_children())
            num = self.num_cliente.get().strip()
            cod = self.cod_producto.get().strip()

            query = "SELECT id, numero_cliente, C_CODIGO FROM clientes"
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

    def enviar_a_todos(self):
        self.log("Iniciando proceso de envío masivo...", "INFO")
        if self.enviando: return
        self.toggle_buttons('disabled')
            
    
        try:
            records = self.db_manager.fetch_data("SELECT numero_cliente, C_CODIGO FROM clientes")
            
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
        
            # Configurar UI de progreso
            self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
            self.progress.pack(pady=10)
            self.lbl_progreso = ttk.Label(self.root, text="Preparando...")
            self.lbl_progreso.pack()
            self.progress["maximum"] = self.total

            self.root.after(1000, self.procesar_envio_masivo)
            
        except Exception as e:
            self.log(f"Error en envío masivo: {str(e)}", "ERROR")
            self.toggle_buttons('normal')
            messagebox.showerror("Error", f"Error obteniendo clientes: {str(e)}")
            self.enviando = False
        
        

    

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

                self.db_manager.execute_query("DELETE FROM clientes WHERE id = ?", (record_id,))
                self.update_status('action', message="Registro eliminado")
                self.search_records()
                self.clear_inputs() 
            except Exception as e:
                messagebox.showerror("Error", str(e))

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
                "UPDATE clientes SET numero_cliente = ?, C_CODIGO = ? WHERE id = ?",
                (self.num_cliente.get(), self.cod_producto.get(), record_id)
            )
            self.update_status('action', message="Registro actualizado")

            # Restablecer el estado a 'Conectado' después de 3 segundos
            self.root.after(3000, lambda: self.update_status('connected'))

            self.search_records()
            self.clear_inputs()
        except Exception as e:
            messagebox.showerror("Error", str(e))

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
            query_numero_cliente = "SELECT numero_cliente FROM clientes WHERE C_CODIGO = ?"
            result_numero_cliente = self.db_manager.fetch_data(query_numero_cliente, (clean_codigo,))
            if not result_numero_cliente:
                messagebox.showinfo("Error", "Número de cliente no encontrado")
                return
        
            numero_cliente = result_numero_cliente[0][0]

            self.enviar_mensaje_whatsapp(numero_cliente, [descripcion])
            self.show_temp_notification("Enviado Exitosamente")
    
        except Exception as e:
            messagebox.showerror("Error", f"Error obteniendo descripción o cantidad: {str(e)}")

    def procesar_envio_programado(self, id_envio, numero_cliente):
        """Envía un mensaje programado usando plantillas de WhatsApp y actualiza el estado"""
        try:
            # 1. Obtener datos extendidos del envío
            envio_data = self.db_manager.fetch_data(
                "SELECT tipo_envio, codigo_producto FROM envios_programados WHERE id = ?", 
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
                    "UPDATE envios_programados SET estado = 'ENVIADO' WHERE id = ?",
                    (id_envio,)
                )
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
            return False
        finally:
            self.log(f"Finalizado el procesamiento del envío {id_envio} para el cliente {numero_cliente}", "INFO")
            error_code=ErrorCode.WHATSAPP_API_FAILURE
            return False

    def procesar_envio_masivo(self,):

        try:
            if self.actual == 0:
                # Crear tabla temporal si no existe
                self.db_manager.execute_query("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'TEMP_ENVIO')
                CREATE TABLE TEMP_ENVIO (
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
                                    "INSERT INTO TEMP_ENVIO (numero_cliente, descripcion) VALUES (?, ?)",
                                    (numero, desc_result[0][0])
                                )
        finally:
            if self.actual >= self.total or self.enviando == False:
                self.toggle_buttons('normal')
                self.enviando = False
                self.progress.destroy()
                self.lbl_progreso.destroy()
                self.log("Proceso de envío completado", "SUCCESS")
                return

        numero = self.clientes_lista[self.actual][0]
    
        # Obtener todos los productos del cliente desde la tabla temporal
        productos_result = self.db_manager.fetch_data(
            "SELECT descripcion FROM TEMP_ENVIO WHERE numero_cliente = ?", (numero,)
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
        self.db_manager.execute_query("DELETE FROM TEMP_ENVIO WHERE numero_cliente = ?", (numero,))
    
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

if __name__ == "__main__":
    root = tk.Tk()
    app = DatabaseApp(root)
    root.mainloop() 