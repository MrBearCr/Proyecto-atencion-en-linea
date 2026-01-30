"""
Módulo de inicialización de base de datos para posmigra.
Reutiliza DatabaseManager y AuthManager de pal/ para mantener la misma lógica.
"""
import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al path para importar pal/
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pal.infrastructure.database import DatabaseManager
from pal.core.auth import AuthManager
from pal.core.credentials import SecureCredentialsManager

# Instancias globales (singleton pattern)
_db_manager = None
_auth_manager = None
_credentials_manager = None


def get_credentials_manager() -> SecureCredentialsManager:
    """Obtiene o crea el gestor de credenciales."""
    global _credentials_manager
    if _credentials_manager is None:
        _credentials_manager = SecureCredentialsManager()
    return _credentials_manager


def get_db_manager() -> DatabaseManager:
    """Obtiene o crea el gestor de base de datos."""
    global _db_manager
    if _db_manager is None:
        cred_manager = get_credentials_manager()
        _db_manager = DatabaseManager(cred_manager)
    return _db_manager


def get_auth_manager() -> AuthManager:
    """Obtiene o crea el gestor de autenticación."""
    global _auth_manager
    if _auth_manager is None:
        db_manager = get_db_manager()
        _auth_manager = AuthManager(db_manager)
    return _auth_manager


def ensure_db_connected():
    """
    Asegura que la base de datos esté conectada.
    Lee la configuración desde db_config.ini usando SecureCredentialsManager.
    """
    db_manager = get_db_manager()
    
    # Si ya está conectado, no hacer nada
    if db_manager.conn is not None:
        try:
            # Verificar que la conexión sigue activa
            db_manager.cursor.execute("SELECT 1")
            return True
        except Exception:
            # La conexión se perdió, reconectar
            pass
    
    # Obtener credenciales desde SecureCredentialsManager
    cred_manager = get_credentials_manager()
    
    try:
        # Leer configuración desde db_config.ini
        config_path = PROJECT_ROOT / "db_config.ini"
        if not config_path.exists():
            raise Exception("db_config.ini no encontrado")
        
        import configparser
        config = configparser.ConfigParser()
        config.read(config_path)
        
        # Obtener valores encriptados y desencriptarlos
        server_enc = config.get("Database", "server", fallback="")
        database_enc = config.get("Database", "database", fallback="")
        user_enc = config.get("Database", "user", fallback="")
        
        server = cred_manager.decrypt(server_enc) if server_enc else ""
        database = cred_manager.decrypt(database_enc) if database_enc else ""
        user = cred_manager.decrypt(user_enc) if user_enc else ""
        password = ""  # Windows Auth si user está vacío
        
        # Conectar
        success = db_manager.connect(server, database, user, password)
        if not success:
            raise Exception("No se pudo conectar a la base de datos")
        
        return True
    except Exception as e:
        print(f"[POSMIGRA][DB] Error conectando: {e}")
        return False

