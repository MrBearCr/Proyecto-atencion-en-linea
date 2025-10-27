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
                codigo_producto NVARCHAR(15) NULL
            );
            
            -- Agregar columna codigo_producto si la tabla existe pero no tiene la columna
            IF EXISTS (SELECT * FROM sys.tables WHERE name = 'envios_programados' AND type = 'U')
            AND NOT EXISTS (
                SELECT * FROM sys.columns 
                WHERE object_id = OBJECT_ID('envios_programados') 
                AND name = 'codigo_producto'
            )
            BEGIN
                ALTER TABLE envios_programados ADD codigo_producto NVARCHAR(15) NULL;
            END

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
            AND EXISTS (
                SELECT * FROM sys.columns 
                WHERE object_id = OBJECT_ID('envios_programados') 
                AND name = 'codigo_producto'
            )
            CREATE INDEX idx_envios_producto 
            ON envios_programados (codigo_producto);
        """)
            self.conn.commit()

        except pyodbc.Error as e:
            error_msg = f"{ErrorCode.DB_TABLE_CREATION}: {str(e)}"
            raise Exception(error_msg) from e
        
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
                        HAVING SUM(n_cantidad) < 21  
                        ORDER BY stock ASC
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
        cursor = None
        try:
            # Ensure connection is valid
            if not self.ensure_connection():
                raise Exception("Unable to establish database connection")
            
            # Create new cursor for this operation
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return True
        except pyodbc.Error as e:
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            error_msg = f"{ErrorCode.DB_QUERY_EXECUTION}: {str(e)}"
            raise Exception(error_msg) from e
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
        """Executes a SELECT query with improved error handling and connection validation"""
        max_retries = 3
        
        for attempt in range(max_retries):
            cursor = None
            try:
                # Ensure we have a valid connection
                if not self.ensure_connection():
                    if attempt == max_retries - 1:
                        raise Exception("Unable to establish database connection")
                    time.sleep(2)
                    continue
                
                # Create a new cursor for this query to avoid state conflicts
                cursor = self.conn.cursor()
                cursor.execute(query, params or ())
                result = cursor.fetchall()
                
                # Log successful execution in debug mode
                if getattr(self, 'debug_enabled', False):
                    self._log(f"[DB DEBUG] Query executed successfully: {len(result) if result else 0} rows returned", "DEBUG")
                
                return result
                
            except pyodbc.Error as e:
                error_code = getattr(e, 'args', [''])[0] if hasattr(e, 'args') else str(e)
                error_msg = str(e)
                
                # Handle specific ODBC errors
                if error_code in ['HY000', 'HY010', '08S01', '08003', '07005']:
                    # Connection-related errors - try to reconnect
                    if getattr(self, 'debug_enabled', False):
                        self._log(f"[DB DEBUG] Connection error detected on attempt {attempt + 1}: {error_code}", "DEBUG")
                    
                    # Force reconnection
                    if cursor:
                        try:
                            cursor.close()
                        except:
                            pass
                    self.conn = None
                    self.cursor = None
                    
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                
                # Log the error details
                detailed_error = f"""
            Error en consulta SQL:
            Query: {query}
            Params: {params}
            Error Code: {error_code}
            Error: {error_msg}
            Attempt: {attempt + 1}/{max_retries}
            """
                self._log(detailed_error, "ERROR")
                
                # If this is the last attempt, raise the exception
                if attempt == max_retries - 1:
                    raise Exception(f"Database query failed after {max_retries} attempts: {error_msg}")
                    
            except Exception as e:
                # Handle non-ODBC exceptions
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
                # Always close cursor after use
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
        
        # Should not reach here, but just in case
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
                            p.C_DESCRI
                        FROM MA_DEPOPROD d
                        INNER JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.C_CODIGO
                        WHERE d.c_coddeposito = ?
                        GROUP BY d.c_codarticulo, p.C_DESCRI
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
                    COALESCE(p.cu_descripcion_corta, p.C_DESCRI, 'SIN DESCRIPCIÓN') AS descripcion,
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
        """Obtiene ventas TRA en chunks para carga paralela - OPTIMIZADO
        
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
            # OPTIMIZACIÓN CRÍTICA: CTE + NOLOCK + = en lugar de LIKE
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
                    COALESCE(p.cu_descripcion_corta, p.C_DESCRI, 'SIN DESCRIPCIÓN') AS descripcion,
                    COALESCE(p.C_DEPARTAMENTO, '') AS departamento,
                    COALESCE(p.C_GRUPO, '') AS grupo,
                    COALESCE(p.C_SUBGRUPO, '') AS subgrupo,
                    v.neto
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
            cursor.execute(query, (fecha_inicio_str, fecha_fin_str, sede_codigo, offset, fetch_size))
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"Error obteniendo chunk de ventas TRA: {str(e)}")
            return []
