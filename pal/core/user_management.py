"""
UserManager y RoleManager para gestión de usuarios/roles PAL
"""
from __future__ import annotations
from typing import Optional, Dict, List, Any
from datetime import datetime
import bcrypt

from ..infrastructure.database import DatabaseManager

class UserManager:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def crear_usuario(self, username: str, password: str, nombre_completo: str,
                      email: str | None = None, roles: List[int] | None = None) -> int:
        pwd_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
        self.db.execute_query(
            """
            INSERT INTO pal_usuarios (username, password_hash, nombre_completo, email, activo)
            VALUES (?, ?, ?, ?, 1)
            """,
            (username, pwd_hash, nombre_completo, email)
        )
        row = self.db.fetch_data("SELECT id FROM pal_usuarios WHERE username = ?", (username,))
        user_id = int(row[0][0]) if row else 0
        if roles:
            for rol_id in roles:
                self.db.execute_query(
                    "IF NOT EXISTS (SELECT 1 FROM pal_usuarios_roles WHERE usuario_id = ? AND rol_id = ?)\n"
                    "INSERT INTO pal_usuarios_roles (usuario_id, rol_id) VALUES (?, ?)\n",
                    (user_id, rol_id, user_id, rol_id)
                )
        return user_id

    def actualizar_usuario(self, usuario_id: int, **kwargs):
        campos = []
        params: List[Any] = []
        for k in ("username", "nombre_completo", "email", "activo"):
            if k in kwargs:
                campos.append(f"{k} = ?")
                params.append(kwargs[k])
        if not campos:
            return False
        params.append(usuario_id)
        return self.db.execute_query(
            f"UPDATE pal_usuarios SET {', '.join(campos)} WHERE id = ?",
            tuple(params)
        )

    def desactivar_usuario(self, usuario_id: int):
        return self.db.execute_query(
            "UPDATE pal_usuarios SET activo = 0 WHERE id = ?",
            (usuario_id,)
        )

    def listar_usuarios(self, activos_solo: bool = True) -> List[Dict[str, Any]]:
        query = "SELECT id, username, nombre_completo, email, activo FROM pal_usuarios"
        if activos_solo:
            query += " WHERE activo = 1"
        rows = self.db.fetch_data(query)
        return [
            {
                "id": int(r[0]),
                "username": str(r[1]),
                "nombre_completo": str(r[2]),
                "email": str(r[3]) if r[3] is not None else None,
                "activo": bool(r[4])
            }
            for r in (rows or [])
        ]

    def obtener_usuario(self, usuario_id: int) -> Optional[Dict[str, Any]]:
        rows = self.db.fetch_data(
            "SELECT id, username, nombre_completo, email, activo FROM pal_usuarios WHERE id = ?",
            (usuario_id,)
        )
        if not rows:
            return None
        r = rows[0]
        return {
            "id": int(r[0]),
            "username": str(r[1]),
            "nombre_completo": str(r[2]),
            "email": str(r[3]) if r[3] is not None else None,
            "activo": bool(r[4])
        }

class RoleManager:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def crear_rol(self, nombre: str, descripcion: str | None, permisos_codigos: List[str] | None):
        self.db.execute_query(
            "INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (?, ?, 0)",
            (nombre, descripcion)
        )
        rol_id = int(self.db.fetch_data("SELECT id FROM pal_roles WHERE nombre = ?", (nombre,))[0][0])
        if permisos_codigos:
            for codigo in permisos_codigos:
                row = self.db.fetch_data("SELECT id FROM pal_permisos WHERE codigo = ?", (codigo,))
                if row:
                    permiso_id = int(row[0][0])
                    self.db.execute_query(
                        "IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = ? AND permiso_id = ?)\n"
                        "INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (?, ?)\n",
                        (rol_id, permiso_id, rol_id, permiso_id)
                    )
        return rol_id

    def actualizar_rol(self, rol_id: int, **kwargs):
        campos = []
        params: List[Any] = []
        for k in ("nombre", "descripcion"):
            if k in kwargs:
                campos.append(f"{k} = ?")
                params.append(kwargs[k])
        if not campos:
            return False
        params.append(rol_id)
        return self.db.execute_query(
            f"UPDATE pal_roles SET {', '.join(campos)} WHERE id = ?",
            tuple(params)
        )

    def asignar_rol_usuario(self, usuario_id: int, rol_id: int):
        return self.db.execute_query(
            "IF NOT EXISTS (SELECT 1 FROM pal_usuarios_roles WHERE usuario_id = ? AND rol_id = ?)\n"
            "INSERT INTO pal_usuarios_roles (usuario_id, rol_id) VALUES (?, ?)\n",
            (usuario_id, rol_id, usuario_id, rol_id)
        )

    def remover_rol_usuario(self, usuario_id: int, rol_id: int):
        return self.db.execute_query(
            "DELETE FROM pal_usuarios_roles WHERE usuario_id = ? AND rol_id = ?",
            (usuario_id, rol_id)
        )
