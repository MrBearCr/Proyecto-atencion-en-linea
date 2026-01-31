from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import configparser
import os
import sys
import logging
from urllib.parse import quote_plus

# Logging setup
logger = logging.getLogger(__name__)

# Ensure 'pal' package can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from pal.core.credentials import SecureCredentialsManager
except ImportError:
    logger.warning("Could not import SecureCredentialsManager. Passwords will be treated as plain text if logic permits.")
    SecureCredentialsManager = None

# Global variables for the database connection
engine = None
SessionLocal = None
Base = declarative_base()

# State variable to track connection status
_db_connected = False
_last_error = "Not initialized"

def get_db_status():
    """Returns a tuple (bool, str) indicating connection status and last error."""
    return _db_connected, _last_error

def init_db_connection():
    """
    Reads db_config.ini, sets up the engine and SessionLocal.
    Returns True if successful, False otherwise.
    """
    global engine, SessionLocal, _db_connected, _last_error

    # Locate db_config.ini (Root of the project)
    # Adjust path logic: posmigra/app/database.py -> posmigra/app -> posmigra -> ROOT
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_config_path = os.path.join(root_dir, 'db_config.ini')

    if not os.path.exists(db_config_path):
        _last_error = "Archivo db_config.ini no encontrado."
        logger.warning(_last_error)
        return False

    config = configparser.ConfigParser()
    try:
        config.read(db_config_path)
    except Exception as e:
        _last_error = f"Error leyendo db_config.ini: {e}"
        logger.error(_last_error)
        return False

    server = config.get("Database", "server", fallback="")
    database = config.get("Database", "database", fallback="")
    user = config.get("Database", "user", fallback="")
    password_stored = config.get("Database", "password", fallback="")

    if not server or not database:
        _last_error = "Configuración incompleta (falta server o database)."
        logger.warning(_last_error)
        return False

    # Password Decryption Logic
    password = password_stored
    if user and password_stored and SecureCredentialsManager:
        try:
            creds_manager = SecureCredentialsManager()
            password = creds_manager.decrypt(password_stored)
        except Exception as e:
            logger.warning(f"Fallo al desencriptar contraseña (posible texto plano o llave inválida): {e}")
            # Fallback: assume it might be plain text if decryption fails (or let connection fail)
            password = password_stored

    # Construct Connection String
    driver = "ODBC Driver 17 for SQL Server"
    connection_string = ""
    
    try:
        if user:
            # SQL Auth
            pwd_encoded = quote_plus(password)
            connection_string = f"mssql+pyodbc://{user}:{pwd_encoded}@{server}/{database}?driver={driver}&TrustServerCertificate=yes&Encrypt=no"
        else:
            # Windows Auth
            connection_string = f"mssql+pyodbc://{server}/{database}?driver={driver}&trusted_connection=yes&TrustServerCertificate=yes&Encrypt=no"

        # Initialize Engine
        # pool_pre_ping=True helps handle dropped connections gracefully
        new_engine = create_engine(connection_string, pool_size=10, max_overflow=20, pool_pre_ping=True)
        
        # Test Connection
        with new_engine.connect() as conn:
            pass # Just checking if we can connect
        
        # If successful, assign globals
        engine = new_engine
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        _db_connected = True
        _last_error = None
        logger.info(f"Conexión exitosa a la base de datos: {server}/{database}")
        return True

    except Exception as e:
        _db_connected = False
        _last_error = f"Error al conectar con la BD: {e}"
        logger.error(_last_error)
        return False

def seed_initial_data():
    """Seeds initial data (admin user, roles, permissions) if not present."""
    from app.models import UserDB, RoleDB, PermissionDB
    from app.utils import hash_password
    
    db = SessionLocal()
    try:
        # 1. Create essential permissions if they don't exist
        essential_perms = [
            ("USER_MANAGEMENT_READ", "AUTH", "Ver usuarios"),
            ("USER_MANAGEMENT_CREATE", "AUTH", "Crear usuarios"),
            ("USER_MANAGEMENT_UPDATE", "AUTH", "Actualizar usuarios"),
            ("USER_MANAGEMENT_DELETE", "AUTH", "Eliminar usuarios"),
            ("ROLE_MANAGEMENT_READ", "AUTH", "Ver roles"),
            ("ROLE_MANAGEMENT_CREATE", "AUTH", "Crear roles"),
            ("STOCK_ALERTS_READ", "STOCK", "Ver alertas de stock"),
            ("TRA_SALES_READ", "TRA", "Ver ventas TRA"),
            ("MBRP_REPORT_READ", "MBRP", "Ver reportes MBRP"),
        ]
        
        for code, mod, desc in essential_perms:
            if not db.query(PermissionDB).filter(PermissionDB.codigo == code).first():
                db.add(PermissionDB(codigo=code, modulo=mod, descripcion=desc))
        db.commit()

        # 2. Create Admin Role
        admin_role = db.query(RoleDB).filter(RoleDB.nombre == "Administrador").first()
        if not admin_role:
            admin_role = RoleDB(nombre="Administrador", descripcion="Acceso total", es_sistema=True)
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
            
            # Assign all permissions to admin role
            all_perms = db.query(PermissionDB).all()
            for p in all_perms:
                from app.models import RolePermissionDB
                db.add(RolePermissionDB(rol_id=admin_role.id, permiso_id=p.id))
            db.commit()

        # 3. Create Default Admin User (password: 123)
        if not db.query(UserDB).filter(UserDB.username == "admin").first():
            hashed_pwd = hash_password("123")
            admin_user = UserDB(
                username="admin",
                password_hash=hashed_pwd,
                nombre_completo="Administrador del Sistema",
                email="admin@casapro.com",
                activo=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            # Assign admin role
            from app.models import UserRoleDB
            db.add(UserRoleDB(usuario_id=admin_user.id, rol_id=admin_role.id))
            db.commit()
            
        logger.info("Datos iniciales verificados/sembrados.")
    except Exception as e:
        logger.error(f"Error seeding initial data: {e}")
        db.rollback()
    finally:
        db.close()

# Dependency to get DB session
def get_db():
    if SessionLocal is None:
        # Try to initialize if not done yet
        if not init_db_connection():
             # Yield None or raise error? 
             # Raising error is better so endpoints fail fast if no DB
             # However, for the config endpoint, we don't need this dependency.
             from fastapi import HTTPException
             raise HTTPException(status_code=503, detail="Base de datos no configurada o inaccesible.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Placeholder for database schema creation (if needed, though the original app seems to handle it)
# The original app has a create_table method in infrastructure/database.py.
# For FastAPI, this might be handled via Alembic migrations or a separate setup script.
# For now, we'll assume the database and tables are pre-existing or managed externally.

