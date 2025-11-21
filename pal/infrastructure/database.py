"""
Gestor de base de datos para la aplicación PAL
"""
import pyodbc
import configparser
import time
import threading
from ..core.errors import ErrorCode

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
        # Pool de conexiones para hilos paralelos
        self._connection_pool = {}
        # Lock para acceso thread-safe al pool
        import threading
        self._pool_lock = threading.Lock()
        # Lock para conectar/reconectar de forma serializada
        self._connect_lock = threading.Lock()
        # Evitar correr migraciones/DDL en cada reconexión
        self._schema_initialized = False
        # Flag de depuración para controlar prints [DB DEBUG]
        self.debug_enabled = False

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
        
        # Cadena inicial sin database para crear la BD si no existe
        initial_conn_str = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={server};"
            "Encrypt=no;"          
            "TrustServerCertificate=yes;"  # Changed to yes for better compatibility
            "Connection Timeout=30;"       # Increased timeout
            "MARS_Connection=yes;"         # Enable Multiple Active Result Sets
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
                # Store connection parameters for potential reconnection
                self.server = server
                self.database = database
                self.user = user
                self.password = password
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
                except Exception as se:
                    self._log(f"Security schema check failed: {se}", "ERROR")
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
                    CONSTRAINT chk_perm_modulo CHECK (modulo IN (N'TRA', N'MBRP', N'STOCK', N'MENSAJES', N'ESTADISTICAS', N'CALENDARIO', N'ADMIN'))
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
                    CONSTRAINT chk_pal_um_modulo CHECK (modulo IN (N'TRA', N'MBRP', N'STOCK', N'MENSAJES', N'ESTADISTICAS', N'CALENDARIO', N'ADMIN'))
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
            ,(N'admin.auditoria', N'ADMIN', N'Ver logs de auditoría');

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
            VALUES (N'TRA'),(N'MBRP'),(N'STOCK'),(N'MENSAJES'),(N'ESTADISTICAS'),(N'CALENDARIO'),(N'ADMIN');

            INSERT INTO pal_usuarios_modulos (usuario_id, modulo, habilitado, asignado_por)
            SELECT @admin_user_id, m.modulo, 1, @admin_user_id
            FROM @mods m
            LEFT JOIN pal_usuarios_modulos um ON um.usuario_id = @admin_user_id AND um.modulo = m.modulo
            WHERE um.usuario_id IS NULL;
            """
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
        except Exception as e:
            raise
        
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
                    f"DRIVER={{SQL Server}};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    "Encrypt=no;"
                    "TrustServerCertificate=yes;"
                    "Connection Timeout=30;"
                    "MARS_Connection=yes;"  # Enable Multiple Active Result Sets
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
                            COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') as C_DESCRI
                        FROM MA_DEPOPROD d
                        INNER JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.C_CODIGO
                        WHERE d.c_coddeposito = ?
                        GROUP BY d.c_codarticulo, p.cu_descripcion_corta
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
                            ROW_NUMBER() OVER (ORDER BY stock_total ASC) as rn
                        FROM stock_summary
                    )
                    SELECT codigo, descripcion, stock, nivel
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
    
    def obtener_ventas_completas_tra(self, fecha_inicio, fecha_fin, sede_codigo, limit=None):
        """Obtiene ventas completas TRA con jerarquía para carga inicial
        
        Args:
            fecha_inicio: Fecha inicio del rango
            fecha_fin: Fecha fin del rango  
            sede_codigo: Código de sede/depósito
            limit: Límite de registros (para carga inicial)
            
        Returns:
            list: Lista de ventas con jerarquía incluida
        """
        try:
            query = """
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
                    END) AS neto
                FROM TR_INVENTARIO i
                LEFT JOIN MA_PRODUCTOS p ON i.c_Codarticulo = p.C_CODIGO
                WHERE i.f_fecha BETWEEN CONVERT(DATE, ?, 105) AND CONVERT(DATE, ?, 105)
                AND i.c_Concepto IN ('VEN', 'DEV')
                AND i.c_Deposito LIKE ?
                GROUP BY 
                    i.c_Codarticulo,
                    p.cu_descripcion_corta,
                    p.C_DESCRI,
                    p.C_DEPARTAMENTO,
                    p.C_GRUPO,
                    p.C_SUBGRUPO
                ORDER BY neto DESC
            """
            
            if limit:
                query = query.replace("ORDER BY neto DESC", f"ORDER BY neto DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY")
                
            fecha_inicio_str = fecha_inicio.strftime("%d-%m-%Y")
            fecha_fin_str = fecha_fin.strftime("%d-%m-%Y")
            
            return self.fetch_data(query, (fecha_inicio_str, fecha_fin_str, sede_codigo))
        except Exception as e:
            print(f"Error obteniendo ventas TRA completas: {str(e)}")
            return []
    
    def obtener_ventas_por_producto_chunk(self, fecha_inicio, fecha_fin, sede_codigo, 
                                         start_row=1, fetch_size=1000):
        """Obtiene ventas TRA en chunks para carga paralela - OPTIMIZADO (soporta consulta global ICH)
        
        Args:
            fecha_inicio: Fecha inicio del rango
            fecha_fin: Fecha fin del rango  
            sede_codigo: Código de sede/depósito
            start_row: Fila inicial (1-indexed)
            fetch_size: Cantidad de filas a obtener
            
        Returns:
            list: Lista de ventas en el chunk especificado
            
        Optimizaciones:
        - WITH (NOLOCK): Evita bloqueos de lectura (4x-10x más rápido)
        - Usa = en lugar de LIKE: Permite uso de índices
        - CTE pre-agregada: Reduce datos antes del JOIN costoso
        - Filtra neto > 0: Solo productos con ventas reales
        """
        try:
            # OPTIMIZACIÓN CRÍTICA: CTE + NOLOCK + filtro dinámico por depósito
            global_query = (sede_codigo in (None, '%', '00', 'ICH', 'ALL'))
            if global_query:
                query = """
                    WITH VentasAgregadas AS (
                        SELECT 
                            i.c_Codarticulo AS codigo,
                            SUM(CASE 
                                WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                                WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                                ELSE 0 
                            END) AS neto
                        FROM TR_INVENTARIO i WITH (NOLOCK)
                        WHERE i.f_fecha BETWEEN CONVERT(DATE, ?, 105) AND CONVERT(DATE, ?, 105)
                            AND i.c_Concepto IN ('VEN', 'DEV')
                        GROUP BY i.c_Codarticulo
                        HAVING SUM(CASE 
                            WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                            WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                            ELSE 0 
                        END) > 0
                    )
                    SELECT 
                        v.codigo,
                        COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') AS descripcion,
                        COALESCE(p.C_DEPARTAMENTO, '') AS departamento,
                        COALESCE(p.C_GRUPO, '') AS grupo,
                        COALESCE(p.C_SUBGRUPO, '') AS subgrupo,
                        v.neto,
                        COALESCE(p.n_precio1, 0) AS precio,
                        COALESCE(p.n_costoact, 0) AS costo
                    FROM VentasAgregadas v
                    LEFT JOIN MA_PRODUCTOS p WITH (NOLOCK) ON v.codigo = p.C_CODIGO
                    ORDER BY v.neto DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """
            else:
                query = """
                    WITH VentasAgregadas AS (
                        SELECT 
                            i.c_Codarticulo AS codigo,
                            SUM(CASE 
                                WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                                WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                                ELSE 0 
                            END) AS neto
                        FROM TR_INVENTARIO i WITH (NOLOCK)
                        WHERE i.f_fecha BETWEEN CONVERT(DATE, ?, 105) AND CONVERT(DATE, ?, 105)
                            AND i.c_Concepto IN ('VEN', 'DEV')
                            AND i.c_Deposito = ?
                        GROUP BY i.c_Codarticulo
                        HAVING SUM(CASE 
                            WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                            WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                            ELSE 0 
                        END) > 0
                    )
                    SELECT 
                    v.codigo,
                        COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') AS descripcion,
                        COALESCE(p.C_DEPARTAMENTO, '') AS departamento,
                        COALESCE(p.C_GRUPO, '') AS grupo,
                        COALESCE(p.C_SUBGRUPO, '') AS subgrupo,
                        v.neto,
                        COALESCE(p.n_precio1, 0) AS precio,
                        COALESCE(p.n_costoact, 0) AS costo
                    FROM VentasAgregadas v
                    LEFT JOIN MA_PRODUCTOS p WITH (NOLOCK) ON v.codigo = p.C_CODIGO
                    ORDER BY v.neto DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """
            
            fecha_inicio_str = fecha_inicio.strftime("%d-%m-%Y")
            fecha_fin_str = fecha_fin.strftime("%d-%m-%Y")
            offset = start_row - 1  # Convert to 0-indexed
            
            # Ejecutar usando conexión específica del hilo para evitar colisiones
            thread_conn = self.get_thread_connection("tra_chunk")
            if not thread_conn:
                return []
            cursor = thread_conn.cursor()
            if global_query:
                cursor.execute(query, (fecha_inicio_str, fecha_fin_str, offset, fetch_size))
            else:
                cursor.execute(query, (fecha_inicio_str, fecha_fin_str, sede_codigo, offset, fetch_size))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Error obteniendo chunk de ventas TRA: {str(e)}")
            return []
    
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
    
    def obtener_alertas_stock_chunk(self, start_row=1, fetch_size=500, deposito='0301'):
        """Obtiene alertas de stock en chunks para depósito específico
        
        Args:
            start_row: Fila inicial (1-indexed)
            fetch_size: Cantidad de filas a obtener
            deposito: Código de depósito/sede
            
        Returns:
            list: Lista de tuplas (codigo, descripcion, stock, nivel)
        """
        try:
            query = """
                SELECT 
                    c_codarticulo AS codigo,
                    MAX(COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN')) AS descripcion,
                    CAST(SUM(n_cantidad) AS INT) AS stock,  
                    CASE
                        WHEN SUM(n_cantidad) BETWEEN 15 AND 20 THEN 'Leve'  
                        WHEN SUM(n_cantidad) BETWEEN 8 AND 14 THEN 'Media'
                        ELSE 'Crítica'
                    END AS nivel
                FROM MA_DEPOPROD d
                    INNER JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.C_CODIGO
                    WHERE c_coddeposito = ?
                    GROUP BY c_codarticulo
                    HAVING SUM(n_cantidad) < 21  
                    ORDER BY CAST(SUM(n_cantidad) AS INT) ASC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """
            offset = start_row - 1  # Convert to 0-indexed
            return self.fetch_data(query, (deposito, offset, fetch_size))
        except Exception as e:
            print(f"Error obteniendo chunk de alertas stock: {str(e)}")
            return []
    
    def obtener_alertas_stock_multiples(self, start_row=1, fetch_size=500, depositos=['0301']):
        """Obtiene alertas de stock para múltiples depósitos
        
        Args:
            start_row: Fila inicial (1-indexed)
            fetch_size: Cantidad de filas a obtener
            depositos: Lista de códigos de depósito
            
        Returns:
            list: Lista de tuplas (codigo, descripcion, stock, nivel)
        """
        try:
            if not depositos:
                depositos = ['0301']
            
            placeholders = ','.join('?' for _ in depositos)
            query = f"""
                SELECT 
                    c_codarticulo AS codigo,
                    MAX(COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN')) AS descripcion,
                    CAST(SUM(n_cantidad) AS INT) AS stock,  
                    CASE
                        WHEN SUM(n_cantidad) BETWEEN 15 AND 20 THEN 'Leve'  
                        WHEN SUM(n_cantidad) BETWEEN 8 AND 14 THEN 'Media'
                        ELSE 'Crítica'
                    END AS nivel
                FROM MA_DEPOPROD d
                    INNER JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.C_CODIGO
                    WHERE c_coddeposito IN ({placeholders})
                    GROUP BY c_codarticulo
                    HAVING SUM(n_cantidad) < 21  
                    ORDER BY CAST(SUM(n_cantidad) AS INT) ASC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """
            offset = start_row - 1  # Convert to 0-indexed
            params = depositos + [offset, fetch_size]
            return self.fetch_data(query, params)
        except Exception as e:
            print(f"Error obteniendo alertas stock múltiples: {str(e)}")
            return []
