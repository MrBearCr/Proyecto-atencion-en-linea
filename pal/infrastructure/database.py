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
        # Pool de conexiones para hilos paralelos
        self._connection_pool = {}

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
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                # Verificar conexión
                if not self.conn:
                    print(f"[DB DEBUG] Reconectando en obtener_alertas_stock (intento {attempt + 1})...")
                    self.connect(self.server, self.database, self.user, self.password)
                    if not self.conn:
                        continue
                
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
                    query += f" OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
            
                # Usar cursor fresco para evitar errores de secuencia
                cursor = self.conn.cursor()
                cursor.execute(query)
                result = cursor.fetchall()
                cursor.close()
                
                print(f"[DB DEBUG] obtener_alertas_stock exitoso: {len(result)} registros (limit: {limit})")
                return result
                
            except Exception as e:
                error_msg = str(e)
                print(f"[DB DEBUG] Error en obtener_alertas_stock (intento {attempt + 1}): {error_msg}")
                
                # Manejar errores ODBC
                if "HY010" in error_msg or "HY000" in error_msg:
                    # Resetear conexión
                    try:
                        if hasattr(self, 'cursor') and self.cursor:
                            self.cursor.close()
                        if self.conn:
                            self.conn.close()
                        self.conn = None
                        self.cursor = None
                    except:
                        pass
                    
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                
                return []  # Return empty on final failure
        
        print(f"[DB DEBUG] obtener_alertas_stock fallido después de {max_retries} intentos")
        return []
    
    def get_thread_connection(self, thread_name="default"):
        """Obtiene una conexión independiente para un hilo específico"""
        import threading
        
        current_thread = threading.current_thread().name
        thread_key = f"{thread_name}_{current_thread}"
        
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
            )
            
            if self.user:
                conn_str += f"UID={self.user};PWD={self.password or ''};"
            else:
                conn_str += "Trusted_Connection=yes;"
            
            new_conn = pyodbc.connect(conn_str)
            self._connection_pool[thread_key] = new_conn
            
            print(f"[DB DEBUG] Nueva conexión creada para hilo: {thread_key}")
            return new_conn
            
        except Exception as e:
            print(f"[DB DEBUG] Error creando conexión para hilo {thread_key}: {e}")
            return None
    
    def close_thread_connections(self):
        """Cierra todas las conexiones del pool de hilos"""
        for thread_key, conn in list(self._connection_pool.items()):
            try:
                conn.close()
                print(f"[DB DEBUG] Conexión cerrada: {thread_key}")
            except:
                pass
        self._connection_pool.clear()
        
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
    
    def obtener_alertas_stock_chunk(self, start_row=1, fetch_size=500, deposito='0301'):
        """Obtiene alertas de stock en chunks para carga paralela con manejo robusto de errores ODBC
        
        Args:
            start_row: Fila inicial (1-indexed)
            fetch_size: Cantidad de filas a obtener
            deposito: Código de depósito
            
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
                    print(f"[DB DEBUG] No se pudo obtener conexión para hilo en intento {attempt + 1}")
                    continue
                
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
                        WHERE c_coddeposito = ?
                        GROUP BY c_codarticulo
                        HAVING SUM(n_cantidad) < 21  
                        ORDER BY stock ASC
                        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                    """
                
                offset = start_row - 1  # Convert to 0-indexed
                
                # Usar conexión fresca para evitar errores de secuencia
                cursor = self.conn.cursor()
                cursor.execute(query, (deposito, offset, fetch_size))
                result = cursor.fetchall()
                cursor.close()
                
                # Debug logging solo en primer intento exitoso
                if attempt == 0:
                    query_time = time.perf_counter() - query_start
                    print(f"[DB DEBUG] Chunk query: offset={offset}, fetch_size={fetch_size}, deposito={deposito}")
                    print(f"[DB DEBUG] Returned {len(result)} rows in {query_time:.3f}s")
                    
                    if result and len(result) > 0:
                        first_stock = result[0][2] if len(result[0]) > 2 else "N/A"
                        last_stock = result[-1][2] if len(result[-1]) > 2 else "N/A"
                        print(f"[DB DEBUG] Stock range: {first_stock} to {last_stock}")
                
                return result
                
            except Exception as e:
                query_time = time.perf_counter() - query_start
                error_msg = str(e)
                
                # Manejar errores ODBC específicos
                if "HY010" in error_msg or "HY000" in error_msg:
                    print(f"[DB DEBUG] Error ODBC en intento {attempt + 1}: {error_msg}")
                    
                    # Cerrar y recrear conexión para errores de secuencia
                    try:
                        if hasattr(self, 'cursor') and self.cursor:
                            self.cursor.close()
                        if self.conn:
                            self.conn.close()
                        self.conn = None
                        self.cursor = None
                    except:
                        pass
                    
                    # Esperar antes de reintentar
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    # Error no recuperable
                    print(f"[DB DEBUG] Error no recuperable (tiempo: {query_time:.3f}s): {error_msg}")
                    return []
        
        # Si llegamos aquí, todos los intentos fallaron
        print(f"[DB DEBUG] Chunk fallido después de {max_retries} intentos")
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
                    COALESCE(p.C_DESCRI, 'SIN DESCRIPCIÓN') AS descripcion,
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
        """Obtiene ventas TRA en chunks para carga paralela
        
        Args:
            fecha_inicio: Fecha inicio del rango
            fecha_fin: Fecha fin del rango  
            sede_codigo: Código de sede/depósito
            start_row: Fila inicial (1-indexed)
            fetch_size: Cantidad de filas a obtener
            
        Returns:
            list: Lista de ventas en el chunk especificado
        """
        try:
            query = """
                SELECT 
                    i.c_Codarticulo AS codigo,
                    COALESCE(p.C_DESCRI, 'SIN DESCRIPCIÓN') AS descripcion,
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
                    p.C_DESCRI,
                    p.C_DEPARTAMENTO,
                    p.C_GRUPO,
                    p.C_SUBGRUPO
                ORDER BY neto DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """
            
            fecha_inicio_str = fecha_inicio.strftime("%d-%m-%Y")
            fecha_fin_str = fecha_fin.strftime("%d-%m-%Y")
            offset = start_row - 1  # Convert to 0-indexed
            
            return self.fetch_data(query, (fecha_inicio_str, fecha_fin_str, sede_codigo, offset, fetch_size))
        except Exception as e:
            print(f"Error obteniendo chunk de ventas TRA: {str(e)}")
            return []
