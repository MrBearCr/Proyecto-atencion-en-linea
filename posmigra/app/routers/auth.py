from fastapi import APIRouter, HTTPException, Depends, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import secrets
from datetime import datetime, timedelta

from app.database import get_db
from app.crud import (
    get_user_by_username, 
    get_active_session_by_token, 
    invalidate_session_token,
    log_audit_access
)
from app.utils import check_password
from app.models import LoginRequestAPI, LoginResponseAPI, UserDB, SessionDB

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequestAPI, db: Session = Depends(get_db)):
    """
    Inicia sesión de usuario.
    Verifica credenciales, genera un token de sesión y lo guarda en la base de datos.
    """
    user = get_user_by_username(db, login_data.username)
    
    # Simple check for demo/migration. In real app, check for 'activo' and lockout.
    if not user or not user.activo:
        log_audit_access(db, "LOGIN_FAIL", "AUTH", f"User {login_data.username} not found or inactive", login_data.ip_address, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o usuario inactivo."
        )

    if not check_password(login_data.password, user.password_hash):
        log_audit_access(db, "LOGIN_FAIL", "AUTH", f"Invalid password for {login_data.username}", login_data.ip_address, False, user.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas."
        )

    # Generate token
    token = secrets.token_urlsafe(32)
    
    # Create session in DB
    # We should have a CRUD function for this, but for now we can do it here or assume it's in crud.
    # Let's check crud.py for session creation.
    
    # Assuming crud.py has a way to create session, or we do it directly.
    # Looking at the previous read of crud.py, I don't see create_session.
    
    expires_at = datetime.utcnow() + timedelta(hours=8)
    new_session = SessionDB(
        usuario_id=user.id,
        token=token,
        fecha_inicio=datetime.utcnow(),
        fecha_expiracion=expires_at,
        activa=True,
        ip_address=login_data.ip_address
    )
    db.add(new_session)
    
    # Update last access
    user.fecha_ultimo_acceso = datetime.utcnow()
    user.intentos_fallidos = 0
    db.add(user)
    
    try:
        db.commit()
        log_audit_access(db, "LOGIN_SUCCESS", "AUTH", "Inicio de sesión exitoso", login_data.ip_address, True, user.id)
        return TokenResponse(access_token=token)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear sesión: {e}")

@router.get("/me")
async def get_me(request: Request, db: Session = Depends(get_db)):
    """
    Obtiene la información del usuario actual a partir del token de sesión.
    """
    # Use the same logic as get_current_user dependency in main.py
    # But here we do it directly for the endpoint
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
         raise HTTPException(status_code=401, detail="No autenticado")
    
    token = auth_header.split(" ")[1]
    session_db = get_active_session_by_token(db, token)
    
    if not session_db:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    
    user = db.query(UserDB).filter(UserDB.id == session_db.usuario_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    return {
        "id": user.id,
        "username": user.username,
        "nombre_completo": user.nombre_completo,
        "email": user.email,
        # Potentially roles and permissions
    }

@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        invalidate_session_token(db, token)
    return {"message": "Sesión cerrada"}
