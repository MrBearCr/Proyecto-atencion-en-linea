"""
Dependencias compartidas para los endpoints de la API.
"""
from fastapi import HTTPException, Query
from typing import Dict, Any
from .db import get_auth_manager


def verify_token(token: str = Query(..., description="Token de autenticación")) -> Dict[str, Any]:
    """
    Dependencia para verificar el token de autenticación en los endpoints.
    """
    auth_manager = get_auth_manager()
    user_info = auth_manager.verificar_sesion(token)
    
    if not user_info:
        raise HTTPException(status_code=401, detail="Token inválido o sesión expirada")
    
    return user_info

