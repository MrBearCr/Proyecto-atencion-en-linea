"""
Gestor de base de datos para la aplicación PAL
"""
import pyodbc
import configparser
import time
import threading
from typing import List, Dict, Tuple, Any
from ..core.errors import ErrorCode
from ..core.credentials import SecureCredentialsManager

class DatabaseManager:
    def __init__(self, credentials_manager=None):
        self.conn = None
        self.cursor = None
        self.connected_server = ""
        self.config = configparser.ConfigParser()
        self.server = None
        self.database = None
        self.user = None
        self.password = None
        self.credentials_manager = credentials_manager
        # Pool de conexiones para hilos paralelos
        self._connection_pool = {}
        # Lock para acceso thread-safe al pool
        import threading
        self._pool_lock = threading.Lock()
        # Lock para conectar/reconectar de forma serializada
        self._connect_lock = threading.Lock()
        
        # Estado de inicialización del esquema (evita loops o re-ejecuciones innecesarias)
        self._schema_initialized = False

        # Driver y opciones determinados en el primer connect()
        self.current_odbc_driver = None
        self.current_encrypt_opts = ""

    def _log(self, message: str, level: str = 'INFO'):
        """Logger interno con prefijo para identificar origen en consola"""
        try:
            thread_name = threading.current_thread().name
            prefix = f"[PAL][DB][{level}][{thread_name}]"
            print(f"{prefix} {message}")
        except Exception:
            try:
                print(message)
            except Exception:
                pass

    def _get_best_odbc_driver(self) -> str:
        """
        Detecta el mejor driver ODBC de SQL Server disponible en esta máquina.
        Prioriza las versiones más recientes para mayor compatibilidad.
        Retorna el nombre del driver listo para incluir en la cadena de conexión.
        """
        try:
            drivers = pyodbc.drivers()
        except Exception:
            drivers = []

        # Orden de preferencia: más nuevo primero
        preferred = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "ODBC Driver 13 for SQL Server",
            "ODBC Driver 11 for SQL Server",
            "SQL Server Native Client 11.0",
            "SQL Server Native Client 10.0",
            "SQL Server",   # driver legacy, incluido en Windows
        ]

        for drv in preferred:
            if drv in drivers:
                self._log(f"Driver ODBC seleccionado: {drv}", "INFO")
                return drv

        # Si no encontramos ninguno de la lista, usar el primero SQL-relacionado disponible
        sql_drivers = [d for d in drivers if 'SQL' in d.upper()]
        if sql_drivers:
            self._log(f"Driver ODBC de fallback: {sql_drivers[0]}", "WARNING")
            return sql_drivers[0]

        # Último recurso: el legacy que siempre ha estado en Windows
        self._log("No se encontró driver ODBC de SQL Server, usando legacy 'SQL Server'", "ERROR")
        return "SQL Server"

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
            self._log(f"Error verificando tabla {table_name}: {str(e)}", "ERROR")
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
        self._log(f"Attempting to connect to server: {server}, database: {database}, user: {user if user else 'Windows Auth'}", "INFO")

        # Guardar parámetros base para reconexiones y hilos secundarios
        self.server = server
        self.database = database
        self.user = user
        self.password = password

        # Detectar el mejor driver disponible en esta máquina
        odbc_driver = self._get_best_odbc_driver()
        self.current_odbc_driver = odbc_driver

        # Cadena inicial sin database para crear la BD si no existe.
        # El driver legacy "SQL Server" (DBNETLIB) no soporta TLS moderno y lanza
        # el error 08001 (SSL handshake) si se activa Encrypt=yes, por lo que se
        # fuerza Encrypt=no para ese driver. Los drivers ODBC 17/18 usan cifrado
        # con certificado auto-firmado aceptado (TrustServerCertificate=yes).
        _legacy_driver = odbc_driver == "SQL Server"
        if _legacy_driver:
            _encrypt_opts = "Encrypt=no;"
        else:
            _encrypt_opts = "Encrypt=yes;TrustServerCertificate=yes;"
        
        self.current_encrypt_opts = _encrypt_opts

        initial_conn_str = (
            f"DRIVER={{{odbc_driver}}};"
            f"SERVER={server};"
            f"{_encrypt_opts}"
            "Connection Timeout=30;"
        )
    
        if user:
            # Autenticación SQL Server (usuario sa u otro)
            initial_conn_str += f"UID={user};PWD={password or ''};"
        else:
            # Autenticación Windows
            initial_conn_str += "Trusted_Connection=yes;"

        # Track retries
        attempt = 0
        last_error = None
        
        while attempt <= retry_attempts:
            if attempt > 0:
                self._log(f"Retry attempt {attempt} of {retry_attempts}...", "WARNING")
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
                self._log(f"Connection attempt {attempt+1} failed: {error_details}", "ERROR")
                attempt += 1
                
                # Only raise exception if we've exhausted all retries
                if attempt > retry_attempts:
                    error_msg = f"{ErrorCode.DB_CONNECTION_FAILED}: {str(e)}"
                    raise Exception(error_msg) from e

        # Cadena de conexión final CON database
        final_conn_str = initial_conn_str + f"DATABASE={database};"

        try:
            # Serializar conexión para evitar condiciones de carrera entre hilos
            with self._connect_lock:
                self.conn = pyodbc.connect(final_conn_str)
                self.cursor = self.conn.cursor()
                self.connected_server = server
                # Ejecutar DDL solo una vez por proceso (evita conflictos en reconexiones/hilos)
                if not self._schema_initialized:
                    try:
                        self.create_table()
                        self._schema_initialized = True
                    except Exception as ddl_e:
                        # No impedir la conexión si el driver no permite múltiples resultados
                        self._log(f"DDL init skipped due to error: {ddl_e}", "WARNING")
                # Do not auto-create security schema; let UI prompt the user
                try:
                    missing = self.check_security_schema()
                    if missing:
                        self._log(f"Security schema missing tables: {', '.join(missing)}", "WARNING")
                    
                    # Auto-create logistics tables if security schema is mostly OK
                    # or at least try to ensure they exist for the new module
                    self.ensure_logistica_tables()
                except Exception as se:
                    self._log(f"Schema check failed: {se}", "ERROR")
                return True
        except pyodbc.Error as e:
            error_msg = f"{ErrorCode.DB_CONNECTION_FAILED}: {str(e)}"
            raise Exception(error_msg) from e

    def create_table(self):
        try:
            # Migración: renombrar tablas antiguas a prefijo pal_
            EXECUTE_MIGRATION = """
            -- Rename clientes -> pal_clientes si aplica
            IF EXISTS (SELECT * FROM sys.tables WHERE name='clientes' AND type='U')
               AND NOT EXISTS (SELECT * FROM sys.tables WHERE name='pal_clientes' AND type='U')
            BEGIN
                EXEC sp_rename 'clientes', 'pal_clientes';
                -- Renombrar índices si existen
                IF EXISTS (SELECT * FROM sys.indexes WHERE name='idx_clientes_numero')
                    EXEC sp_rename 'idx_clientes_numero', 'idx_pal_clientes_numero', 'INDEX';
                IF EXISTS (SELECT * FROM sys.indexes WHERE name='idx_clientes_codigo')
                    EXEC sp_rename 'idx_clientes_codigo', 'idx_pal_clientes_codigo', 'INDEX';
            END;
            -- Rename envios_programados -> pal_envios_programados si aplica
            IF EXISTS (SELECT * FROM sys.tables WHERE name='envios_programados' AND type='U')
               AND NOT EXISTS (SELECT * FROM sys.tables WHERE name='pal_envios_programados' AND type='U')
            BEGIN
                EXEC sp_rename 'envios_programados', 'pal_envios_programados';
                IF EXISTS (SELECT * FROM sys.indexes WHERE name='idx_envios_fecha_estado')
                    EXEC sp_rename 'idx_envios_fecha_estado', 'idx_pal_envios_fecha_estado', 'INDEX';
                IF EXISTS (SELECT * FROM sys.indexes WHERE name='idx_envios_numero')
                    EXEC sp_rename 'idx_envios_numero', 'idx_pal_envios_numero', 'INDEX';
                IF EXISTS (SELECT * FROM sys.indexes WHERE name='idx_envios_producto')
                    EXEC sp_rename 'idx_envios_producto', 'idx_pal_envios_producto', 'INDEX';
            END;
            -- Rename TEMP_ENVIO -> pal_temp_envio si aplica
            IF EXISTS (SELECT * FROM sys.tables WHERE name='TEMP_ENVIO' AND type='U')
               AND NOT EXISTS (SELECT * FROM sys.tables WHERE name='pal_temp_envio' AND type='U')
            BEGIN
                EXEC sp_rename 'TEMP_ENVIO', 'pal_temp_envio';
            END;
            """
            try:
                self.cursor.execute(EXECUTE_MIGRATION)
                self.conn.commit()
            except Exception:
                pass

            # Crear tabla pal_clientes con índices
            self.cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='pal_clientes' AND xtype='U')
                CREATE TABLE pal_clientes (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    numero_cliente NVARCHAR(50) NOT NULL,
                    C_CODIGO NVARCHAR(15) NOT NULL
                );

                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_pal_clientes_numero')
                CREATE INDEX idx_pal_clientes_numero ON pal_clientes (numero_cliente);
                
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_pal_clientes_codigo')
                CREATE INDEX idx_pal_clientes_codigo ON pal_clientes (C_CODIGO);
            """)
            self.conn.commit()

            # Crear tabla pal_envios_programados con índices
            self.cursor.execute("""
            IF NOT EXISTS (
                SELECT * FROM sys.tables 
                WHERE name = 'pal_envios_programados' AND type = 'U'
            )
            CREATE TABLE pal_envios_programados (
                id INT IDENTITY(1,1) PRIMARY KEY,
                numero_cliente NVARCHAR(50) NOT NULL,
                fecha_programada DATETIME NOT NULL,
                fecha_creacion DATETIME DEFAULT GETDATE(),
                estado NVARCHAR(20) DEFAULT 'PENDIENTE',
                tipo_envio NVARCHAR(20) NOT NULL 
                    CHECK (tipo_envio IN ('ENTREGA', 'DISPONIBILIDAD')),
                codigo_producto NVARCHAR(15) NULL
            );
            
            -- Agregar columna codigo_producto si la tabla existe pero no tiene la columna
            IF EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_envios_programados' AND type = 'U')
            AND NOT EXISTS (
                SELECT * FROM sys.columns 
                WHERE object_id = OBJECT_ID('pal_envios_programados') 
                AND name = 'codigo_producto'
            )
            BEGIN
                ALTER TABLE pal_envios_programados ADD codigo_producto NVARCHAR(15) NULL;
            END

            IF NOT EXISTS (
                SELECT * FROM sys.indexes 
                WHERE name = 'idx_pal_envios_fecha_estado'
            )
            CREATE INDEX idx_pal_envios_fecha_estado 
            ON pal_envios_programados (fecha_programada, estado);

            IF NOT EXISTS (
                SELECT * FROM sys.indexes 
                WHERE name = 'idx_pal_envios_numero'
            )
            CREATE INDEX idx_pal_envios_numero 
            ON pal_envios_programados (numero_cliente);

            IF NOT EXISTS (
                SELECT * FROM sys.indexes 
                WHERE name = 'idx_pal_envios_producto'
            )
            AND EXISTS (
                SELECT * FROM sys.columns 
                WHERE object_id = OBJECT_ID('pal_envios_programados') 
                AND name = 'codigo_producto'
            )
            CREATE INDEX idx_pal_envios_producto 
            ON pal_envios_programados (codigo_producto);
        """)
            self.conn.commit()

        except pyodbc.Error as e:
            error_msg = f"{ErrorCode.DB_TABLE_CREATION}: {str(e)}"
            raise Exception(error_msg) from e
        
    def check_security_schema(self):
        """Returns a list of missing pal_* security tables required by the app."""
        required = [
            'pal_usuarios','pal_roles','pal_permisos','pal_usuarios_roles',
            'pal_roles_permisos','pal_usuarios_permisos','pal_usuarios_modulos',
            'pal_auditoria_accesos','pal_sesiones'
        ]
        try:
            rows = self.fetch_data(
                "SELECT name FROM sys.tables WHERE name IN (?,?,?,?,?,?,?,?,?)",
                required
            )
            present = {r[0] for r in (rows or [])}
            return [t for t in required if t not in present]
        except Exception:
            # In case of error, be conservative and assume all are missing
            return required

    def ensure_security_tables(self):
        """Create PAL auth/permissions tables (pal_*) and seed defaults if missing."""
        try:
            sql = """
            -- Tables
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_usuarios' AND type = 'U')
            BEGIN
                CREATE TABLE pal_usuarios (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    username NVARCHAR(50) NOT NULL UNIQUE,
                    password_hash NVARCHAR(255) NOT NULL,
                    nombre_completo NVARCHAR(100) NOT NULL,
                    email NVARCHAR(100) NULL,
                    activo BIT NOT NULL DEFAULT 1,
                    fecha_creacion DATETIME2 DEFAULT SYSUTCDATETIME(),
                    fecha_ultimo_acceso DATETIME2 NULL,
                    intentos_fallidos INT DEFAULT 0,
                    bloqueado_hasta DATETIME2 NULL
                );
            END;

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_roles' AND type = 'U')
            BEGIN
                CREATE TABLE pal_roles (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    nombre NVARCHAR(50) NOT NULL UNIQUE,
                    descripcion NVARCHAR(MAX) NULL,
                    es_sistema BIT NOT NULL DEFAULT 0
                );
            END;

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_permisos' AND type = 'U')
            BEGIN
                CREATE TABLE pal_permisos (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    codigo NVARCHAR(50) NOT NULL UNIQUE,
                    modulo NVARCHAR(50) NOT NULL,
                    descripcion NVARCHAR(MAX) NULL,
                    CONSTRAINT chk_perm_modulo CHECK (modulo IN (N'TRA', N'MBRP', N'STOCK', N'MENSAJES', N'ESTADISTICAS', N'CALENDARIO', N'ADMIN', N'LOGISTICA'))
                );
            END;

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_usuarios_roles' AND type = 'U')
            BEGIN
                CREATE TABLE pal_usuarios_roles (
                    usuario_id INT NOT NULL,
                    rol_id INT NOT NULL,
                    fecha_asignacion DATETIME2 DEFAULT SYSUTCDATETIME(),
                    asignado_por INT NULL,
                    CONSTRAINT pk_pal_usuarios_roles PRIMARY KEY (usuario_id, rol_id),
                    CONSTRAINT fk_pal_ur_usuario FOREIGN KEY (usuario_id) REFERENCES pal_usuarios(id) ON DELETE CASCADE,
                    CONSTRAINT fk_pal_ur_rol FOREIGN KEY (rol_id) REFERENCES pal_roles(id) ON DELETE CASCADE,
                    CONSTRAINT fk_pal_ur_asignado_por FOREIGN KEY (asignado_por) REFERENCES pal_usuarios(id)
                );
            END;

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_roles_permisos' AND type = 'U')
            BEGIN
                CREATE TABLE pal_roles_permisos (
                    rol_id INT NOT NULL,
                    permiso_id INT NOT NULL,
                    CONSTRAINT pk_pal_roles_permisos PRIMARY KEY (rol_id, permiso_id),
                    CONSTRAINT fk_pal_rp_rol FOREIGN KEY (rol_id) REFERENCES pal_roles(id) ON DELETE CASCADE,
                    CONSTRAINT fk_pal_rp_permiso FOREIGN KEY (permiso_id) REFERENCES pal_permisos(id) ON DELETE CASCADE
                );
            END;

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_usuarios_permisos' AND type = 'U')
            BEGIN
                CREATE TABLE pal_usuarios_permisos (
                    usuario_id INT NOT NULL,
                    permiso_id INT NOT NULL,
                    concedido BIT NOT NULL DEFAULT 1,
                    fecha_asignacion DATETIME2 DEFAULT SYSUTCDATETIME(),
                    asignado_por INT NULL,
                    CONSTRAINT pk_pal_usuarios_permisos PRIMARY KEY (usuario_id, permiso_id),
                    CONSTRAINT fk_pal_up_usuario FOREIGN KEY (usuario_id) REFERENCES pal_usuarios(id) ON DELETE CASCADE,
                    CONSTRAINT fk_pal_up_permiso FOREIGN KEY (permiso_id) REFERENCES pal_permisos(id) ON DELETE CASCADE,
                    CONSTRAINT fk_pal_up_asignado_por FOREIGN KEY (asignado_por) REFERENCES pal_usuarios(id)
                );
            END;

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_usuarios_modulos' AND type = 'U')
            BEGIN
                CREATE TABLE pal_usuarios_modulos (
                    usuario_id INT NOT NULL,
                    modulo NVARCHAR(50) NOT NULL,
                    habilitado BIT NOT NULL DEFAULT 1,
                    fecha_asignacion DATETIME2 DEFAULT SYSUTCDATETIME(),
                    asignado_por INT NULL,
                    CONSTRAINT pk_pal_usuarios_modulos PRIMARY KEY (usuario_id, modulo),
                    CONSTRAINT fk_pal_um_usuario FOREIGN KEY (usuario_id) REFERENCES pal_usuarios(id) ON DELETE CASCADE,
                    CONSTRAINT fk_pal_um_asignado_por FOREIGN KEY (asignado_por) REFERENCES pal_usuarios(id),
                    CONSTRAINT chk_pal_um_modulo CHECK (modulo IN (N'TRA', N'MBRP', N'STOCK', N'MENSAJES', N'ESTADISTICAS', N'CALENDARIO', N'ADMIN', N'LOGISTICA'))
                );
            END;

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_auditoria_accesos' AND type = 'U')
            BEGIN
                CREATE TABLE pal_auditoria_accesos (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    usuario_id INT NULL,
                    accion NVARCHAR(100) NOT NULL,
                    modulo NVARCHAR(50) NULL,
                    detalle NVARCHAR(MAX) NULL,
                    ip_address NVARCHAR(45) NULL,
                    exitoso BIT NOT NULL,
                    fecha DATETIME2 DEFAULT SYSUTCDATETIME(),
                    CONSTRAINT fk_pal_aud_usuario FOREIGN KEY (usuario_id) REFERENCES pal_usuarios(id)
                );
            END;

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_sesiones' AND type = 'U')
            BEGIN
                CREATE TABLE pal_sesiones (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    usuario_id INT NOT NULL,
                    token NVARCHAR(255) NOT NULL UNIQUE,
                    ip_address NVARCHAR(45) NULL,
                    fecha_inicio DATETIME2 DEFAULT SYSUTCDATETIME(),
                    fecha_expiracion DATETIME2 NOT NULL,
                    activa BIT NOT NULL DEFAULT 1,
                    CONSTRAINT fk_pal_ses_usuario FOREIGN KEY (usuario_id) REFERENCES pal_usuarios(id) ON DELETE CASCADE
                );
            END;

            -- Indexes
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_usuarios_username')
                CREATE INDEX idx_pal_usuarios_username ON pal_usuarios(username);
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_usuarios_activo')
                CREATE INDEX idx_pal_usuarios_activo ON pal_usuarios(activo);
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_sesiones_token')
                CREATE INDEX idx_pal_sesiones_token ON pal_sesiones(token);
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_sesiones_activa')
                CREATE INDEX idx_pal_sesiones_activa ON pal_sesiones(activa);
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_auditoria_usuario')
                CREATE INDEX idx_pal_auditoria_usuario ON pal_auditoria_accesos(usuario_id);
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_auditoria_fecha')
                CREATE INDEX idx_pal_auditoria_fecha ON pal_auditoria_accesos(fecha);
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_usuarios_modulos_usuario')
                CREATE INDEX idx_pal_usuarios_modulos_usuario ON pal_usuarios_modulos(usuario_id);
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_usuarios_modulos_modulo')
                CREATE INDEX idx_pal_usuarios_modulos_modulo ON pal_usuarios_modulos(modulo);

            -- Seed roles
            IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Administrador')
                INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Administrador', N'Acceso total al sistema', 1);
            IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Supervisor')
                INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Supervisor', N'Operación y consulta avanzada', 1);
            IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Analista')
                INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Analista', N'Consulta y exportación', 1);
            IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Operador Stock')
                INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Operador Stock', N'Gestión de stock', 1);
            IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Mensajería')
                INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Mensajería', N'Envío y gestión de mensajes', 1);
            IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Consulta')
                INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Consulta', N'Solo lectura', 1);
            IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Gerente Logistica')
                INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Gerente Logistica', N'Autorización y gestión total de logística', 1);
            IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Subgerente Logistica')
                INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Subgerente Logistica', N'Autorización y gestión de logística', 1);

            -- Seed permissions
            DECLARE @perm TABLE(codigo NVARCHAR(50), modulo NVARCHAR(50), descripcion NVARCHAR(MAX));
            INSERT INTO @perm (codigo, modulo, descripcion)
            VALUES
             (N'tra.ver', N'TRA', N'Ver datos de rotación')
            ,(N'tra.exportar', N'TRA', N'Exportar reportes')
            ,(N'tra.configurar', N'TRA', N'Configurar parámetros')
            ,(N'tra.ver_costo_utilidad', N'TRA', N'Ver costo y utilidad en reportes')
            ,(N'mbrp.ver', N'MBRP', N'Ver datos MBRP')
            ,(N'mbrp.exportar', N'MBRP', N'Exportar reportes')
            ,(N'mbrp.configurar', N'MBRP', N'Configurar umbrales')
            ,(N'mbrp.ver_costo_utilidad', N'MBRP', N'Ver costo y utilidad en reportes')
            ,(N'stock.ver', N'STOCK', N'Ver alertas de stock')
            ,(N'stock.editar', N'STOCK', N'Marcar favoritos / edición')
            ,(N'stock.exportar', N'STOCK', N'Exportar reportes')
            ,(N'stock.configurar', N'STOCK', N'Configurar alertas')
            ,(N'stock.ver_costo_utilidad', N'STOCK', N'Ver costo y utilidad en reportes')
            ,(N'mensajes.ver', N'MENSAJES', N'Ver mensajes programados')
            ,(N'mensajes.crear', N'MENSAJES', N'Crear mensajes')
            ,(N'mensajes.enviar', N'MENSAJES', N'Enviar mensajes')
            ,(N'mensajes.eliminar', N'MENSAJES', N'Eliminar mensajes')
            ,(N'mensajes.configurar', N'MENSAJES', N'Configurar plantillas')
            ,(N'estadisticas.ver', N'ESTADISTICAS', N'Ver gráficos y reportes')
            ,(N'estadisticas.exportar', N'ESTADISTICAS', N'Exportar reportes')
            ,(N'calendario.ver', N'CALENDARIO', N'Ver eventos')
            ,(N'calendario.crear', N'CALENDARIO', N'Crear eventos')
            ,(N'calendario.editar', N'CALENDARIO', N'Editar eventos')
            ,(N'calendario.eliminar', N'CALENDARIO', N'Eliminar eventos')
            ,(N'admin.usuarios', N'ADMIN', N'Gestionar usuarios')
            ,(N'admin.roles', N'ADMIN', N'Gestionar roles')
            ,(N'admin.permisos', N'ADMIN', N'Gestionar permisos')
            ,(N'admin.sistema', N'ADMIN', N'Configuración general')
            ,(N'admin.auditoria', N'ADMIN', N'Ver logs de auditoría')
            ,(N'logistica.ver', N'LOGISTICA', N'Acceso al módulo de logística')
            ,(N'abastecimiento.ver', N'LOGISTICA', N'Ver módulo de abastecimiento')
            ,(N'abastecimiento.generar', N'LOGISTICA', N'Generar sugerencias de transferencia')
            ,(N'abastecimiento.autorizar', N'LOGISTICA', N'Autorizar transferencias entre sedes')
            ,(N'abastecimiento.exportar', N'LOGISTICA', N'Exportar reportes a Excel')
            ,(N'abastecimiento.configurar', N'LOGISTICA', N'Configurar parámetros de abastecimiento');

            INSERT INTO pal_permisos (codigo, modulo, descripcion)
            SELECT p.codigo, p.modulo, p.descripcion
            FROM @perm p
            LEFT JOIN pal_permisos pe ON pe.codigo = p.codigo
            WHERE pe.id IS NULL;

            -- Assign permissions to roles
            DECLARE @rol_admin INT = (SELECT id FROM pal_roles WHERE nombre = N'Administrador');
            DECLARE @rol_super INT = (SELECT id FROM pal_roles WHERE nombre = N'Supervisor');
            DECLARE @rol_analista INT = (SELECT id FROM pal_roles WHERE nombre = N'Analista');
            DECLARE @rol_stock INT = (SELECT id FROM pal_roles WHERE nombre = N'Operador Stock');
            DECLARE @rol_msg INT = (SELECT id FROM pal_roles WHERE nombre = N'Mensajería');
            DECLARE @rol_consulta INT = (SELECT id FROM pal_roles WHERE nombre = N'Consulta');
            DECLARE @rol_ger_log INT = (SELECT id FROM pal_roles WHERE nombre = N'Gerente Logistica');
            DECLARE @rol_sub_log INT = (SELECT id FROM pal_roles WHERE nombre = N'Subgerente Logistica');

            DECLARE @rp TABLE(rol_id INT, perm_code NVARCHAR(50));
            INSERT INTO @rp(rol_id, perm_code)
            SELECT @rol_admin, codigo FROM pal_permisos;
            
            -- Asignar ver_costo_utilidad solo a Administrador y Supervisor por defecto

            INSERT INTO @rp(rol_id, perm_code)
            SELECT @rol_super, codigo FROM pal_permisos WHERE codigo IN (
                N'tra.ver', N'tra.exportar', N'tra.ver_costo_utilidad',
                N'mbrp.ver', N'mbrp.exportar', N'mbrp.ver_costo_utilidad',
                N'stock.ver', N'stock.editar', N'stock.exportar', N'stock.ver_costo_utilidad',
                N'mensajes.ver', N'mensajes.crear', N'mensajes.enviar',
                N'estadisticas.ver'
            );

            INSERT INTO @rp(rol_id, perm_code)
            SELECT @rol_analista, codigo FROM pal_permisos WHERE codigo IN (
                N'tra.ver', N'tra.exportar',
                N'mbrp.ver', N'mbrp.exportar',
                N'stock.ver',
                N'estadisticas.ver'
            );

            INSERT INTO @rp(rol_id, perm_code)
            SELECT @rol_stock, codigo FROM pal_permisos WHERE codigo IN (
                N'stock.ver', N'stock.editar'
            );

            INSERT INTO @rp(rol_id, perm_code)
            SELECT @rol_msg, codigo FROM pal_permisos WHERE codigo IN (
                N'mensajes.ver', N'mensajes.crear', N'mensajes.enviar'
            );

            INSERT INTO @rp(rol_id, perm_code)
            SELECT @rol_consulta, codigo FROM pal_permisos WHERE codigo IN (
                N'tra.ver', N'mbrp.ver', N'stock.ver', N'estadisticas.ver', N'calendario.ver', N'mensajes.ver'
            );

            INSERT INTO @rp(rol_id, perm_code)
            SELECT @rol_ger_log, codigo FROM pal_permisos WHERE modulo = N'LOGISTICA';

            INSERT INTO @rp(rol_id, perm_code)
            SELECT @rol_sub_log, codigo FROM pal_permisos WHERE modulo = N'LOGISTICA';

            INSERT INTO pal_roles_permisos (rol_id, permiso_id)
            SELECT r.rol_id, p.id
            FROM @rp r
            JOIN pal_permisos p ON p.codigo = r.perm_code
            LEFT JOIN pal_roles_permisos rp ON rp.rol_id = r.rol_id AND rp.permiso_id = p.id
            WHERE rp.rol_id IS NULL;

            -- Ensure initial admin user and modules
            IF NOT EXISTS (SELECT 1 FROM pal_usuarios WHERE username = N'admin')
            BEGIN
                -- Bcrypt hash para contraseña: 123
                -- Generado con: bcrypt.hashpw(b'123', bcrypt.gensalt(rounds=12))
                DECLARE @admin_pwd NVARCHAR(255) = N'$2b$12$1dErMkRR9YPWV9vUeSAfbO5t.jQHOF4cLCzyDi1x5plUjtuEH/r/O';
                INSERT INTO pal_usuarios (username, password_hash, nombre_completo, email, activo)
                VALUES (N'admin', @admin_pwd, N'Administrador del Sistema', NULL, 1);
            END;

            DECLARE @admin_user_id INT = (SELECT id FROM pal_usuarios WHERE username = N'admin');
            IF @admin_user_id IS NOT NULL AND @rol_admin IS NOT NULL
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pal_usuarios_roles WHERE usuario_id = @admin_user_id AND rol_id = @rol_admin
                )
                INSERT INTO pal_usuarios_roles (usuario_id, rol_id, asignado_por)
                VALUES (@admin_user_id, @rol_admin, @admin_user_id);
            END;

            DECLARE @mods TABLE(modulo NVARCHAR(50));
            INSERT INTO @mods(modulo)
            VALUES (N'TRA'),(N'MBRP'),(N'STOCK'),(N'MENSAJES'),(N'ESTADISTICAS'),(N'CALENDARIO'),(N'ADMIN'),(N'LOGISTICA');

            INSERT INTO pal_usuarios_modulos (usuario_id, modulo, habilitado, asignado_por)
            SELECT @admin_user_id, m.modulo, 1, @admin_user_id
            FROM @mods m
            LEFT JOIN pal_usuarios_modulos um ON um.usuario_id = @admin_user_id AND um.modulo = m.modulo
            WHERE um.usuario_id IS NULL;
            """
            if not self.conn:
                return
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
        except Exception as e:
            raise

    def ensure_logistica_tables(self):
        """Crea las tablas pal_ para el módulo de Logística / Abastecimiento si no existen."""
        try:
            sql = """
            -- Settings globales (Sedes dinámicas, etc)
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_global_settings' AND type = 'U')
            BEGIN
                CREATE TABLE pal_global_settings (
                    setting_key NVARCHAR(50) PRIMARY KEY,
                    setting_value NVARCHAR(MAX),
                    description NVARCHAR(255),
                    last_modified DATETIME DEFAULT GETDATE()
                );
            END;

            -- Parámetros de abastecimiento (días de stock por categoría)
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_parametros_abastecimiento' AND type = 'U')
            BEGIN
                CREATE TABLE pal_parametros_abastecimiento (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    categoria_id NVARCHAR(50) NULL, -- Código de grupo en Profit (NULL = Global)
                    dias_stock INT DEFAULT 7,
                    umbral_quiebre DECIMAL(10,2) DEFAULT 50, -- Cantidad mínima física para considerar quiebre
                    umbral_autorizacion DECIMAL(10,2) DEFAULT 10,
                    dias_analisis_ventas INT DEFAULT 365, -- Rango de días de rotación a usar (30, 90, 365)
                    fecha_actualizacion DATETIME DEFAULT GETDATE()
                );
            END;
            ELSE
            BEGIN
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_parametros_abastecimiento]') AND name = 'umbral_autorizacion')
                BEGIN
                    ALTER TABLE [dbo].[pal_parametros_abastecimiento] ADD [umbral_autorizacion] DECIMAL(10,2) DEFAULT 10;
                END
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_parametros_abastecimiento]') AND name = 'umbral_quiebre')
                BEGIN
                    ALTER TABLE [dbo].[pal_parametros_abastecimiento] ADD [umbral_quiebre] DECIMAL(10,2) DEFAULT 50;
                END
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_parametros_abastecimiento]') AND name = 'dias_analisis_ventas')
                BEGIN
                    ALTER TABLE [dbo].[pal_parametros_abastecimiento] ADD [dias_analisis_ventas] INT DEFAULT 365;
                END
            END

            -- Auditoría de autorizaciones
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_auditoria_autorizaciones' AND type = 'U')
            BEGIN
                CREATE TABLE pal_auditoria_autorizaciones (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    usuario_id INT,
                    producto_codigo NVARCHAR(15),
                    sucursal_origen NVARCHAR(50),
                    sucursal_destino NVARCHAR(50),
                    cantidad_original DECIMAL(10,2),
                    cantidad_autorizada DECIMAL(10,2),
                    motivo TEXT,
                    fecha_autorizacion DATETIME DEFAULT GETDATE()
                );
            END;

            -- Sugerencias de transferencia
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_sugerencias_transferencia' AND type = 'U')
            BEGIN
                CREATE TABLE pal_sugerencias_transferencia (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    producto_codigo NVARCHAR(15),
                    sucursal_destino NVARCHAR(50),
                    sucursal_origen_sugerida NVARCHAR(50),
                    cantidad_sugerida DECIMAL(10,2),
                    cantidad_disponible DECIMAL(10,2),
                    stock_actual DECIMAL(10,2),
                    dias_stock_actual INT,
                    dias_stock_necesario INT,
                    tiene_odc_activa BIT DEFAULT 0,
                    es_producto_rojo BIT DEFAULT 0,
                    tipo_solicitud NVARCHAR(20) DEFAULT 'normal', -- normal, odc, producto_rojo
                    requiere_autorizacion BIT DEFAULT 0,
                    fue_autorizada BIT DEFAULT 0,
                    usuario_autoriza INT,
                    cantidad_pre_ajuste DECIMAL(10,2) NULL,
                    fecha_autorizacion DATETIME,
                    fecha_generacion DATETIME DEFAULT GETDATE(),
                    estado NVARCHAR(20) DEFAULT 'pendiente' -- pendiente, aprobada, rechazada, exportada
                );
            END;
            ELSE
            BEGIN
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_sugerencias_transferencia]') AND name = 'stock_actual')
                BEGIN
                    ALTER TABLE [dbo].[pal_sugerencias_transferencia] ADD [stock_actual] DECIMAL(10,2) NULL;
                END
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_sugerencias_transferencia]') AND name = 'cantidad_pre_ajuste')
                BEGIN
                    ALTER TABLE [dbo].[pal_sugerencias_transferencia] ADD [cantidad_pre_ajuste] DECIMAL(10,2) NULL;
                END
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_sugerencias_transferencia]') AND name = 'maestro_id')
                BEGIN
                    ALTER TABLE [dbo].[pal_sugerencias_transferencia] ADD [maestro_id] INT NULL;
                END
            END

            -- Maestro de Transferencias (Agrupación por Órden)
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_transferencias_maestro' AND type = 'U')
            BEGIN
                CREATE TABLE pal_transferencias_maestro (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    numero_transf NVARCHAR(20) UNIQUE NOT NULL,
                    sucursal_destino NVARCHAR(50) NOT NULL,
                    fecha_creacion DATETIME DEFAULT GETDATE(),
                    usuario_crea INT,
                    estado NVARCHAR(20) DEFAULT 'en_transito' -- en_transito, recibida, anulada
                );
            END;

            -- Productos no trasladables (Lista ROJA) - Por sede destino
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_productos_no_trasladables' AND type = 'U')
            BEGIN
                CREATE TABLE pal_productos_no_trasladables (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    producto_codigo NVARCHAR(15) NOT NULL,
                    sede_destino NVARCHAR(50) NULL, -- NULL = todas las sedes destino
                    motivo NVARCHAR(255) NULL,
                    fecha_registro DATETIME DEFAULT GETDATE(),
                    usuario_id INT NULL,
                    activo BIT DEFAULT 1
                );
            END;
            ELSE
            BEGIN
                -- Agregar columnas faltantes si la tabla ya existía
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_productos_no_trasladables]') AND name = 'fecha_registro')
                BEGIN
                    ALTER TABLE [dbo].[pal_productos_no_trasladables] ADD [fecha_registro] [datetime] NULL DEFAULT (getdate())
                END
                
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_productos_no_trasladables]') AND name = 'usuario_id')
                BEGIN
                    ALTER TABLE [dbo].[pal_productos_no_trasladables] ADD [usuario_id] [int] NULL
                END

                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_productos_no_trasladables]') AND name = 'activo')
                BEGIN
                    ALTER TABLE [dbo].[pal_productos_no_trasladables] ADD [activo] [bit] NULL DEFAULT ((1))
                END
            END

            -- Compromisos Centralizados de Inventario
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_compromisos_inventario' AND type = 'U')
            BEGIN
                CREATE TABLE pal_compromisos_inventario (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    producto_codigo NVARCHAR(15) NOT NULL,
                    sucursal_origen NVARCHAR(50) NOT NULL,
                    sucursal_destino NVARCHAR(50) NOT NULL,
                    cantidad DECIMAL(10,2) NOT NULL,
                    estado NVARCHAR(20) DEFAULT 'activo', -- activo, completado, anulado
                    referencia_maestro INT NULL,
                    usuario_id INT NULL,
                    fecha_creacion DATETIME DEFAULT GETDATE(),
                    fecha_actualizacion DATETIME DEFAULT GETDATE()
                );
            END;
            ELSE
            BEGIN
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_compromisos_producto')
                    CREATE INDEX idx_pal_compromisos_producto ON pal_compromisos_inventario(producto_codigo, estado);
            END

            -- Índices
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_sugerencias_estado')
                CREATE INDEX idx_pal_sugerencias_estado ON pal_sugerencias_transferencia(estado, fecha_generacion);

            -- Asegurar permisos base para Logística
            IF NOT EXISTS (SELECT * FROM pal_permisos WHERE codigo = 'abastecimiento.ver')
                INSERT INTO pal_permisos (codigo, modulo, descripcion) VALUES ('abastecimiento.ver', 'LOGISTICA', 'Ver módulo de abastecimiento');
            IF NOT EXISTS (SELECT * FROM pal_permisos WHERE codigo = 'abastecimiento.generar')
                INSERT INTO pal_permisos (codigo, modulo, descripcion) VALUES ('abastecimiento.generar', 'LOGISTICA', 'Generar sugerencias de transferencia');
            IF NOT EXISTS (SELECT * FROM pal_permisos WHERE codigo = 'abastecimiento.autorizar')
                INSERT INTO pal_permisos (codigo, modulo, descripcion) VALUES ('abastecimiento.autorizar', 'LOGISTICA', 'Autorizar transferencias');

            -- Asegurar roles para Logística
            IF NOT EXISTS (SELECT * FROM pal_roles WHERE nombre = 'Gerente Logistica')
                INSERT INTO pal_roles (nombre, descripcion) VALUES ('Gerente Logistica', 'Gestión completa de abastecimiento y transferencias');
            IF NOT EXISTS (SELECT * FROM pal_roles WHERE nombre = 'Subgerente Logistica')
                INSERT INTO pal_roles (nombre, descripcion) VALUES ('Subgerente Logistica', 'Generación de sugerencias y visualización');

            -- Recepciones Parciales
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_recepciones_maestro' AND type = 'U')
            BEGIN
                CREATE TABLE pal_recepciones_maestro (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    numero_recepcion NVARCHAR(20) UNIQUE NOT NULL,
                    transferencia_id INT NOT NULL,
                    fecha_recepcion DATETIME DEFAULT GETDATE(),
                    usuario_recibe INT,
                    observaciones TEXT NULL,
                    estado NVARCHAR(20) DEFAULT 'completada'
                );
            END;

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_recepciones_detalle' AND type = 'U')
            BEGIN
                CREATE TABLE pal_recepciones_detalle (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    recepcion_id INT NOT NULL,
                    sugerencia_id INT NOT NULL,
                    cantidad_recibida DECIMAL(18,2) NOT NULL
                );
            END;

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_recepciones_lotes' AND type = 'U')
            BEGIN
                CREATE TABLE pal_recepciones_lotes (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    recepcion_detalle_id INT NOT NULL,
                    lote_interno NVARCHAR(50) NOT NULL,
                    lote_fabrica NVARCHAR(50) NULL,
                    fecha_vencimiento DATE NULL,
                    cantidad DECIMAL(18,2) NOT NULL,
                    fecha_registro DATETIME DEFAULT GETDATE()
                );
            END;

            -- Agregar columnas a pal_sugerencias_transferencia si no existen
            IF EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_sugerencias_transferencia' AND type = 'U')
            BEGIN
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_sugerencias_transferencia]') AND name = 'cantidad_recibida_total')
                BEGIN
                    ALTER TABLE [dbo].[pal_sugerencias_transferencia] ADD [cantidad_recibida_total] DECIMAL(18,2) DEFAULT 0;
                END
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_sugerencias_transferencia]') AND name = 'estado_recepcion')
                BEGIN
                    ALTER TABLE [dbo].[pal_sugerencias_transferencia] ADD [estado_recepcion] NVARCHAR(20) DEFAULT 'pendiente';
                END
            END
            """
            if not self.conn:
                return
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
        except Exception as e:
            self._log(f"Error creando tablas de logística: {e}", "ERROR")

    def obtener_alertas_stock(self, limit=None):
        max_retries = 3
        
        for attempt in range(max_retries):
            cursor = None
            thread_conn = None
            try:
                # Obtener conexión thread-safe
                thread_conn = self.get_thread_connection("alertas_stock")
                if not thread_conn:
                    if getattr(self, 'debug_enabled', False):
                        self._log(f"[DB DEBUG] No se pudo obtener conexión para alertas (intento {attempt + 1})", "DEBUG")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return []
                
                # Mantener la consulta exacta de recup.py - solo depósito 0301
                query = """
                    SELECT 
                        c_codarticulo AS codigo,
                        COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') AS descripcion,
                        'Dep. 0301' AS sede,
                        CAST(SUM(n_cantidad) AS INT) AS stock,  
                    CASE
                        WHEN SUM(n_cantidad) BETWEEN 15 AND 20 THEN 'Leve'  
                        WHEN SUM(n_cantidad) BETWEEN 8 AND 14 THEN 'Media'
                        ELSE 'Crítica'
                    END AS nivel,
                    '' AS dummy1,
                    '' AS dummy2,
                    COALESCE(p.C_DESCRI, 'SIN DESCRIPCIÓN') AS descripcion_larga
                    FROM MA_DEPOPROD d
                        INNER JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.C_CODIGO
                        WHERE c_coddeposito = '0301'
                        GROUP BY c_codarticulo, p.cu_descripcion_corta, p.C_DESCRI
                    HAVING SUM(n_cantidad) <= 20  
                    ORDER BY CAST(SUM(n_cantidad) AS INT) ASC
                    """
            
                if limit:
                    query += f" OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
            
                # Crear cursor para esta operación
                cursor = thread_conn.cursor()
                cursor.execute(query)  # Sin parámetros - hardcodeado como recup.py
                result = cursor.fetchall()
                
                if getattr(self, 'debug_enabled', False):
                    self._log(f"[DB DEBUG] Query executed successfully: {len(result)} rows returned", "DEBUG")
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                if getattr(self, 'debug_enabled', False):
                    self._log(f"[DB DEBUG] Error en obtener_alertas_stock (intento {attempt + 1}): {error_msg}", "DEBUG")
                
                # Manejar errores ODBC específicos
                if any(code in error_msg for code in ["HY010", "HY000", "07005", "08S01", "08003"]):
                    # Error de conexión - limpiar pool para este hilo
                    thread_key = f"alertas_stock_{threading.current_thread().name}"
                    with self._pool_lock:
                        if thread_key in self._connection_pool:
                            try:
                                self._connection_pool[thread_key].close()
                            except:
                                pass
                            del self._connection_pool[thread_key]
                    
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                
                # Si es el último intento, devolver lista vacía
                if attempt == max_retries - 1:
                    return []
                    
            finally:
                # Siempre cerrar el cursor
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
        
        return []
    
    def get_thread_connection(self, thread_name="default"):
        """Obtiene una conexión independiente para un hilo específico con thread-safety"""
        import threading
        
        current_thread = threading.current_thread().name
        thread_key = f"{thread_name}_{current_thread}"
        
        # Thread-safe access to connection pool
        with self._pool_lock:
            # Si ya existe una conexión para este hilo, verificar que esté activa
            if thread_key in self._connection_pool:
                try:
                    conn = self._connection_pool[thread_key]
                    # Verificar si la conexión está activa
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    return conn
                except:
                    # Conexión inválida, remover del pool
                    try:
                        self._connection_pool[thread_key].close()
                    except:
                        pass
                    del self._connection_pool[thread_key]
            
            # Crear nueva conexión para este hilo
            try:
                import pyodbc
                
                conn_str = (
                    f"DRIVER={{{self.current_odbc_driver}}};" 
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    f"{self.current_encrypt_opts}" # current_encrypt_opts already includes trailing semicolon
                    "Connection Timeout=30;"
                    "MARS_Connection=yes;"
                )
                
                if self.user:
                    conn_str += f"UID={self.user};PWD={self.password or ''};"
                else:
                    conn_str += "Trusted_Connection=yes;"
                
                new_conn = pyodbc.connect(conn_str)
                self._connection_pool[thread_key] = new_conn
                if getattr(self, 'debug_enabled', False):
                    self._log(f"[DB DEBUG] Nueva conexión creada para hilo: {thread_key}", "DEBUG")
                return new_conn

            except Exception as e:
                if getattr(self, 'debug_enabled', False):
                    self._log(f"[DB DEBUG] Error creando conexión para hilo {thread_key}: {e}", "DEBUG")
                return None
    
    def close_thread_connections(self):
        """Cierra todas las conexiones del pool de hilos de forma thread-safe"""
        with self._pool_lock:
            for thread_key, conn in list(self._connection_pool.items()):
                try:
                    conn.close()
                    if getattr(self, 'debug_enabled', False):
                        self._log(f"[DB DEBUG] Conexión cerrada: {thread_key}", "DEBUG")
                except:
                    pass
            self._connection_pool.clear()
        

    def execute_query(self, query, params=None):
        """Ejecuta DML/DDL usando conexión por-hilo; maneja reconexión y rollback seguro"""
        max_retries = 3
        for attempt in range(max_retries):
            cursor = None
            thread_conn = None
            try:
                # Usar conexión dedicada del hilo actual
                thread_conn = self.get_thread_connection("exec")
                if not thread_conn:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    raise Exception("Unable to establish database connection")

                cursor = thread_conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                thread_conn.commit()
                return True
            except pyodbc.Error as e:
                # Intentar rollback seguro
                try:
                    if thread_conn:
                        thread_conn.rollback()
                except Exception:
                    pass
                # Errores de conexión: limpiar conexión del pool y reintentar
                err_s = str(e)
                if any(code in err_s for code in ["HY000", "HY010", "08S01", "08003", "07005"]):
                    try:
                        thread_key = f"exec_{threading.current_thread().name}"
                        with self._pool_lock:
                            if thread_key in self._connection_pool:
                                try:
                                    self._connection_pool[thread_key].close()
                                except Exception:
                                    pass
                                del self._connection_pool[thread_key]
                    except Exception:
                        pass
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                error_msg = f"{ErrorCode.DB_QUERY_EXECUTION}: {str(e)}"
                raise Exception(error_msg) from e
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                raise

    def execute_many(self, query, params_list):
        """Ejecuta inserción masiva optimizada usando fast_executemany"""
        if not params_list:
            return True
            
        max_retries = 2
        for attempt in range(max_retries):
            thread_conn = None
            try:
                # Usar conexión dedicada del hilo actual
                thread_conn = self.get_thread_connection("exec_many")
                if not thread_conn:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    raise Exception("Unable to establish database connection")

                cursor = thread_conn.cursor()
                # Optimización crítica para SQL Server - acelera hasta 100x
                try:
                    cursor.fast_executemany = True
                except Exception:
                    pass
                
                cursor.executemany(query, params_list)
                thread_conn.commit()
                return True
            except Exception as e:
                try:
                    if thread_conn:
                        thread_conn.rollback()
                except Exception:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                self._log(f"Error en execute_many: {e}", "ERROR")
                return False
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass

    def is_connection_valid(self):
        """Validates if the current database connection is active and functional"""
        try:
            if not self.conn:
                return False
            
            # Test connection with a simple query
            test_cursor = self.conn.cursor()
            test_cursor.execute("SELECT 1")
            test_cursor.fetchone()
            test_cursor.close()
            return True
        except Exception:
            return False
    
    def ensure_connection(self):
        """Ensures we have a valid database connection, reconnecting if necessary"""
        if not self.is_connection_valid():
            try:
                # Close any existing connection
                if self.conn:
                    try:
                        self.conn.close()
                    except Exception:
                        pass
                    self.conn = None
                    self.cursor = None
                
                # Reconnect
                if self.server and self.database:
                    self.connect(self.server, self.database, self.user, self.password)
                    return True
                else:
                    self._log("Cannot reconnect: missing server or database configuration", "WARNING")
                    return False
            except Exception as e:
                self._log(f"Failed to ensure database connection: {str(e)}", "ERROR")
                return False
        return True

    def fetch_data(self, query, params=None):
        """SELECT con conexión por-hilo y reintentos sin tocar self.conn global"""
        max_retries = 3
        for attempt in range(max_retries):
            cursor = None
            thread_conn = None
            try:
                # Conexión dedicada del hilo
                thread_conn = self.get_thread_connection("fetch")
                if not thread_conn:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    raise Exception("Unable to establish database connection")

                cursor = thread_conn.cursor()
                cursor.execute(query, params or ())
                result = cursor.fetchall()

                if getattr(self, 'debug_enabled', False):
                    self._log(f"[DB DEBUG] Query executed successfully: {len(result) if result else 0} rows returned", "DEBUG")
                return result

            except pyodbc.Error as e:
                error_code = getattr(e, 'args', [''])[0] if hasattr(e, 'args') else str(e)
                error_msg = str(e)
                # Errores de conexión: limpiar conexión del hilo y reintentar
                if error_code in ['HY000', 'HY010', '08S01', '08003', '07005']:
                    if getattr(self, 'debug_enabled', False):
                        self._log(f"[DB DEBUG] Connection error detected on attempt {attempt + 1}: {error_code}", "DEBUG")
                    try:
                        thread_key = f"fetch_{threading.current_thread().name}"
                        with self._pool_lock:
                            if thread_key in self._connection_pool:
                                try:
                                    self._connection_pool[thread_key].close()
                                except Exception:
                                    pass
                                del self._connection_pool[thread_key]
                    except Exception:
                        pass
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                # Log detallado
                detailed_error = f"""
            Error en consulta SQL:
            Query: {query}
            Params: {params}
            Error Code: {error_code}
            Error: {error_msg}
            Attempt: {attempt + 1}/{max_retries}
            """
                self._log(detailed_error, "ERROR")
                if attempt == max_retries - 1:
                    raise Exception(f"Database query failed after {max_retries} attempts: {error_msg}")
            except Exception as e:
                error_msg = f"""
            Unexpected error in database query:
            Query: {query}
            Params: {params}
            Error: {str(e)}
            Attempt: {attempt + 1}/{max_retries}
            """
                self._log(error_msg, "ERROR")
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
        return []

    def fetch_data_threadsafe(self, query, params=None, thread_name="generic"):
        """Ejecuta una SELECT usando una conexión dedicada para el hilo actual."""
        try:
            thread_conn = self.get_thread_connection(thread_name)
            if not thread_conn:
                return []
            cursor = thread_conn.cursor()
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            # print(f"[DB DEBUG] Error en fetch_data_threadsafe('{thread_name}'): {e}")  # DEBUG COMENTADO
            return []

    def execute_query_threadsafe(self, query, params=None, thread_name="generic"):
        """Ejecuta DML/DDL usando una conexión dedicada para el hilo actual."""
        try:
            thread_conn = self.get_thread_connection(thread_name)
            if not thread_conn:
                return False
            cursor = thread_conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            thread_conn.commit()
            cursor.close()
            return True
        except Exception as e:
            try:
                thread_conn.rollback()
            except Exception:
                pass
            # print(f"[DB DEBUG] Error en execute_query_threadsafe('{thread_name}'): {e}")  # DEBUG COMENTADO
            return False
    
    def obtener_alertas_stock_chunk(self, start_row=1, fetch_size=500, deposito='0301'):
        """Obtiene alertas de stock en chunks para carga paralela con manejo robusto de errores ODBC
        
        Args:
            start_row: Fila inicial (1-indexed)
            fetch_size: Cantidad de filas a obtener
            deposito: Código de depósito (por defecto 0301 como recup.py)
            
        Returns:
            list: Lista de alertas en el chunk especificado
        """
        import time
        query_start = time.perf_counter()
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                # Usar conexión independiente para este hilo
                thread_conn = self.get_thread_connection("stock_chunk")
                if not thread_conn:
                    # print(f"[DB DEBUG] No se pudo obtener conexión para hilo en intento {attempt + 1}")  # DEBUG COMENTADO
                    continue
                
                # Consulta optimizada con CTE para mejor performance
                query = """
                    WITH stock_summary AS (
                        SELECT 
                            d.c_codarticulo,
                            SUM(d.n_cantidad) as stock_total,
                            COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') as C_DESCRI,
                            COALESCE(p.C_DESCRI, 'SIN DESCRIPCIÓN') as C_DESCRI_FULL
                        FROM MA_DEPOPROD d
                        INNER JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.C_CODIGO
                        WHERE d.c_coddeposito = ?
                        GROUP BY d.c_codarticulo, p.cu_descripcion_corta, p.C_DESCRI
                        HAVING SUM(d.n_cantidad) < 21
                    ),
                    stock_ranked AS (
                        SELECT 
                            c_codarticulo AS codigo,
                            C_DESCRI AS descripcion,
                            CAST(stock_total AS INT) AS stock,
                            CASE
                                WHEN stock_total BETWEEN 15 AND 20 THEN 'Leve'  
                                WHEN stock_total BETWEEN 8 AND 14 THEN 'Media'
                                ELSE 'Crítica'
                            END AS nivel,
                            ROW_NUMBER() OVER (ORDER BY stock_total ASC) as rn,
                            C_DESCRI_FULL AS desc_larga
                        FROM stock_summary
                    )
                    SELECT codigo, desc_corta, 'Dep. ' + CAST(? AS VARCHAR) as sede, stock, nivel, '' as dummy1, '' as dummy2, desc_larga
                    FROM stock_ranked
                    WHERE rn BETWEEN ? AND ?
                    """
                
                # Parámetros para consulta CTE: rango BETWEEN
                start_rn = start_row
                end_rn = start_row + fetch_size - 1
                
                # Usar conexión y cursor específicos del hilo para evitar errores de secuencia
                cursor = thread_conn.cursor()
                cursor.execute(query, (deposito, start_rn, end_rn))
                result = cursor.fetchall()
                cursor.close()
                
                # Debug logging solo en primer intento exitoso
                if attempt == 0:
                    query_time = time.perf_counter() - query_start
                    # print(f"[DB DEBUG] Chunk query: offset={offset}, fetch_size={fetch_size}, deposito={deposito}")  # DEBUG COMENTADO
                    # print(f"[DB DEBUG] Returned {len(result)} rows in {query_time:.3f}s")  # DEBUG COMENTADO
                    
                    if result and len(result) > 0:
                        first_stock = result[0][2] if len(result[0]) > 2 else "N/A"
                        last_stock = result[-1][2] if len(result[-1]) > 2 else "N/A"
                        # print(f"[DB DEBUG] Stock range: {first_stock} to {last_stock}")  # DEBUG COMENTADO
                
                return result
                
            except Exception as e:
                query_time = time.perf_counter() - query_start
                error_msg = str(e)
                
                # Manejar errores ODBC específicos
                if "HY010" in error_msg or "HY000" in error_msg:
                    # print(f"[DB DEBUG] Error ODBC en intento {attempt + 1}: {error_msg}")  # DEBUG COMENTADO
                    
                    # Cerrar SOLO la conexión de este hilo y limpiarla del pool
                    try:
                        thread_key = f"stock_chunk_{threading.current_thread().name}"
                        with self._pool_lock:
                            try:
                                # Cerrar cursor local si sigue abierto
                                try:
                                    cursor.close()
                                except Exception:
                                    pass
                                # Cerrar conexión del pool para este hilo
                                if thread_key in self._connection_pool:
                                    try:
                                        self._connection_pool[thread_key].close()
                                    except Exception:
                                        pass
                                    del self._connection_pool[thread_key]
                            except Exception:
                                pass
                    except Exception:
                        pass
                    
                    # Esperar antes de reintentar
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    # Error no recuperable
                    # print(f"[DB DEBUG] Error no recuperable (tiempo: {query_time:.3f}s): {error_msg}")  # DEBUG COMENTADO
                    return []
        
        # Si llegamos aquí, todos los intentos fallaron
        # print(f"[DB DEBUG] Chunk fallido después de {max_retries} intentos")  # DEBUG COMENTADO
        return []
    
    def get_subgroup_name(self, code):
        """Obtiene el nombre descriptivo de un subgrupo dado su código."""
        try:
            result = self.fetch_data(
                "SELECT C_DESCRIPCIO FROM MA_SUBGRUPOS WHERE C_CODIGO = ?",
                (code,)
            )
            return result[0][0] if result else None
        except Exception:
            return None

    def get_department_name(self, code):
        """Obtiene el nombre descriptivo de un departamento dado su código."""
        try:
            result = self.fetch_data(
                "SELECT C_DESCRIPCIO FROM MA_DEPARTAMENTOS WHERE C_CODIGO = ?",
                (code,)
            )
            return result[0][0] if result else None
        except Exception:
            return None

    def get_group_name(self, code):
        """Obtiene el nombre descriptivo de un grupo dado su código."""
        try:
            result = self.fetch_data(
                "SELECT C_DESCRIPCIO FROM MA_GRUPOS WHERE C_CODIGO = ?",
                (code,)
            )
            return result[0][0] if result else None
        except Exception:
            return None

    def obtener_ventas_completas_tra(self, fecha_inicio, fecha_fin, sede_codigo, limit=None, exclude_depts=None):
        """Obtiene ventas completas TRA con jerarquía para carga inicial
        
        Args:
            fecha_inicio: Fecha inicio del rango
            fecha_fin: Fecha fin del rango  
            sede_codigo: Código de sede/depósito
            limit: Límite de registros (para carga inicial)
            exclude_depts: Departamentos a excluir
            
        Returns:
            list: Lista de ventas con jerarquía incluida
        """
        try:
            # Construir cláusula de exclusión
            exclude_clause = ""
            if exclude_depts:
                placeholders_ex = ','.join(['?'] * len(exclude_depts))
                exclude_clause = f"AND p.C_DEPARTAMENTO NOT IN ({placeholders_ex})"

            query = f"""
                SELECT 
                    i.c_Codarticulo AS codigo,
                    COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') AS descripcion,
                    COALESCE(p.C_DEPARTAMENTO, '') AS departamento,
                    COALESCE(p.C_GRUPO, '') AS grupo,
                    COALESCE(p.C_SUBGRUPO, '') AS subgrupo,
                    SUM(CASE 
                        WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                        WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                        ELSE 0 
                    END) AS neto,
                    0.0 AS precio,
                    0.0 AS impuesto1,
                    0.0 AS costo,
                    COALESCE(p.C_DESCRI, 'SIN DESCRIPCIÓN') AS descripcion_larga
                FROM TR_INVENTARIO i
                LEFT JOIN MA_PRODUCTOS p ON i.c_Codarticulo = p.C_CODIGO
                WHERE i.f_fecha BETWEEN CONVERT(DATE, ?, 105) AND CONVERT(DATE, ?, 105)
                AND i.c_Concepto IN ('VEN', 'DEV')
                AND i.c_Deposito LIKE ?
                {exclude_clause}
                GROUP BY 
                    i.c_Codarticulo,
                    p.cu_descripcion_corta,
                    p.C_DESCRI,
                    p.C_DEPARTAMENTO,
                    p.C_GRUPO,
                    p.C_SUBGRUPO,
                    p.C_DESCRI
                ORDER BY neto DESC
            """
            
            if limit:
                query = query.replace("ORDER BY neto DESC", f"ORDER BY neto DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY")
                
            fecha_inicio_str = fecha_inicio.strftime("%d-%m-%Y")
            fecha_fin_str = fecha_fin.strftime("%d-%m-%Y")
            
            params = [fecha_inicio_str, fecha_fin_str, sede_codigo]
            if exclude_depts:
                params.extend(exclude_depts)
                
            return self.fetch_data(query, tuple(params))
        except Exception as e:
            print(f"Error obteniendo ventas TRA completas: {str(e)}")
            return []
    
    def obtener_ventas_por_producto_chunk(self, fecha_inicio, fecha_fin, sede_codigo, 
                                         start_row=1, fetch_size=1000, include_zero_sales=False,
                                         exclude_depts=None):
        """Obtiene ventas TRA en chunks para carga paralela - OPTIMIZADO
        
        Args:
            fecha_inicio: Fecha inicio del rango
            fecha_fin: Fecha fin del rango  
            sede_codigo: Código de sede/depósito o lista de depósitos
            start_row: Fila inicial (1-indexed)
            fetch_size: Cantidad de filas a obtener
            include_zero_sales: Si True, incluye productos con neto <= 0
            exclude_depts: Lista de departamentos a excluir
        """
        try:
            # OPTIMIZACIÓN CRÍTICA: CTE + NOLOCK + filtro dinámico por depósito
            is_list = isinstance(sede_codigo, (list, tuple))
            if is_list:
                depositos_list = list(sede_codigo)
                global_query = False
            else:
                global_query = (sede_codigo in (None, '%', '00', 'ICH', 'ALL'))
                depositos_list = [sede_codigo] if not global_query else []
            
            # Construir cláusula de exclusión
            exclude_clause = ""
            if exclude_depts:
                placeholders_ex = ','.join(['?'] * len(exclude_depts))
                exclude_clause = f"AND p.C_DEPARTAMENTO NOT IN ({placeholders_ex})"
            
            # Construir cláusula HAVING dinámicamente
            having_clause = ""
            if not include_zero_sales:
                having_clause = """HAVING SUM(CASE 
                            WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                            WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                            ELSE 0 
                        END) > 0"""
            
            # Parametros para la query
            params = [fecha_inicio.strftime("%d-%m-%Y"), fecha_fin.strftime("%d-%m-%Y")]
            
            # Construir filtro de depósitos
            dep_filter = ""
            if is_list:
                placeholders_dep = ','.join(['?'] * len(depositos_list))
                dep_filter = f"AND i.c_Deposito IN ({placeholders_dep})"
                params.extend(depositos_list)
            elif not global_query:
                dep_filter = "AND i.c_Deposito = ?"
                params.append(sede_codigo)

            # CTE común - calcula ventas por producto
            cte_part = f"""
                WITH VentasAgregadas AS (
                    SELECT 
                        RTRIM(LTRIM(i.c_Codarticulo)) AS codigo,
                        SUM(CASE 
                            WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                            WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                            ELSE 0 
                        END) AS neto
                    FROM TR_INVENTARIO i WITH (NOLOCK)
                    WHERE i.f_fecha BETWEEN CONVERT(DATE, ?, 105) AND CONVERT(DATE, ?, 105)
                        AND i.c_Concepto IN ('VEN', 'DEV') 
                        {dep_filter}
                    GROUP BY i.c_Codarticulo
                    {having_clause}
                )
            """
            
            # Query principal
            if include_zero_sales:
                # MODO MASIVO: FROM MA_PRODUCTOS LEFT JOIN Ventas
                main_part = f"""
                    SELECT DISTINCT
                        RTRIM(LTRIM(p.C_CODIGO)) AS codigo,
                        COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') AS descripcion,
                        COALESCE(p.C_DEPARTAMENTO, '') AS departamento,
                        COALESCE(p.C_GRUPO, '') AS grupo,
                        COALESCE(p.C_SUBGRUPO, '') AS subgrupo,
                        COALESCE(v.neto, 0) AS neto,
                        COALESCE(p.n_precio1, 0) AS precio,
                        COALESCE(p.n_impuesto1, 0) AS impuesto1,
                        COALESCE(p.n_costoact, 0) AS costo,
                        COALESCE(p.C_DESCRI, 'SIN DESCRIPCIÓN') AS descripcion_larga,
                        p.C_DESCRI as desc_larga_raw
                    FROM MA_PRODUCTOS p WITH (NOLOCK)
                    LEFT JOIN VentasAgregadas v ON p.C_CODIGO = v.codigo
                    WHERE 1=1 {exclude_clause}
                    ORDER BY COALESCE(v.neto, 0) DESC, RTRIM(LTRIM(p.C_CODIGO)) ASC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """
            else:
                # MODO NORMAL: FROM Ventas LEFT JOIN MA_PRODUCTOS
                main_part = f"""
                    SELECT DISTINCT
                        RTRIM(LTRIM(v.codigo)) AS codigo,
                        COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') AS descripcion,
                        COALESCE(p.C_DEPARTAMENTO, '') AS departamento,
                        COALESCE(p.C_GRUPO, '') AS grupo,
                        COALESCE(p.C_SUBGRUPO, '') AS subgrupo,
                        v.neto,
                        COALESCE(p.n_precio1, 0) AS precio,
                        COALESCE(p.n_impuesto1, 0) AS impuesto1,
                        COALESCE(p.n_costoact, 0) AS costo,
                        COALESCE(p.C_DESCRI, 'SIN DESCRIPCIÓN') AS descripcion_larga,
                        p.C_DESCRI as desc_larga_raw
                    FROM VentasAgregadas v
                    LEFT JOIN MA_PRODUCTOS p WITH (NOLOCK) ON v.codigo = p.C_CODIGO
                    WHERE 1=1 {exclude_clause}
                    ORDER BY v.neto DESC, RTRIM(LTRIM(v.codigo)) ASC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """
            
            # ORDEN DE PARÁMETROS CRÍTICO:
            # 1. Fechas y Sede (ya están en 'params')
            
            # 2. Exclusiones (si existen)
            if exclude_depts:
                params.extend(exclude_depts)
            
            # 3. Paginación (OFFSET y FETCH NEXT)
            params.append(max(0, start_row-1))
            params.append(fetch_size)
            
            query = cte_part + main_part
            
            # Ejecutar usando conexión específica del hilo
            thread_conn = self.get_thread_connection("tra_chunk")
            if not thread_conn:
                return []
            cursor = thread_conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Error obteniendo chunk de ventas TRA: {str(e)}")
            return []
    
    def obtener_fechas_criticas_tra(self, codigos, sede_codigo):
        """
        Obtiene fecha de actualización, última venta y suma de ventas desde la actualización
        para un conjunto de productos en una sede.
        """
        if not codigos:
            return {}
            
        fechas = {}
        chunk_size = 1000
        
        try:
            for i in range(0, len(codigos), chunk_size):
                chunk = codigos[i:i + chunk_size]
                placeholders = ','.join(['?'] * len(chunk))
                
                query = f"""
                    SELECT 
                        RTRIM(LTRIM(p.C_CODIGO)) as codigo,
                        p.Update_date,
                        dates.last_ven,
                        dates.total_qty
                    FROM MA_PRODUCTOS p WITH (NOLOCK)
                    OUTER APPLY (
                        SELECT 
                            MAX(i.f_fecha) as last_ven,
                            SUM(CASE WHEN i.c_Concepto = 'DEV' THEN i.n_Cantidad * -1 ELSE i.n_Cantidad END) AS total_qty
                        FROM TR_INVENTARIO i WITH (NOLOCK)
                        WHERE i.c_Codarticulo = p.C_CODIGO 
                          AND (i.c_Concepto = 'VEN' OR i.c_Concepto = 'DEV')
                          AND i.f_fecha >= p.Update_date
                          AND (i.c_Deposito = ? OR ? IN ('00', 'ICH', 'ALL', '%'))
                    ) dates
                    WHERE p.C_CODIGO IN ({placeholders})
                """
                
                params = [sede_codigo, sede_codigo] + list(chunk)
                rows = self.fetch_data(query, params)
                
                for row in rows:
                    codigo = str(row[0]).strip()
                    fechas[codigo] = {
                        'update_date': row[1],
                        'last_ven': row[2],
                        'total_sales': float(row[3] or 0)
                    }
                    
            return fechas
        except Exception as e:
            print(f"Error obteniendo fechas críticas TRA: {str(e)}")
            return fechas

    def obtener_fechas_liquidacion_y_ventas(self, codigos, depositos, dias_estudio=365, dias_obj=30):
        """
        Obtiene fecha de última liquidación, fecha de última venta y unidades vendidas
        por períodos en cascada (dias_obj, dias_obj*2, dias_obj*4 ... dias_obj²) para un
        conjunto de productos y depósitos. Todo en una sola consulta SQL.

        Returns:
            dict: {
                codigo: {
                    'ultima_liquidacion': date,
                    'ultima_venta': date,
                    'periodos': {30: float, 60: float, 120: float, ...}  # unidades por período
                }
            }
        """
        if not codigos or not depositos:
            return {}

        # Construir ventanas en cascada: [N, 2N, 3N] donde N = dias_obj
        # Máximo = dias_obj × 3 (sin valores hardcodeados)
        max_dias = int(dias_obj * 3)
        periodos = [int(dias_obj), int(dias_obj * 2), max_dias]

        resultado = {}
        chunk_size = 1000

        try:
            placeholders_deps = ','.join(['?'] * len(depositos))

            # Agregate CASE WHEN expressions para el OUTER APPLY
            cases_ven = ',\n                            '.join([
                f"SUM(CASE WHEN i.c_Concepto = 'VEN' AND i.f_fecha >= DATEADD(day, -{p}, GETDATE()) THEN i.n_cantidad ELSE 0 END)"
                f" - SUM(CASE WHEN i.c_Concepto = 'DEV' AND i.f_fecha >= DATEADD(day, -{p}, GETDATE()) THEN i.n_cantidad ELSE 0 END)"
                f" as units_{p}d"
                for p in periodos
            ])
            # Referencias a las columnas del OUTER APPLY en el SELECT exterior
            select_period_cols = ',\n                        '.join([f"stats.units_{p}d" for p in periodos])

            for i in range(0, len(codigos), chunk_size):
                chunk = codigos[i:i + chunk_size]
                placeholders_cods = ','.join(['?'] * len(chunk))

                query = f"""
                    SELECT
                        RTRIM(LTRIM(p.C_CODIGO)) as codigo,
                        ISNULL(liq.ultima_liquidacion, p.Update_date) as ultima_liquidacion,
                        stats.last_sale as ultima_venta,
                        {select_period_cols}
                    FROM MA_PRODUCTOS p WITH (NOLOCK)
                    OUTER APPLY (
                        SELECT MAX(h.d_fechaCambio) as ultima_liquidacion
                        FROM MA_HISTORICO_COSTO_PRECIO h WITH (NOLOCK)
                        WHERE h.c_codarticulo = p.C_CODIGO
                          AND h.c_procesoOrigen = 'REGISTRO DE FACTURA'
                    ) liq
                    OUTER APPLY (
                        SELECT
                            MAX(i.f_fecha) as last_sale,
                            {cases_ven}
                        FROM TR_INVENTARIO i WITH (NOLOCK)
                        WHERE i.c_Codarticulo = p.C_CODIGO
                            AND i.c_Deposito IN ({placeholders_deps})
                            AND i.f_fecha >= DATEADD(day, -{max_dias}, GETDATE())
                            AND (i.c_Concepto = 'VEN' OR i.c_Concepto = 'DEV')
                    ) stats
                    WHERE p.C_CODIGO IN ({placeholders_cods})
                """

                params = list(depositos) + list(chunk)
                rows = self.fetch_data(query, params)

                for row in rows:
                    codigo = str(row[0]).strip()
                    periodos_vals = {}
                    # Columnas: 0=codigo, 1=ult_liq, 2=ult_venta, 3..N-1=periods, N=dummy
                    for idx, p in enumerate(periodos):
                        val = row[3 + idx]
                        periodos_vals[p] = float(val or 0)
                    resultado[codigo] = {
                        'ultima_liquidacion': row[1],
                        'ultima_venta': row[2],
                        'periodos': periodos_vals
                    }
            return resultado
        except Exception as e:
            print(f"Error en obtener_fechas_liquidacion_y_ventas: {str(e)}")
            return resultado

    def obtener_depositos(self):
        """Obtiene lista de depósitos desde MA_DEPOSITO
        
        Returns:
            list: Lista de tuplas (c_coddeposito, c_descripcion)
        """
        try:
            query = """
                SELECT c_coddeposito, c_descripcion
                FROM MA_DEPOSITO
                ORDER BY c_coddeposito
            """
            result = self.fetch_data(query)
            return result if result else []
        except Exception as e:
            print(f"Error obteniendo depósitos: {str(e)}")
            return []
    
    def obtener_proveedores(self, search_text=None, limit=None):
        """Obtiene lista de proveedores desde MA_PROVEEDORES.
        
        Opcionalmente filtra por texto en código o descripción y limita la cantidad de filas.
        """
        try:
            base_query = (
                "SELECT c_codproveed, c_descripcio "
                "FROM MA_PROVEEDORES WITH (NOLOCK) "
            )
            params: list[str] = []
            filters = []
            if search_text:
                texto = f"%{search_text.strip()}%"
                filters.append("(c_codproveed LIKE ? OR c_descripcio LIKE ?)")
                params.extend([texto, texto])
            if filters:
                base_query += " WHERE " + " AND ".join(filters)
            base_query += " ORDER BY c_descripcio"
            if limit and limit > 0:
                base_query += f" OFFSET 0 ROWS FETCH NEXT {int(limit)} ROWS ONLY"
            result = self.fetch_data(base_query, params) or []
            return result
        except Exception as e:
            print(f"Error obteniendo proveedores: {str(e)}")
            return []
    
    def obtener_codigos_por_proveedor(self, cod_proveedor: str):
        """Obtiene códigos de producto asociados a un proveedor en MA_PRODXPROV.
        
        Args:
            cod_proveedor: Código del proveedor (c_codproveed/c_codprovee)
        
        Returns:
            list[str]: Lista de códigos de producto (c_codigo) asociados al proveedor
        """
        try:
            if not cod_proveedor:
                return []
            query = """
                SELECT DISTINCT c_codigo
                FROM MA_PRODXPROV WITH (NOLOCK)
                WHERE c_codprovee = ?
            """
            rows = self.fetch_data(query, (str(cod_proveedor).strip(),)) or []
            return [str(r[0]).strip() for r in rows if r and r[0] is not None]
        except Exception as e:
            print(f"Error obteniendo códigos por proveedor: {str(e)}")
            return []

    def obtener_proveedores_por_producto(self, search_text):
        """Obtiene proveedores asociados a uno o varios productos según código.
        
        Args:
            search_text: Texto a buscar en el código de producto (c_codigo, LIKE %texto%).
        
        Returns:
            list: Lista de tuplas (c_codproveed, c_descripcio) de proveedores únicos.
        """
        try:
            if not search_text:
                return []
            texto = f"%{str(search_text).strip()}%"
            query = """
                SELECT DISTINCT pr.c_codproveed, pr.c_descripcio
                FROM MA_PRODXPROV px WITH (NOLOCK)
                INNER JOIN MA_PROVEEDORES pr WITH (NOLOCK)
                    ON px.c_codprovee = pr.c_codproveed
                WHERE px.c_codigo LIKE ?
                ORDER BY pr.c_descripcio
            """
            rows = self.fetch_data(query, (texto,)) or []
            return [(str(r[0]).strip(), r[1]) for r in rows if r and r[0] is not None]
        except Exception as e:
            print(f"Error obteniendo proveedores por producto: {str(e)}")
            return []
    
    # Métodos legacy obtener_alertas_stock, obtener_alertas_stock_chunk y obtener_alertas_stock_multiples removidos.
    # Se reemplazan por obtener_quiebres_directos para el módulo Quiebre de Stock.

    def obtener_ventas_persisted_tra(self, sede="0301", dias_rango=365):
        """
        Carga la vista TRA completa desde la tabla de persistencia pal_productos_rotacion 
        filtrando por sede y rango de días.
        """
        try:
            sql = """
                SELECT 
                    p.C_CODIGO, 
                    p.C_DESCRI, 
                    p.C_DEPARTAMENTO, 
                    p.C_GRUPO, 
                    p.C_SUBGRUPO,
                    r.n_neto,
                    r.c_clasificacion
                FROM pal_productos_rotacion r WITH (NOLOCK)
                JOIN MA_PRODUCTOS p WITH (NOLOCK) ON r.c_codigo = p.C_CODIGO
                WHERE r.c_sede = ? AND r.n_dias_rango = ?
                ORDER BY r.n_neto DESC
            """
            return self.fetch_data(sql, (sede, dias_rango))
        except Exception as e:
            self._log(f"Error cargando ventas persistidas: {e}", "ERROR")
            return None

    def obtener_quiebres_directos(self, depositos, solo_alta_rotacion=True, sede_context="0301", 
                                 dias_context=365, nombre_sede_display=None, exclude_depts=None):
        """
        Identifica productos en quiebre de stock filtrando por rotación.
        Consolida todos los depósitos proporcionados como una sola unidad (Sede).
        """
        if not depositos:
            return []
            
        try:
            placeholders = ','.join(['?'] * len(depositos))
            sede_label = nombre_sede_display or sede_context
            
            # Construir cláusula de exclusión
            exclude_clause = ""
            if exclude_depts:
                placeholders_ex = ','.join(['?'] * len(exclude_depts))
                exclude_clause = f"AND p.C_DEPARTAMENTO NOT IN ({placeholders_ex})"
            
            # Parte opcional del JOIN para rotación con contexto dual
            rotation_join = ""
            rotation_where = ""
            if solo_alta_rotacion:
                if self.table_exists('pal_productos_rotacion'):
                    # Buscamos rotación EXCLUSIVAMENTE para la sede específica
                    rotation_join = f"""
                        INNER JOIN pal_productos_rotacion rot WITH (NOLOCK) 
                            ON p.C_CODIGO = rot.c_codigo 
                            AND rot.c_sede = '{sede_context}'
                            AND rot.n_dias_rango = {dias_context}
                    """
                    rotation_where = "AND rot.c_clasificacion IN ('ALTA', 'MEDIA')"
            
            # Query consolidada por Sede con Proyección de Venta Perdida Real
            query = f"""
                SELECT 
                    RTRIM(LTRIM(p.C_CODIGO)) as codigo,
                    COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') as descripcion,
                    COALESCE(p.C_DESCRI, 'SIN DESCRIPCIÓN') as descripcion_larga,
                    '{sede_label}' as sede,
                    ISNULL(liq.ultima_liquidacion, p.Update_date) as ultima_compra,
                    stats.last_sale as ultima_venta,
                    -- Cálculo de Venta Perdida Proyectada: (Ventas / Días con Stock) * Días en Quiebre
                    CAST(CEILING(
                        (CAST(ISNULL(stats.sold_units, 0) AS FLOAT) / 
                         NULLIF(DATEDIFF(DAY, ISNULL(liq.ultima_liquidacion, p.Update_date), stats.last_sale) + 1, 0)) -- Días con stock
                        * DATEDIFF(DAY, ISNULL(stats.last_sale, ISNULL(liq.ultima_liquidacion, p.Update_date)), GETDATE()) -- Días en quiebre
                    ) AS INT) as unidades_perdidas,
                    DATEDIFF(DAY, ISNULL(stats.last_sale, ISNULL(liq.ultima_liquidacion, p.Update_date)), GETDATE()) as dias_quiebre
                FROM MA_PRODUCTOS p WITH (NOLOCK)
                {rotation_join}
                OUTER APPLY (
                    SELECT MAX(h.d_fechaCambio) as ultima_liquidacion
                    FROM MA_HISTORICO_COSTO_PRECIO h WITH (NOLOCK)
                    WHERE h.c_codarticulo = p.C_CODIGO
                      AND h.c_procesoOrigen = 'REGISTRO DE FACTURA'
                ) liq
                CROSS APPLY (
                    SELECT 
                        SUM(ISNULL(n_cantidad, 0)) as total_stock
                    FROM MA_DEPOPROD WITH (NOLOCK)
                    WHERE c_codarticulo = p.C_CODIGO AND c_coddeposito IN ({placeholders})
                ) stock
                OUTER APPLY (
                    SELECT 
                        MAX(i.f_fecha) as last_sale,
                        SUM(CASE WHEN i.c_Concepto = 'VEN' THEN i.n_cantidad ELSE 0 END) - 
                        SUM(CASE WHEN i.c_Concepto = 'DEV' THEN i.n_cantidad ELSE 0 END) as sold_units
                    FROM TR_INVENTARIO i WITH (NOLOCK)
                    WHERE i.c_Codarticulo = p.C_CODIGO 
                        AND i.c_Deposito IN ({placeholders})
                        AND i.f_fecha >= ISNULL(liq.ultima_liquidacion, p.Update_date)
                        AND (i.c_Concepto = 'VEN' OR i.c_Concepto = 'DEV')
                ) stats
                WHERE stock.total_stock <= 0
                  AND stats.sold_units > 0 -- Solo si hubo movimiento previo para poder proyectar
                  {exclude_clause}
                  {rotation_where}
                ORDER BY unidades_perdidas DESC
            """
            
            # Los parámetros se combinan: depósitos (para stock) + depósitos (para stats) + departamentos excluidos
            params = depositos + depositos
            if exclude_depts:
                params.extend(exclude_depts)
                
            rows = self.fetch_data(query, params)
            
            quiebres = []
            for row in rows:
                # Retornar como tupla para compatibilidad con Treeview en app.py
                # Estructura: (codigo, descripcion, sede, unidades_perdidas, dias_quiebre, ultima_compra, ultima_venta, descripcion_larga)
                quiebres.append((
                    str(row[0]).strip(),      # codigo
                    str(row[1]).strip(),      # descripcion (corta)
                    row[3],                   # sede
                    float(row[6] or 0),       # unidades_perdidas
                    int(row[7] or 0),         # dias_quiebre
                    row[4],                   # ultima_compra (datetime)
                    row[5],                   # ultima_venta (datetime)
                    str(row[2]).strip()       # descripcion_larga
                ))
            return quiebres
            
        except Exception as e:
            print(f"Error en obtener_quiebres_directos: {str(e)}")
            return []

    def get_sedes_config(self):
        """
        Recupera la configuración de todas las sedes activas desde la tabla pal_sedes_configuracion.
        Retorna una lista de diccionarios con los detalles de conexión de cada sede.
        """
        query = """
            SELECT id, nombre_sede, ip_servidor, nombre_bd, usuario_bd, password_bd_enc, activa
            FROM pal_sedes_configuracion
            WHERE activa = 1
            ORDER BY nombre_sede ASC
        """
        try:
            rows = self.fetch_data(query)
            self._log(f"Se encontraron {len(rows)} sedes activas.", "INFO")
            sedes = []
            for row in rows:
                sedes.append({
                    'id': row[0],
                    'nombre_sede': row[1],
                    'ip_servidor': row[2],
                    'nombre_bd': row[3],
                    'usuario_bd': row[4],
                    'password_bd_enc': row[5],
                    'activa': row[6]
                })
            return sedes
        except Exception as e:
            self._log(f"Error crítico al obtener la configuración de sedes: {e}", "ERROR")
            # Relanzar la excepción para que la UI pueda manejarla
            raise Exception("No se pudieron obtener las configuraciones de sedes activas desde la base de datos.") from e


    def connect_to_vad20_sede(self, sede_config):
        """
        Establece una conexión pyodbc temporal a la base de datos VAD20 de una sede específica.
        Requiere un diccionario de configuración de sede obtenido de get_sedes_config().
        La contraseña se desencripta usando SecureCredentialsManager.
        """
        if not sede_config:
            raise Exception("Configuración de sede no proporcionada")

        server = sede_config.get('ip_servidor')
        database = sede_config.get('nombre_bd')
        user = sede_config.get('usuario_bd')
        encrypted_password = sede_config.get('password_bd_enc')

        if not server or not database:
            raise Exception(f"Configuración incompleta para sede {sede_config.get('nombre_sede', 'Unknown')}")

        password = None
        if encrypted_password and self.credentials_manager:
            try:
                password = self.credentials_manager.decrypt(encrypted_password)
            except Exception as e:
                self._log(f"Error desencriptando contraseña para {sede_config.get('nombre_sede')}: {e}", "ERROR")
                # fallback al password en texto plano si existe o seguir sin pass
                password = encrypted_password # Intento desesperado si no estaba encriptado realmente

        # Cadena de conexión simplificada para mayor compatibilidad
        # Algunos drivers antiguos fallan con Encrypt/TrustServerCertificate
        conn_str = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
        )

        if user:
            conn_str += f"UID={user};PWD={password or ''};"
        else:
            conn_str += "Trusted_Connection=yes;"
        
        # Agregar timeouts básicos
        conn_str += "Connection Timeout=30;"
        
        try:
            self._log(f"Intentando conectar a VAD20 ({sede_config.get('nombre_sede')}) en {server}...", "INFO")
            temp_conn = pyodbc.connect(conn_str)
            self._log(f"Conectado exitosamente a VAD20 para sede: {sede_config.get('nombre_sede')}", "INFO")
            return temp_conn
        except Exception as e:
            self._log(f"Fallo al conectar a VAD20 para sede {sede_config.get('nombre_sede')}: {e}", "ERROR")
            raise Exception(f"Fallo al conectar a VAD20 para {sede_config.get('nombre_sede')}. Verifique IP {server} y red.")

    def connect_to_vad10_sede(self, sede_config):
        """
        Establece una conexión pyodbc temporal a la base de datos VAD10 de una sede específica.
        Usa la misma IP y credenciales de la sede configurada, pero apunta a VAD10 en lugar de VAD20.
        Útil para obtener datos de usuarios/cajeras que residen en VAD10 de cada sede.
        """
        if not sede_config:
            raise Exception("Configuración de sede no proporcionada")

        server = sede_config.get('ip_servidor')
        user = sede_config.get('usuario_bd')
        encrypted_password = sede_config.get('password_bd_enc')

        if not server:
            raise Exception(f"Configuración incompleta para sede {sede_config.get('nombre_sede', 'Unknown')}")

        password = None
        if encrypted_password and self.credentials_manager:
            try:
                password = self.credentials_manager.decrypt(encrypted_password)
            except Exception as e:
                self._log(f"Error desencriptando contraseña para VAD10 {sede_config.get('nombre_sede')}: {e}", "ERROR")
                password = encrypted_password

        conn_str = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={server};"
            f"DATABASE=VAD10;"
        )

        if user:
            conn_str += f"UID={user};PWD={password or ''};"
        else:
            conn_str += "Trusted_Connection=yes;"

        conn_str += "Connection Timeout=30;"

        try:
            self._log(f"Intentando conectar a VAD10 ({sede_config.get('nombre_sede')}) en {server}...", "INFO")
            temp_conn = pyodbc.connect(conn_str)
            self._log(f"Conectado exitosamente a VAD10 para sede: {sede_config.get('nombre_sede')}", "INFO")
            return temp_conn
        except Exception as e:
            self._log(f"Fallo al conectar a VAD10 para sede {sede_config.get('nombre_sede')}: {e}", "ERROR")
            raise Exception(f"Fallo al conectar a VAD10 para {sede_config.get('nombre_sede')}. Verifique IP {server} y red.")

    def add_sede(self, sede_data):
        """Agrega una nueva sede a la tabla pal_sedes_configuracion."""
        query = """
            INSERT INTO pal_sedes_configuracion 
            (nombre_sede, ip_servidor, nombre_bd, usuario_bd, password_bd_enc, activa)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            sede_data['nombre_sede'],
            sede_data['ip_servidor'],
            sede_data['nombre_bd'],
            sede_data['usuario_bd'],
            sede_data.get('password_bd_enc'), # Usar .get por si es None
            sede_data['activa']
        )
        return self.execute_query(query, params)

    def update_sede(self, sede_id, sede_data):
        """Actualiza una sede existente en la tabla pal_sedes_configuracion."""
        query = """
            UPDATE pal_sedes_configuracion SET
            nombre_sede = ?,
            ip_servidor = ?,
            nombre_bd = ?,
            usuario_bd = ?,
            password_bd_enc = ?,
            activa = ?,
            fecha_modificacion = GETDATE()
            WHERE id = ?
        """
        params = (
            sede_data['nombre_sede'],
            sede_data['ip_servidor'],
            sede_data['nombre_bd'],
            sede_data['usuario_bd'],
            sede_data.get('password_bd_enc'),
            sede_data['activa'],
            sede_id
        )
        return self.execute_query(query, params)

    def delete_sede(self, sede_id):
        """Elimina una sede de la tabla pal_sedes_configuracion."""
        query = "DELETE FROM pal_sedes_configuracion WHERE id = ?"
        return self.execute_query(query, (sede_id,))

    def _get_factors_dict_for_range(self, year_start, year_end):
        """
        Obtiene un diccionario {(año, mes, día): factor} desde la BD principal
        para un rango de años dado.
        """
        try:
            query = """
                SELECT CAST(año AS INT), CAST(mes AS INT), CAST(dia AS INT), factor
                FROM [vad10]..FACTOR_DOLAR WITH (NOLOCK)
                WHERE CAST(año AS INT) BETWEEN ? AND ?
                ORDER BY año, mes, dia
            """
            rows = self.fetch_data(query, (year_start, year_end))
            factors = {}
            for r in rows:
                try:
                    # r: (año, mes, dia, factor)
                    key = (int(r[0]), int(r[1]), int(r[2]))
                    factors[key] = float(r[3])
                except:
                    continue
            return factors
        except Exception as e:
            self._log(f"Error obteniendo diccionario de factores: {e}", "ERROR")
            return {}

    def get_reporte_compras_por_cliente(self, connection, fecha_inicio, fecha_fin, 
                                        rif_filter=None, desc_filter=None, 
                                        progress_callback=None):
        """
        Obtiene reporte de compras uniendo MA_PAGOS (Sede) con FACTOR_DOLAR (Main) en Python.
        Soporta carga por chunks de días para actualizar barra de progreso.
        """
        import datetime
        
        # 1. Obtener Factores y Metadatos de la BD Principal (self)
        factors_dict = self._get_factors_dict_for_range(fecha_inicio.year, fecha_fin.year)
        
        # Cargar nombres de departamentos, grupos y subgrupos como mapeos (VAD10 -> Python)
        try:
            depts_raw = self.fetch_data("SELECT C_CODIGO, C_DESCRIPCIO FROM MA_DEPARTAMENTOS WITH (NOLOCK)")
            dept_map = {str(c).strip(): str(d).strip() for c, d in depts_raw if c}
            
            groups_raw = self.fetch_data("SELECT C_CODIGO, C_DESCRIPCIO FROM MA_GRUPOS WITH (NOLOCK)")
            group_map = {str(c).strip(): str(d).strip() for c, d in groups_raw if c}
            
            subs_raw = self.fetch_data("SELECT C_CODIGO, C_DESCRIPCIO FROM MA_SUBGRUPOS WITH (NOLOCK)")
            sub_map = {str(c).strip(): str(d).strip() for c, d in subs_raw if c}
        except Exception as e:
            self._log(f"Error cargando metadatos maestros: {e}", "WARNING")
            dept_map, group_map, sub_map = {}, {}, {}

        # Último factor conocido (fallback)
        last_factor = 1.0
        if factors_dict:
            # Ordenar por fecha para encontrar el último real
            sorted_keys = sorted(factors_dict.keys())
            last_factor = factors_dict[sorted_keys[-1]]

        # 2. Iterar por rango de fechas en chunks
        delta = fecha_fin - fecha_inicio
        total_days = delta.days + 1
        chunk_size = 5 # Procesar de 5 en 5 días
        
        all_rows = []
        
        cursor = connection.cursor()
        
        current_date = fecha_inicio
        days_processed = 0
        
        while current_date <= fecha_fin:
            chunk_end = min(current_date + datetime.timedelta(days=chunk_size - 1), fecha_fin)
            
            # Construir condiciones dinámicas
            where_clauses = ["p.F_Fecha BETWEEN CONVERT(DATETIME, ?, 120) AND CONVERT(DATETIME, ?, 120)"]
            params = [current_date.strftime('%Y-%m-%d 00:00:00'), chunk_end.strftime('%Y-%m-%d 23:59:59')]
            
            if rif_filter:
                where_clauses.append("p.C_RIF LIKE ?")
                params.append(f"%{rif_filter}%")
            if desc_filter:
                where_clauses.append("p.C_DESC_CLIENTE LIKE ?")
                params.append(f"%{desc_filter}%")
                
            where_sql = " AND ".join(where_clauses)
            
            # Query modificado: Omitimos JOINs a tablas de metadatos faltantes en sede
            query = f"""
                SELECT
                    p.C_RIF,
                    p.C_DESC_CLIENTE,
                    p.C_NUMERO,
                    p.F_Fecha,
                    t.COD_PRINCIPAL,
                    p.N_Total,
                    COALESCE(pr.cu_descripcion_corta, pr.C_DESCRI, 'SIN DESCRIPCIÓN') AS desc_corta,
                    pr.C_DEPARTAMENTO, 
                    pr.C_GRUPO,
                    pr.C_SUBGRUPO,
                    pr.c_marca,
                    t.CANTIDAD,
                    pr.C_DESCRI AS desc_larga
                FROM
                    MA_PAGOS p WITH (NOLOCK)
                JOIN
                    MA_TRANSACCION t WITH (NOLOCK) ON p.C_NUMERO = t.C_numero
                LEFT JOIN
                    MA_PRODUCTOS pr WITH (NOLOCK) ON t.COD_PRINCIPAL = pr.C_CODIGO
                WHERE
                    {where_sql}
                ORDER BY
                    p.C_DESC_CLIENTE, p.F_Fecha
            """
            
            try:
                cursor.execute(query, params)
                chunk_rows = cursor.fetchall()
                
                # Procesar en Python
                for r in chunk_rows:
                    # r: (rif, nombre, numero, fecha, prod_cod, total_bs, desc_corta, dept_code, group_code, sub_code, marca, cantidad, desc_larga)
                    fecha = r[3]
                    total_bs = float(r[5]) if r[5] else 0.0
                    
                    # Resolver nombres desde mapeos de la BD Principal
                    d_code = str(r[7]).strip() if r[7] else ""
                    g_code = str(r[8]).strip() if r[8] else ""
                    s_code = str(r[9]).strip() if r[9] else ""
                    
                    dept_name = dept_map.get(d_code, d_code)
                    group_name = group_map.get(g_code, g_code)
                    sub_name = sub_map.get(s_code, s_code)
                    
                    # Reconstruir la fila con los nombres resueltos para la UI
                    # (rif, name, num, date, prod_code, total_bs, desc_corta, dept_name, group_name, sub_name, marca, qty, desc_larga)
                    row_with_names = (
                        r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                        dept_name, group_name, sub_name, r[10], r[11], r[12]
                    )
                    
                    # Buscar factor
                    key = (fecha.year, fecha.month, fecha.day)
                    factor = factors_dict.get(key)
                    
                    if factor is None:
                        # Intentar buscar hacia atrás unos días sutilmente
                        factor = last_factor
                        for d in range(15):
                             prev = fecha - datetime.timedelta(days=d)
                             k = (prev.year, prev.month, prev.day)
                             if k in factors_dict:
                                 factor = factors_dict[k]
                                 break
                    
                    total_usd = total_bs / factor if factor else 0.0
                    
                    # Estructura de retorno compatible con UI:
                    # (rif, name, num, date, prod_code, total_bs, desc_corta, dept, grupo, sub, marca, qty, total_usd, desc_larga)
                    row_final = (
                        r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                        dept_name, group_name, sub_name, r[10], r[11], total_usd, r[12]
                    )
                    all_rows.append(row_final)
                    
            except Exception as e:
                self._log(f"Error procesando chunk: {e}", "ERROR")
            
            # Actualizar progreso
            days_in_chunk = (chunk_end - current_date).days + 1
            days_processed += days_in_chunk
            
            if progress_callback:
                progress_callback(days_processed, total_days)
            
            # Avanzar
            current_date = chunk_end + datetime.timedelta(days=1)
            
        cursor.close()
        return all_rows

    def get_dolar_factor(self, connection):
        """
        Obtiene el factor de cambio para el dólar (código 101) desde MA_MONEDAS.
        
        Args:
            connection: Conexión activa a la BD.
            
        Returns:
             float: El factor de cambio, o 1.0 si no se encuentra.
        """
        try:
            cursor = connection.cursor()
            # Usar FACTOR_DOLAR en lugar de MA_MONEDAS (REGLA: siempre buscar en vad10)
            query = """
                SELECT TOP 1 factor 
                FROM [vad10]..FACTOR_DOLAR WITH (NOLOCK) 
                ORDER BY año DESC, mes DESC, dia DESC
            """
            cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()
            
            if row and row[0]:
                return float(row[0])
            return 1.0
        except Exception as e:
            self._log(f"Error obteniendo factor dolar desde FACTOR_DOLAR: {e}", "WARNING")
            return 1.0

    def get_client_purchase_history(self, connection, client_ids: list, fecha_inicio, fecha_fin, progress_callback=None):
        """
        Obtiene historial de compras con cálculo USD en Python.
        Soporta chunking.
        """
        import datetime
        from collections import defaultdict
        
        if not client_ids:
            return []

        # 1. Factores
        factors_dict = self._get_factors_dict_for_range(fecha_inicio.year, fecha_fin.year)
        
        # 2. Chunking
        delta = fecha_fin - fecha_inicio
        total_days = delta.days + 1
        chunk_size = 10 
        
        # Agregador local: {(rif, nombre, yyyy-mm): {'total': 0.0, 'invoices': []}}
        aggregated = defaultdict(lambda: {'total': 0.0, 'invoices': []})
        client_names = {} # Map rif -> name
        
        cursor = connection.cursor()
        current_date = fecha_inicio
        days_processed = 0
        
        placeholders = ','.join(['?' for _ in client_ids])
        
        while current_date <= fecha_fin:
            chunk_end = min(current_date + datetime.timedelta(days=chunk_size - 1), fecha_fin)
            
            query = f"""
                SELECT 
                    p.C_RIF,
                    p.C_DESC_CLIENTE,
                    p.F_Fecha,
                    p.N_Total,
                    p.C_NUMERO
                FROM MA_PAGOS p WITH (NOLOCK)
                WHERE p.C_RIF IN ({placeholders})
                    AND p.F_Fecha BETWEEN CONVERT(DATETIME, ?, 120) AND CONVERT(DATETIME, ?, 120)
            """
            
            f_start = current_date.strftime('%Y-%m-%d 00:00:00')
            f_end = chunk_end.strftime('%Y-%m-%d 23:59:59')
            params = client_ids + [f_start, f_end]
            
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                for r in rows:
                    rif, name, fecha, total_bs, invoice_num = r
                    client_names[rif] = name
                    total_bs = float(total_bs) if total_bs else 0.0
                    
                    # Factor
                    key = (fecha.year, fecha.month, fecha.day)
                    factor = factors_dict.get(key)
                    if factor is None:
                        # Fallback simple
                        for d in range(15):
                             prev = fecha - datetime.timedelta(days=d)
                             k = (prev.year, prev.month, prev.day)
                             if k in factors_dict:
                                 factor = factors_dict[k]
                                 break
                        if not factor: factor = 1.0
                    
                    total_usd = total_bs / factor
                    
                    ym = fecha.strftime('%Y-%m')
                    aggregated[(rif, ym)]['total'] += total_usd
                    # Guardar info de factura (limitando a un número razonable de detalles si es necesario)
                    aggregated[(rif, ym)]['invoices'].append(f"{invoice_num} (${total_usd:,.2f})")
                    
            except Exception as e:
                self._log(f"Error en chunk history: {e}", "ERROR")

            # Progress
            days_in_chunk = (chunk_end - current_date).days + 1
            days_processed += days_in_chunk
            if progress_callback:
                progress_callback(days_processed, total_days)
                
            current_date = chunk_end + datetime.timedelta(days=1)
            
        cursor.close()
        
        # Formatear salida: [(client_id, client_name, year_month, total_usd, invoices_summary), ...]
        result = []
        for (rif, ym), data in aggregated.items():
            name = client_names.get(rif, "Unknown")
            total = data['total']
            invoices = data['invoices']
            
            # Crear resumen de facturas (máximo 5)
            if len(invoices) > 5:
                # Mostrar las primeras 5 y el conteo del resto
                inv_summary = "\n".join(invoices[:5]) + f"\n... y {len(invoices)-5} facturas más"
            else:
                inv_summary = "\n".join(invoices)
                
            result.append((rif, name, ym, total, inv_summary))
            
        result.sort(key=lambda x: (x[0], x[2]))
        return result

    def get_client_heatmap_history(self, connection, client_ids: list, fecha_inicio, fecha_fin, progress_callback=None):
        """
        Obtiene historial de compras enfocado en la hora para el mapa de calor.
        Usa JOIN con MA_TRANSACCION para consistencia con reportes de clientes.
        Retorna: lista de tuplas (rif, nombre, fecha, hora_int, total_usd)
        """
        import datetime
        
        # 1. Factores
        factors_dict = self._get_factors_dict_for_range(fecha_inicio.year, fecha_fin.year)
        
        cursor = connection.cursor()
        
        f_start = fecha_inicio.strftime('%Y-%m-%d 00:00:00')
        f_end = fecha_fin.strftime('%Y-%m-%d 23:59:59')
        
        if client_ids:
            placeholders = ','.join(['?' for _ in client_ids])
            query = f"""
                SELECT DISTINCT
                    p.C_RIF,
                    p.C_DESC_CLIENTE,
                    p.F_Fecha,
                    p.F_Hora,
                    p.N_Total
                FROM MA_PAGOS p WITH (NOLOCK)
                INNER JOIN MA_TRANSACCION t WITH (NOLOCK) ON p.C_NUMERO = t.C_numero
                WHERE p.C_RIF IN ({placeholders})
                    AND p.F_Fecha BETWEEN CONVERT(DATETIME, ?, 120) AND CONVERT(DATETIME, ?, 120)
            """
            params = client_ids + [f_start, f_end]
        else:
            query = f"""
                SELECT DISTINCT
                    p.C_RIF,
                    p.C_DESC_CLIENTE,
                    p.F_Fecha,
                    p.F_Hora,
                    p.N_Total
                FROM MA_PAGOS p WITH (NOLOCK)
                INNER JOIN MA_TRANSACCION t WITH (NOLOCK) ON p.C_NUMERO = t.C_numero
                WHERE p.F_Fecha BETWEEN CONVERT(DATETIME, ?, 120) AND CONVERT(DATETIME, ?, 120)
            """
            params = [f_start, f_end]
        
        result = []
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            for r in rows:
                rif, name, fecha, hora, total_bs = r
                hora_int = 0
                if hora:
                    try:
                        if hasattr(hora, 'hour'):
                            hora_int = hora.hour
                        else:
                            parts = str(hora).split()
                            if len(parts) > 1:
                                hora_int = int(parts[1].split(':')[0])
                            else:
                                hora_int = int(parts[0].split(':')[0])
                    except:
                        pass
                
                # Conversion USD
                total_bs = float(total_bs) if total_bs else 0.0
                key = (fecha.year, fecha.month, fecha.day)
                factor = factors_dict.get(key)
                if factor is None:
                    for d in range(15):
                         prev = fecha - datetime.timedelta(days=d)
                         k = (prev.year, prev.month, prev.day)
                         if k in factors_dict:
                             factor = factors_dict[k]
                             break
                    if not factor: factor = 1.0
                total_usd = total_bs / factor
                
                result.append((rif, name, fecha, hora_int, total_usd))
        except Exception as e:
            self._log(f"Error en heatmap history: {e}", "ERROR")
        finally:
            cursor.close()
            
        if progress_callback:
            progress_callback(100, 100)
            
        return result

    def get_ma_usuarios_map(self, connection=None):
        """
        Obtiene un mapa de código de usuario -> descripción.
        Si se proporciona connection, busca en esa base de datos (Sede).
        Si no, busca en la base de datos principal (VAD10).
        """
        def normalize(v):
            try:
                s = str(v or "").strip().lstrip('0')
                return s if s else "0"
            except: return ""

        posibles_columnas = ["codusuario", "c_codigo", "c_usuario", "cu_usuario", "c_codusu", "C_USUARIO"]
        rows = None
        
        # Determinar origen para el log
        if connection:
            try:
                # Intentar obtener info del servidor de la conexión
                server_info = str(connection.getinfo(pyodbc.SQL_SERVER_NAME))
                db_info = "Conexión Seleccionada"
                self._log(f"Obteniendo mapa de usuarios desde SERVER: {server_info} ({db_info})", "INFO")
            except:
                self._log("Obteniendo mapa de usuarios desde conexión externa proporcionada", "INFO")
        else:
            self._log(f"Obteniendo mapa de usuarios desde CONEXIÓN PRINCIPAL ({self.server})", "WARNING")

        for col in posibles_columnas:
            try:
                query = f"SELECT RTRIM(LTRIM({col})), descripcion FROM MA_USUARIOS WITH (NOLOCK)"
                if connection:
                    cursor = connection.cursor()
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    cursor.close()
                else:
                    rows = self.fetch_data(query)
                
                if rows:
                    break
            except Exception:
                continue
        
        if not rows:
            return {}
            
        return {normalize(r[0]): str(r[1]).strip() for r in rows if r and r[0]}

    def get_client_cajera_history(self, connection, client_ids: list = None, fecha_inicio = None, fecha_fin = None, progress_callback=None, usuarios_map=None):
        """
        Obtiene el historial de atención por cajera. Granularidad Diaria.
        
        Args:
            usuarios_map: Mapa de código -> nombre de usuarios. Si se proporciona, se usa directamente.
                         Si es None, se obtiene automáticamente de VAD10 y la sede.
        """
        import datetime
        from collections import defaultdict
        
        def normalize_user_id(v):
            try:
                s = str(v or "").strip().lstrip('0')
                return s if s else "0"
            except: return ""

        # 1. Factores de conversión 
        factors_dict = self._get_factors_dict_for_range(fecha_inicio.year, fecha_fin.year)
        
        # 2. Mapa de Usuarios (Estricto por sede)
        if usuarios_map is None:
            # Si no se pasó mapa, intentamos obtenerlo de la conexión actual de la sede (VAD20/VAD10)
            # pero NO usamos el fallback local para evitar cruce de datos entre sucursales
            try:
                usuarios_map = self.get_ma_usuarios_map(connection)
            except Exception:
                usuarios_map = {}
                self._log("No se pudo obtener mapa de usuarios de la sede. Se usarán códigos genéricos.", "WARNING")
        
        # 3. Chunking por fechas para progreso
        delta = fecha_fin - fecha_inicio
        total_days = delta.days + 1
        chunk_size = 10 
        
        # Agregador local: {(user_code, user_name, yyyy-mm-dd): {'total': 0.0, 'count': 0, 'invoices': []}}
        aggregated = defaultdict(lambda: {'total': 0.0, 'count': 0, 'invoices': []})
        
        cursor = connection.cursor()
        current_date = fecha_inicio
        days_processed = 0
        
        while current_date <= fecha_fin:
            chunk_end = min(current_date + datetime.timedelta(days=chunk_size - 1), fecha_fin)
            
            # Filtro dinámico de RIFs
            where_rif = ""
            params_rif = []
            if client_ids:
                placeholders = ','.join(['?' for _ in client_ids])
                where_rif = f"AND p.C_RIF IN ({placeholders})"
                params_rif = client_ids
            
            query = f"""
                SELECT 
                    p.C_USUARIO,
                    p.F_Fecha,
                    p.N_Total,
                    p.C_NUMERO,
                    p.C_DESC_CLIENTE
                FROM MA_PAGOS p WITH (NOLOCK)
                WHERE p.F_Fecha BETWEEN CONVERT(DATETIME, ?, 120) AND CONVERT(DATETIME, ?, 120)
                {where_rif}
            """
            
            f_start = current_date.strftime('%Y-%m-%d 00:00:00')
            f_end = chunk_end.strftime('%Y-%m-%d 23:59:59')
            params = [f_start, f_end] + params_rif
            
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                for r in rows:
                    user_code_raw, fecha, total_bs, invoice_num, client_name = r
                    user_code_norm = normalize_user_id(user_code_raw)
                    user_name = usuarios_map.get(user_code_norm, f"Usuario ({user_code_raw})")
                    
                    total_bs = float(total_bs) if total_bs else 0.0
                    
                    # Factor de cambio
                    key = (fecha.year, fecha.month, fecha.day)
                    factor = factors_dict.get(key)
                    if factor is None:
                        for d in range(15):
                             prev = fecha - datetime.timedelta(days=d)
                             k = (prev.year, prev.month, prev.day)
                             if k in factors_dict:
                                 factor = factors_dict[k]
                                 break
                        if not factor: factor = 1.0
                    
                    total_usd = total_bs / factor
                    ymd = fecha.strftime('%Y-%m-%d')
                    
                    agg_key = (user_code_norm, user_name, ymd)
                    aggregated[agg_key]['total'] += total_usd
                    aggregated[agg_key]['count'] += 1
                    aggregated[agg_key]['invoices'].append(f"{invoice_num}: {client_name} (${total_usd:,.2f})")
                    
            except Exception:
                pass

            days_in_chunk = (chunk_end - current_date).days + 1
            days_processed += days_in_chunk
            if progress_callback:
                progress_callback(days_processed, total_days)
                
            current_date = chunk_end + datetime.timedelta(days=1)
            
        cursor.close()
        
        # Formatear salida: [(user_code, user_name, year_month_day, total_usd, invoices_summary), ...]
        result = []
        for (u_code, u_name, ymd), data in aggregated.items():
            total = data['total']
            count = data['count']
            invoices = data['invoices']
            
            if len(invoices) > 5:
                inv_summary = f"Total facturado: ${total:,.2f} en {count} tickets.\n" + \
                             "\n".join(invoices[:5]) + f"\n... y {len(invoices)-5} facturas más"
            else:
                inv_summary = f"Total facturado: ${total:,.2f} en {count} tickets.\n" + "\n".join(invoices)
                
            result.append((u_code, u_name, ymd, total, inv_summary))
            
        result.sort(key=lambda x: (x[0], x[2]))
        return result

    def obtener_proveedores_detalle_por_producto(self, cod_producto):
        """
        Obtiene detalles de proveedores asociados a un producto desde MA_PRODXPROV y MA_PROVEEDORES.
        
        Args:
            cod_producto (str): Código del producto.
            
        Returns:
            list: Lista de tuplas (c_codprovee, c_descripcio, c_numero_compra, d_fecha)
        """
        try:
            query = """
                SELECT 
                    pxp.c_codprovee,
                    p.C_descripcio,
                    pxp.c_numero_compra,
                    pxp.d_fecha,
                    pxp.n_costo
                FROM MA_PRODXPROV pxp WITH (NOLOCK)
                JOIN MA_PROVEEDORES p WITH (NOLOCK) ON pxp.c_codprovee = p.c_codproveed
                WHERE pxp.c_codigo = ?
                ORDER BY pxp.d_fecha DESC
            """
            return self.fetch_data(query, (str(cod_producto).strip(),))
        except Exception as e:
            self._log(f"Error obteniendo detalles de proveedores para {cod_producto}: {e}", "ERROR")
            return []

    def obtener_ultimas_compras_bulk(self, codigos_productos: List[str]) -> Dict[str, str]:
        """
        Obtiene el proveedor de la última compra para una lista de productos de forma eficiente.
        
        Args:
            codigos_productos: Lista de códigos de productos.
            
        Returns:
            dict: Mapeo codigo_producto -> nombre_proveedor
        """
        if not codigos_productos:
            return {}
            
        resultados = {}
        try:
            # Límite de parámetros SQL Server (2100)
            BATCH_SIZE = 2000
            for i in range(0, len(codigos_productos), BATCH_SIZE):
                chunk = codigos_productos[i:i + BATCH_SIZE]
                placeholders = ','.join(['?'] * len(chunk))
                
                query = f"""
                WITH UltimaCompra AS (
                    SELECT 
                        pxp.c_codigo, 
                        p.C_descripcio as proveedor_nombre,
                        pxp.d_fecha,
                        ROW_NUMBER() OVER (PARTITION BY pxp.c_codigo ORDER BY pxp.d_fecha DESC) as rn
                    FROM MA_PRODXPROV pxp WITH (NOLOCK)
                    JOIN MA_PROVEEDORES p WITH (NOLOCK) ON pxp.c_codprovee = p.c_codproveed
                    WHERE pxp.c_codigo IN ({placeholders})
                )
                SELECT c_codigo, proveedor_nombre, d_fecha
                FROM UltimaCompra
                WHERE rn = 1
                """
                
                rows = self.fetch_data(query, chunk)
                if rows:
                    for cod, prov, fecha in rows:
                        fecha_str = f" ({fecha.strftime('%d/%m/%Y')})" if fecha else ""
                        resultados[str(cod).strip()] = f"{str(prov).strip()}{fecha_str}"
            
            return resultados
        except Exception as e:
            self._log(f"Error en obtener_ultimas_compras_bulk: {e}", "ERROR")
            return {}
