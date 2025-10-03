"""
Módulo de códigos de error para la aplicación PAL
"""
from enum import Enum

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
