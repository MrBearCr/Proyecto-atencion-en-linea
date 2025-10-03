"""
Gestor de base de datos para la aplicación PAL
"""
import pyodbc
import configparser
import time
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
            initial_conn_str += "Trusted_Connection=no;"

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
        
    def obtener_alertas_stock(self, limit=None):
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
        
            if limit:
                query = query.replace("ORDER BY stock ASC", f"ORDER BY stock ASC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY")
        
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