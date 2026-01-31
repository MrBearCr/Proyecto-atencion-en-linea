from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
import configparser
import os
import sys
import logging
from sqlalchemy import text

# Importar SecureCredentialsManager para encriptar
try:
    from pal.core.credentials import SecureCredentialsManager
except ImportError:
    # Fallback o manejo de error si no se encuentra
    SecureCredentialsManager = None

from app.database import init_db_connection, get_db_status

router = APIRouter(
    prefix="/config",
    tags=["Configuration"]
)

logger = logging.getLogger(__name__)

class DatabaseConfigSchema(BaseModel):
    server: str = Field(..., description="Dirección IP o Host del servidor SQL")
    database: str = Field(..., description="Nombre de la base de datos")
    user: str = Field(None, description="Usuario SQL (dejar vacío para Autenticación de Windows)")
    password: str = Field(None, description="Contraseña SQL")

@router.get("/status")
async def check_db_status():
    """Verifica si la base de datos está configurada y conectada."""
    is_connected, error_msg = get_db_status()
    return {
        "configured": is_connected,
        "message": "Conectado correctamente" if is_connected else error_msg
    }

@router.post("/setup", status_code=status.HTTP_201_CREATED)
async def setup_database(config_data: DatabaseConfigSchema):
    """
    Recibe los datos de conexión, encripta la contraseña, guarda el db_config.ini
    y reinicia la conexión a la base de datos.
    """
    
    # 1. Preparar el parser de configuración
    config = configparser.ConfigParser()
    
    # Ruta al archivo db_config.ini (en la raíz del proyecto, dos niveles arriba de app/)
    # Ajustar según la estructura: posmigra/app/routers -> posmigra/app -> posmigra -> ROOT
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    config_path = os.path.join(root_dir, 'db_config.ini')

    # 2. Manejo de encriptación
    password_to_store = config_data.password or ""
    
    if config_data.user and password_to_store:
        if SecureCredentialsManager:
            try:
                cred_manager = SecureCredentialsManager()
                # Encriptamos la contraseña antes de guardarla
                password_to_store = cred_manager.encrypt(password_to_store)
            except Exception as e:
                logger.error(f"Error encriptando contraseña: {e}")
                raise HTTPException(status_code=500, detail="Error de seguridad al encriptar credenciales.")
        else:
            logger.warning("SecureCredentialsManager no disponible. Guardando en texto plano (NO RECOMENDADO).")

    # 3. Escribir en el objeto config
    config['Database'] = {
        'server': config_data.server,
        'database': config_data.database,
        'user': config_data.user or "",
        'password': password_to_store
    }

    # 4. Guardar archivo físico
    try:
        with open(config_path, 'w') as configfile:
            config.write(configfile)
    except Exception as e:
        logger.error(f"No se pudo escribir db_config.ini: {e}")
        raise HTTPException(status_code=500, detail="Error al guardar el archivo de configuración.")

    # 5. Intentar reconectar el backend
    try:
        success = init_db_connection()
        if not success:
            raise ValueError("La conexión falló con los nuevos parámetros.")
    except Exception as e:
        # Si falla, podríamos querer borrar el archivo o dejarlo para que el usuario corrija
        logger.error(f"Error al conectar con la nueva configuración: {e}")
        raise HTTPException(status_code=400, detail=f"Configuración guardada, pero la conexión falló: {str(e)}")

    return {"message": "Configuración guardada y conexión establecida exitosamente."}
