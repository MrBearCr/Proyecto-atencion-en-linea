"""
AuthManager: autenticación y gestión de sesiones para PAL
"""
from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import os
import bcrypt
import secrets

from ..infrastructure.database import DatabaseManager

class AuthManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.max_intentos = 5
        self.tiempo_bloqueo_min = 15  # minutos
        self.duracion_sesion_min = 480  # 8 horas

    # Utilidades
    def _now(self) -> datetime:
        return datetime.utcnow()

    def _to_dt(self, value) -> datetime | None:
        """Convierte valores de fecha/hora provenientes de SQL Server a datetime seguro."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            s = str(value).replace('Z', '')
            # Quitar fracciones si no son parseables
            try:
                return datetime.fromisoformat(s)
            except Exception:
                if '.' in s:
                    s = s.split('.')[0]
                return datetime.fromisoformat(s)
        except Exception:
            return None

    def _hash(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def _check(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    # Sesiones
    def _crear_sesion(self, usuario_id: int, ip_address: Optional[str]) -> str:
        token = secrets.token_urlsafe(48)
        fecha_inicio = self._now()
        fecha_exp = fecha_inicio + timedelta(minutes=self.duracion_sesion_min)
        self.db.execute_query(
            """
            INSERT INTO pal_sesiones (usuario_id, token, ip_address, fecha_inicio, fecha_expiracion, activa)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (usuario_id, token, ip_address or None, fecha_inicio, fecha_exp)
        )
        return token

    def _cerrar_sesion_token(self, token: str) -> None:
        self.db.execute_query(
            "UPDATE pal_sesiones SET activa = 0 WHERE token = ?",
            (token,)
        )

    # API pública
    def login(self, username: str, password: str, ip_address: str | None = None) -> Dict[str, Any]:
        # Obtener usuario
        rows = self.db.fetch_data(
            "SELECT id, password_hash, activo, intentos_fallidos, bloqueado_hasta FROM pal_usuarios WHERE username = ?",
            (username,)
        )
        if not rows:
            return {"success": False, "message": "Usuario o contraseña inválidos"}

        user_id, pwd_hash, activo, intentos, bloqueado_hasta = rows[0]
        ahora = self._now()

        # Validaciones de estado
        if not activo:
            return {"success": False, "message": "Usuario inactivo"}
        bh = self._to_dt(bloqueado_hasta)
        if bh and ahora < bh:
            return {"success": False, "message": "Usuario bloqueado temporalmente"}

        # Validar password
        if not pwd_hash or not self._check(password, str(pwd_hash)):
            # Aumentar intentos
            nuevos_intentos = int(intentos or 0) + 1
            bloqueado = None
            if nuevos_intentos >= self.max_intentos:
                bloqueado = ahora + timedelta(minutes=self.tiempo_bloqueo_min)
                nuevos_intentos = 0
            self.db.execute_query(
                "UPDATE pal_usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE id = ?",
                (nuevos_intentos, bloqueado, user_id)
            )
            return {"success": False, "message": "Usuario o contraseña inválidos"}

        # Resetear intentos fallidos y actualizar último acceso
        self.db.execute_query(
            "UPDATE pal_usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL, fecha_ultimo_acceso = ? WHERE id = ?",
            (ahora, user_id)
        )

        # Crear sesión
        token = self._crear_sesion(user_id, ip_address)
        return {
            "success": True,
            "token": token,
            "user": {"id": user_id, "username": username},
            "message": "Login exitoso"
        }

    def logout(self, token: str) -> None:
        self._cerrar_sesion_token(token)

    def verificar_sesion(self, token: str) -> Optional[Dict[str, Any]]:
        rows = self.db.fetch_data(
            """
            SELECT s.usuario_id, u.username, s.fecha_expiracion, s.activa
            FROM pal_sesiones s
            JOIN pal_usuarios u ON u.id = s.usuario_id
            WHERE s.token = ?
            """,
            (token,)
        )
        if not rows:
            return None
        usuario_id, username, fecha_exp, activa = rows[0]
        if not activa:
            return None
        fe = self._to_dt(fecha_exp)
        if fe and self._now() > fe:
            # Expirar automáticamente
            self._cerrar_sesion_token(token)
            return None
        return {"id": usuario_id, "username": username}

    def cambiar_password(self, usuario_id: int, password_actual: str, password_nuevo: str) -> bool:
        rows = self.db.fetch_data(
            "SELECT password_hash FROM pal_usuarios WHERE id = ?",
            (usuario_id,)
        )
        if not rows:
            return False
        pwd_hash = rows[0][0]
        if not self._check(password_actual, str(pwd_hash)):
            return False
        nuevo_hash = self._hash(password_nuevo)
        return self.db.execute_query(
            "UPDATE pal_usuarios SET password_hash = ? WHERE id = ?",
            (nuevo_hash, usuario_id)
        )

    def resetear_password(self, usuario_id: int, password_temporal: str) -> str:
        temp_hash = self._hash(password_temporal)
        self.db.execute_query(
            "UPDATE pal_usuarios SET password_hash = ? WHERE id = ?",
            (temp_hash, usuario_id)
        )
        return password_temporal
