"""
Módulo de códigos de error para la aplicación PAL
"""
from enum import Enum
import traceback
import sys
from typing import Optional, Dict, Any

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


class PalError(Exception):
    """
    Excepción base para la aplicación PAL.
    Permite encapsular un ErrorCode corporativo junto con detalles técnicos,
    la excepción original que lo causó y el contexto en el que ocurrió,
    facilitando un debug exacto de lo que está ocurriendo en el sistema.
    """
    def __init__(
        self, 
        error_code: ErrorCode, 
        message: str = "", 
        original_exception: Optional[Exception] = None, 
        context: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.custom_message = message
        self.original_exception = original_exception
        self.context = context or {}
        
        # Guardar el traceback en el momento de creación para no perderlo
        self._tb = traceback.format_exc() if sys.exc_info()[0] is not None else ""
        
        # Construir el mensaje detallado de la excepción
        detail = f"[{self.error_code.code}] {self.error_code.description}"
        if self.custom_message:
            detail += f" - {self.custom_message}"
        if self.original_exception:
            detail += f"\n  ↳ Causa: {type(self.original_exception).__name__}: {str(self.original_exception)}"
        if self.context:
            detail += f"\n  ↳ Contexto: {self.context}"
            
        super().__init__(detail)
        
    def get_full_traceback(self) -> str:
        """
        Devuelve un texto formateado con el traceback exacto de este error
        y de la excepción original si fue capturada, ideal para logs de auditoría o archivos de debug.
        """
        lines = []
        lines.append(f"--- DETALLES DEL ERROR: {self.error_code.name} ---")
        lines.append(str(self))
        
        if self._tb and self._tb.strip() != "NoneType: None":
            lines.append("\n--- TRACEBACK DE LA CAPTURA ---")
            lines.append(self._tb)
            
        if self.original_exception:
            lines.append("\n--- EXCEPCIÓN ORIGINAL ---")
            orig_tb = "".join(traceback.format_exception(
                type(self.original_exception), 
                self.original_exception, 
                self.original_exception.__traceback__
            ))
            lines.append(orig_tb)
            
        return "\n".join(lines)
