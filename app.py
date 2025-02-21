import pyodbc
import tkinter as tk
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
import requests
from enum import Enum


CONFIG_FILE = 'db_config.ini'


class ErrorCode(Enum):
    # Errores de base de datos (1000-1999)
    DB_CONNECTION_FAILED = (1001, "Error de conexión a la base de datos")
    DB_QUERY_EXECUTION = (1002, "Error al ejecutar consulta SQL")
    DB_TABLE_CREATION = (1003, "Error creando tabla en la base de datos")
    DB_RECORD_NOT_FOUND = (1004, "Registro no encontrado")
    
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


        #Monitorear actividad
        
        root.bind("<Key>", self.update_activity)
        root.bind("<Button>", self.update_activity)
        root.bind("<Motion>", self.update_activity)

    def update_activity(self, event=None):
        self.last_activity = time.time()
        if not self.session_active:
            self.start_session()

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

    def connect(self, server, database, user, password):
        conn_str = (
        f"DRIVER={{SQL Server}};"
        f"SERVER={server};"
        "Encrypt=no;"          # Conexión SSL obligatoria
        "TrustServerCertificate=no;"  # No confiar en el certificado
          "Connection Timeout=15;"
    )
        if user:
            conn_str += f"UID={user};PWD={password or ''};"
        else:
            conn_str += "Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=no;"

        if database:
            try:
                temp_conn = pyodbc.connect(conn_str)
                temp_cursor = temp_conn.cursor()
                temp_cursor.execute(f"""
                    IF NOT EXISTS (
                        SELECT name FROM sys.databases 
                        WHERE name = '{database}'
                    )
                    CREATE DATABASE {database}
                """)
                temp_conn.commit()
                temp_conn.close()
            except pyodbc.Error as e:
                error_msg = f"{ErrorCode.DB_CONNECTION_FAILED}: {str(e)}"
                raise Exception(error_msg) from e
            finally:
                conn_str += f"DATABASE={database}"

        try:
            self.conn = pyodbc.connect(conn_str)
            self.cursor = self.conn.cursor()
            self.connected_server = server
            self.create_table()
            return True
        except pyodbc.Error as e:
            error_msg = f"{ErrorCode.DB_CONNECTION_FAILED}: {str(e)}"
            raise Exception(error_msg) from e


    def create_table(self):
        try:
            self.cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='clientes' AND xtype='U')
                CREATE TABLE clientes (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    numero_cliente NVARCHAR(50) NOT NULL,
                    C_CODIGO NVARCHAR(15) NOT NULL
                )
            """)
            self.conn.commit()
        except pyodbc.Error as e:
            error_msg = f"{ErrorCode.DB_TABLE_CREATION}: {str(e)}"
            raise Exception(error_msg) from e

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
        if not self.conn:  # <-- Validación crítica
            error_msg = f"{ErrorCode.DB_CONNECTION_FAILED}: No hay conexión activa"
            raise Exception(error_msg)
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except pyodbc.Error as e:
            error_msg = f"{ErrorCode.DB_QUERY_EXECUTION}: {str(e)}"
            raise Exception(error_msg) from e

class DatabaseApp:
    def __init__(self, root):
        self.cred_manager = SecureCredentialsManager()
        self.buttons = {}
        self.enviando = False
        self.session = SessionManager(root)
        self.session.start_session()
        self.root = root
        self.audit_log = AuditLogger()
        self.status_messages = {
            'default': "Desconectado",
            'connected': "Conectado",
            'error': "Error: {message}",
            'action': "Acción: {message}"
        }
        self.root.title("Gestión de Clientes")
        self.root.geometry("800x550")
        self.db_manager = DatabaseManager()
        self.settings_window = None
        self.show_pwd_var = None
        self.httpd = None
        self.setup_styles()
        self.create_widgets()
        self.setup_bindings()
        self.attempt_auto_connect()
        root.tk_setPalette(background='#ffffff')
        root.bind("<Visibility>", self.set_security_headers)

    def abrir_logs(self):
        # Verificar si el servidor HTTP ya está en ejecución
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
    # Definir puerto para el servidor
        puerto = 8000

    # Configurar el servidor HTTP
        handler = http.server.SimpleHTTPRequestHandler
        httpd = socketserver.TCPServer(("", puerto), handler)

    # Ejecutar el servidor en un hilo separado
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

    # Abrir logs.html en el navegador
        webbrowser.open(f'http://localhost:{puerto}/logs.html')


    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        #paletade colores
        self.colors ={
            'primary': '#2c3e50',
            'secondary': '#3498db',
            'success': '#27ae60',
            'danger': '#e74c3c',
            'light': '#ecf0f1',
            'dark': '#2c3e50'
        }

        self.style.configure("Horizontal.TProgressbar",
        thickness=20,
        troughcolor='#e0e0e0',
        troughrelief='flat',
        background='#4CAF50',
        lightcolor='#C8E6C9',
        darkcolor='#388E3C'
        )

        # Configurar fuentes
        self.title_font = font.Font(family='Segoe UI', size=14, weight='bold')
        self.base_font = font.Font(family='Segoe UI', size=10)

        # Configurar estilos de widgets
        self.style.configure('TFrame', background=self.colors['light'])
        self.style.configure('TLabel', background=self.colors['light'], font=self.base_font)
        self.style.configure('TButton', font=self.base_font, padding=6)
        self.style.configure('Header.TLabel', 
                           font=self.title_font, 
                           background=self.colors['primary'],
                           foreground='white',
                           padding=10)
        
        self.style.map('TButton',
                     background=[('active', self.colors['secondary'])],
                     foreground=[('active', 'white')])

    def save_connection_settings(self, server, database, user, token=None):
        config = configparser.ConfigParser()
        config['Connection'] = {
            'Server': self.cred_manager.encrypt(server),
            'Database': self.cred_manager.encrypt(database),
            'User': self.cred_manager.encrypt(user)
        }

        if token is not None:
            self.cred_manager.store_whatsapp_token(token)

        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        # Guardar token si se proporcionó
  
    def load_connection_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                config = configparser.ConfigParser()
                config.read(CONFIG_FILE)

                return {
                    'server': self.cred_manager.decrypt(config['Connection']['Server']),
                    'database': self.cred_manager.decrypt(config['Connection']['Database']),
                    'user': self.cred_manager.decrypt(config['Connection']['User'])
                }
            except Exception as e:
                self.audit_log.log_event(
                    "CONFIG_LOAD_ERROR", os.getlogin(), "FAILED",
                    ErrorCode.INVALID_CONFIG
                )
                error_msg = f"{ErrorCode.INVALID_CONFIG}: {str(e)}"
                messagebox.showerror("Error de Configuración", error_msg)
                os.remove(CONFIG_FILE)
                return None
        return None
    
    
    def set_security_headers(self, event=None):
        root = self.root
        root.wm_attributes("-fullscreen", False)
        root.wm_attributes("-toolwindow", False)
        root.wm_attributes("-disabled", False)
        root.wm_attributes("-topmost", False)
        root.update_idletasks()    

    def attempt_auto_connect(self):
        settings = self.load_connection_settings()
        if settings:
            try:
                if self.db_manager.connect(
                    settings['server'],
                    settings['database'],
                    settings['user'],
                    ""
                ):
                    self.status_label.config(
                        text=f"✅Conectado", 
                        #foreground="green"#
                        )
                    self.search_records()
            except Exception as e:
                self.status_label.config(
                    text=f"⚠ Error reconectando: {str(e)}",
                    foreground="orange"
                )                    
                

    def create_widgets(self):
        # Barra superior
        header = ttk.Frame(self.root, style='Header.TFrame')
        header.pack(fill=tk.X)

        ttk.Label(header,
                text="Gestión de Clientes - Corporativo",
                style='Header.TLabel').pack(side=tk.LEFT, padx=10)
        
        # Botón de configuración
        self.settings_btn = ttk.Button(header,
                                    text="⚙",
                                    command=self.show_settings,
                                    style='Toolbutton.TButton')
        self.settings_btn.pack(side=tk.RIGHT, padx=10)

        self.logs_btn = ttk.Button(header,
                            text="🔍",
                            command=self.abrir_logs,
                            style='Toolbutton.TButton')
        self.logs_btn.pack(side=tk.RIGHT, padx=5)

        # Panel principal
        main_frame = ttk.Frame(self.root, style='Card.TFrame')
        main_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        # Campos de datos
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=0, column=0, padx=15, pady=15, sticky='ew')
        
        # Configurar el grid para 3 filas y 2 columnas
        input_frame.columnconfigure(1, weight=1)
        
        # Fila 0 - Número Cliente
        ttk.Label(input_frame, text="Número Cliente:").grid(row=0, column=0, sticky='w', pady=5)
        self.num_cliente = ttk.Entry(input_frame, width=25, font=self.base_font)
        self.num_cliente.grid(row=0, column=1, padx=10, pady=5, sticky='ew')

        # Fila 1 - Código Producto con botón de búsqueda
        ttk.Label(input_frame, text="Código Producto:").grid(row=1, column=0, sticky='w', pady=5)
        
        codigo_frame = ttk.Frame(input_frame)
        codigo_frame.grid(row=1, column=1, padx=10, pady=5, sticky='ew')
        
        self.cod_producto = ttk.Entry(codigo_frame, width=20, font=self.base_font)
        self.cod_producto.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        search_btn = ttk.Button(codigo_frame, 
                            text="🔍", 
                            width=3,
                            command=self.buscar_descripcion)
        search_btn.pack(side=tk.LEFT, padx=5)

        # Fila 2 - Descripción
        ttk.Label(input_frame, text="Descripción:").grid(row=2, column=0, sticky='w', pady=5)
        self.descripcion = ttk.Entry(input_frame, 
                                font=self.base_font, 
                                state='readonly',
                                style='Descripcion.TEntry')
        self.descripcion.grid(row=2, column=1, padx=10, pady=5, sticky='ew')

        # Botones de acciones
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, pady=10)
        
        self.buttons = {
        'search': {'text': '🔍 Buscar', 'command': self.search_records},
        'save': {'text': '💾 Guardar', 'command': self.save_record},
        'update': {'text': '🔄 Actualizar', 'command': self.update_record},
        'delete': {'text': '🗑 Eliminar', 'command': self.delete_record},
        'Notificar': {'text': '🌐 Notificar', 'command': self.notificar},
        'EnviarTodos': {'text': '🌐 Enviar a Todos', 'command': self.enviar_a_todos}
        }
        
        for idx, (key, btn_data) in enumerate(self.buttons.items()):
            btn = ttk.Button(
                btn_frame, 
                text=btn_data['text'], 
                command=btn_data['command'],
                style='Action.TButton'
            )   
            btn.grid(row=0, column=idx, padx=5)
            self.buttons[key]['widget'] = btn  # Almacenar referencia al widget

        # Tabla de resultados
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=2, column=0, padx=15, pady=15, sticky='nsew')
        
        self.tree = ttk.Treeview(tree_frame, 
                            columns=("ID", "Número", "Código"), 
                            show="headings", 
                            style='Custom.Treeview')

        # Configuración de scrollbar y columnas
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        # Configurar pesos del grid para expansión
        main_frame.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        columns_config = [
            ("ID", 80),
            ("Número", 150),
            ("Código", 150),
        ]
        
        for col_text, width in columns_config:
            self.tree.heading(col_text, text=col_text)
            self.tree.column(col_text, width=width, anchor=tk.W)

        # Configuración adicional de estilos
        self.style.configure('Descripcion.TEntry', 
                        foreground='#444444',
                        background='#f0f0f0',
                        font=('Segoe UI', 9))

        # Barra de estado
        self.create_status_bar()

    def create_status_bar(self):
        # Marco de estado
        status_frame = ttk.Frame(self.root, style='Status.TFrame')
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

        # Icono de estado
        self.status_icon = ttk.Label(status_frame, text="", width=3)
        self.status_icon.pack(side=tk.LEFT, padx=(10, 0))

        # Mensaje principal
        self.status_label = ttk.Label(
            status_frame, 
            text=self.status_messages['default'],
            style='Status.TLabel'
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Notificaciones temporales
        self.temp_notification = ttk.Label(
            status_frame,
            style='Notification.TLabel',
            foreground='white'
        )
        self.temp_notification.pack(side=tk.RIGHT, padx=(0, 10))

    def update_status(self, status_type: str, **kwargs):
        """Actualiza la barra de estado principal"""
        message = self.status_messages[status_type].format(**kwargs)

        # Configurar icono y color
        icon_config = {
            'connected': ('✅', '#27ae60'),
            'error': ('⚠', '#e74c3c'),
            'action': ('▶', '#3498db'),
            'default': ('', '#2c3e50')
        }
            #27ae60 - Verde
            #e74c3c - Rojo
            #3498db - Azul
            #2c3e50 - Gris oscuro

        icon, color = icon_config.get(status_type, ('', '#3498db')) # Valor por defecto

        self.status_icon.config(text=icon, foreground=color)
        self.status_label.config(text=message)

    def show_temp_notification(self, message: str, duration: int = 3000) -> None:
        """Muestra una notificación con desvanecimiento suave"""
        # Configuración inicial
        start_color = (52, 152, 219)    # #3498db en RGB
        end_color = (248, 249, 250)     # #f8f9fa en RGB
        steps = 15                      # Más pasos para mayor suavidad
        interval = 50                   # Intervalo más corto (50ms)
        current_step = [0]              # Usamos lista para modificar en closure

        # Mostrar mensaje inicial
        self.temp_notification.config(
            text=message,
            foreground='white',
            background='#3498db'
        )

        def interpolate_color(step):
            """Interpola linealmente entre dos colores RGB"""
            r = start_color[0] + (end_color[0] - start_color[0]) * step / steps
            g = start_color[1] + (end_color[1] - start_color[1]) * step / steps
            b = start_color[2] + (end_color[2] - start_color[2]) * step / steps
            return f'#{int(r):02x}{int(g):02x}{int(b):02x}'

        def animate():
            if current_step[0] <= steps:
                color = interpolate_color(current_step[0])
                self.temp_notification.config(background=color)
                current_step[0] += 1
                self.root.after(interval, animate)
            else:
                self.temp_notification.config(text="")

        # Iniciar animación después del tiempo de visualización
        self.root.after(duration, animate)

    def setup_bindings(self):
        self.tree.bind("<Double-1>", self.on_tree_double_click)

    def show_settings(self):

         # Ventana de configuración 
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Configuración de Conexión")
        self.settings_window.geometry("550x300")

        # Contenedor principal
        container = ttk.Frame(self.settings_window)
        container.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Configurar grid responsivo
        self.settings_window.columnconfigure(0, weight=1)
        self.settings_window.rowconfigure(0, weight=1)

        # Campos de formulario
        ttk.Label(container, text="Servidor*:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.server_entry = ttk.Entry(container, width=25)
        self.server_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(container, text="Base de Datos:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        self.db_entry = ttk.Entry(container, width=20)
        self.db_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(container, text="Usuario:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.user_entry = ttk.Entry(container, width=25)
        self.user_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(container, text="Contraseña:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.pwd_entry = ttk.Entry(container, show="*", width=20)
        self.pwd_entry.grid(row=1, column=3, padx=5, pady=5, sticky=tk.EW)

        # Campo para el token de WhatsApp
        ttk.Label(container, text="Token WhatsApp:").grid(row=3, column=0, sticky='w', pady=5)
        self.token_entry = ttk.Entry(container, show="*", width=25)  # Asegurar esta línea
        self.token_entry.grid(row=3, column=1, padx=5, pady=5, sticky='ew')

        try:
            saved_token = self.cred_manager.get_whatsapp_token() or ""
            self.token_entry.insert(0, saved_token)
        except Exception as e:
            print(f"Error cargando token: {str(e)}")
            self.token_entry.insert(0, "")
        # Checkbox para mostrar contraseña
        self.show_pwd_var = tk.BooleanVar()
        ttk.Checkbutton(container, 
                  text="Mostrar contraseña",
                  variable=self.show_pwd_var,
                  command=self.toggle_password).grid(row=2, column=3, padx=5, pady=5, sticky=tk.W)
        
        
        settings = self.load_connection_settings()
        if settings:
            self.server_entry.insert(0, settings['server'])
            self.db_entry.insert(0, settings['database'])
            self.user_entry.insert(0, settings['user'])  

        # Botones de conexión
        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=10, sticky=tk.E)
    
        ttk.Button(btn_frame, text="Cancelar", command=self.settings_window.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Conectar", command=self.connect_db).pack(side=tk.LEFT, padx=5)

    def create_system_status_frame(self):
        status_frame = ttk.Frame(self.root)
        self.lbl_db_status = ttk.Label(status_frame, text="DB: Desconectado")
        self.lbl_api_status = ttk.Label(status_frame, text="API: Inactiva")
        self.btn_refresh_status = ttk.Button(status_frame, text="Actualizar", command=self.check_system_status)
    

    def toggle_buttons(self, estado):
        for btn_data in self.buttons.values():
            btn_data['widget'].config(state=estado)
        self.settings_btn.config(state=estado)
        self.logs_btn.config(state=estado)

        

    def toggle_password(self):
        if self.show_pwd_var.get():
            self.pwd_entry.config(show="")
        else:
            self.pwd_entry.config(show="*")

    def connect_db(self):
        server = self.server_entry.get()
        database = self.db_entry.get()
        user = self.user_entry.get()
        password = self.pwd_entry.get()
        token = self.token_entry.get()
    
        if not password:
            password = self.cred_manager.get_temp_password() or ''
    
        if password:
            self.cred_manager.store_temp_password(password)

        if not server:
            messagebox.showwarning("Error", "El campo Servidor es obligatorio")
            return

        try:
            if self.db_manager.connect(server, database, user, password):
                self.save_connection_settings(server, database, user, token)
                self.update_status('connected', server=server)
                self.settings_window.destroy()
                self.show_temp_notification("Conexión exitosa")
                self.search_records()
            
        except Exception as e:
            self.audit_log.log_event(
                "DB_CONNECTION_ATTEMPT", os.getlogin(), "FAILED",
                ErrorCode.DB_CONNECTION_FAILED
            )
            self.update_status('error', message=str(e))
            self.show_temp_notification("Error de conexión", duration=5000)
            self.settings_window.lift()

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
                messagebox.showwarning("Error", str(ErrorCode.DANGEROUS_INPUT))
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
            self.update_status('action', message="Registro guardado correctamente ✅")
            self.show_temp_notification("¡Guardado exitosamente!")

            # Restablecer el estado a 'Conectado' después de 3 segundos
            self.root.after(3000, lambda: self.update_status('connected'))

            self.search_records()
            self.clear_inputs()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.show_temp_notification("Error al guardar", duration=5000)

    def search_records(self):
        if not self.db_manager.conn:  # <-- Agrega esta validación
            messagebox.showerror("Error", "No hay conexión a la base de datos")
      
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
                self.clear_inputs            
            
                
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def enviar_a_todos(self):
        if self.enviando: return
        self.toggle_buttons('disabled')
            
    
        try:
            records = self.db_manager.fetch_data("SELECT numero_cliente, C_CODIGO FROM clientes")
            
            # Agrupar clientes
            clientes_dict = {}
            for numero, codigo in records:
                if numero not in clientes_dict:
                    clientes_dict[numero] = []
                clientes_dict[numero].append(codigo)
        
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

            self.root.after(1000, self.procesar_envio)
        
        except Exception as e:
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
                self.clear_inputs   
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

    def buscar_descripcion(self):
        """Obtiene la descripción y actualiza el campo correspondiente"""
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

            # Consultar descripción
            query = "SELECT C_DESCRI FROM dbo.MA_PRODUCTOS WHERE C_CODIGO = ?"
            result = self.db_manager.fetch_data(query, (clean_codigo,))
            descripcion = result[0][0] if result else "Descripción no encontrada"
            self.actualizar_descripcion(descripcion)

             # Consultar cantidad
            query_cantidad = "SELECT n_cantidad FROM dbo.MA_DEPOPROD WHERE c_codarticulo = ? AND c_coddeposito = '0301'"
            result_cantidad = self.db_manager.fetch_data(query_cantidad, (clean_codigo,))
            if result_cantidad and result_cantidad[0][0] > 0:
                cantidad = int(result_cantidad[0][0])
                self.show_temp_notification(f"Cantidad: {cantidad}")
            else:
                self.show_temp_notification(f"Cantidad no disponible o igual a 0")  
            
        except Exception as e:
            self.actualizar_descripcion("Error en consulta")
            messagebox.showerror("Error", f"Error obteniendo descripción: {str(e)}")
    
                       
    def on_tree_double_click(self, event):
        """Manejo de doble click en la tabla con limpieza de datos"""
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

    def procesar_envio(self):
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
    
        if self.actual >= self.total:
            self.toggle_buttons('normal')
            self.enviando = False
            self.progress.destroy()
            self.lbl_progreso.destroy()
            messagebox.showinfo("Éxito", "Todos los mensajes han sido enviados")
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
        self.root.after(7000, self.procesar_envio)

    def enviar_mensaje_whatsapp(self, numero_cliente, descripcion):
        whatsapp_token = self.cred_manager.get_whatsapp_token()
        if not whatsapp_token:
            self.audit_log.log_event(
                "WHATSAPP_API_ERROR", os.getlogin(), "FAILED",
                ErrorCode.INVALID_API_TOKEN
            )
            messagebox.showerror("Error", str(ErrorCode.INVALID_API_TOKEN))
            self.show_settings()
            return
        # Formatear número telefónico (eliminar caracteres no numéricos)
        numero_limpio = re.sub(r'\D', '', numero_cliente)
        # Si el número inicia con '0', se elimina dicho dígito
        if numero_limpio.startswith('0'):
            numero_limpio = numero_limpio[1:]
        numero_formateado = '58' + numero_limpio
    
        try:
            MAX_LENGTH_PER_ITEM = 45  # Deja espacio para número de secuencia
            MAX_ITEMS = 10  # Máximo de productos por mensaje
            MAX_TOTAL_LENGTH = 1024 #Limite de Whatsapp
            SEPARADOR = "  •  "  # Usar espacios y viñeta simple

        # Procesar descripciones
            productos_limpios = []
            adicionales = len(descripcion) - MAX_ITEMS if len(descripcion) > MAX_ITEMS else 0

            

            for idx, desc in enumerate(descripcion[:MAX_ITEMS], 1):
                clean_desc = re.sub(r'[\n\t]', ' ', desc)

                truncated = (clean_desc[:MAX_LENGTH_PER_ITEM-3] + '...') if len(clean_desc) > MAX_LENGTH_PER_ITEM else clean_desc
                productos_limpios.append(f"{idx}. {truncated}")

            # Unir todos los items con separador
            lista_productos = SEPARADOR.join(productos_limpios)

            if adicionales > 0:
                lista_productos += f"{SEPARADOR}... (+{adicionales} productos más)"

                
            # Configuración de la API
            url = "https://graph.facebook.com/v21.0/490677417472051/messages"
            token = whatsapp_token
        
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        
        # Construir el mensaje de texto simple
            payload = {
                "messaging_product": "whatsapp",
                "to": numero_formateado,
                "type": "template",
                "template": {
                    "name": "alerta_stock",  # Nombre de tu plantilla aprobada
                    "language": {
                        "code": "es"  # Código de idioma, ajusta según sea necesario
                    },
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {
                                    "type": "text",
                                    "text": lista_productos  # Este valor reemplazará el marcador {{1}} en tu plantilla
                                }
                            ]
                        }
                    ]
                }
            }
        
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                error_data = response.json().get('error', {})
                error_msg = error_data.get('message', 'Error desconocido')
                error_details = error_data.get('error_data', {}).get('details', '')
                raise Exception(f"API Error:({error_msg}) - {error_details}")
        
            # Registrar en auditoría
            self.audit_log.log_event(
                "ENVIO_MASIVO", 
                os.getlogin(), 
                f"Enviado a {numero_formateado}"
            )
    
        except Exception as e:
            self.audit_log.log_event(
                "ENVIO_MASIVO_ERROR",
                os.getlogin(),
                f"enviado a {numero_formateado}: {str(e)}"
            )
            messagebox.showerror("Error", f"{str(e)}")
           
    def actualizar_descripcion(self, texto):
        self.descripcion.config(state='normal')
        self.descripcion.delete(0, tk.END)
        self.descripcion.insert(0, texto)
        self.descripcion.config(state='readonly')

if __name__ == "__main__":
    root = tk.Tk()
    app = DatabaseApp(root)
    root.mainloop()