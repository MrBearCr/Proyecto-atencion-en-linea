"""
PermissionsManager: autorización y permisos (módulos habilitados por usuario)
"""
from __future__ import annotations
from typing import Set, Dict, List

from ..infrastructure.database import DatabaseManager

class PermissionsManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._cache: Dict[int, Dict[str, Set[str]]] = {}

    def limpiar_cache_usuario(self, usuario_id: int):
        self._cache.pop(usuario_id, None)

    def modulo_habilitado(self, usuario_id: int, modulo: str) -> bool:
        rows = self.db.fetch_data(
            "SELECT 1 FROM pal_usuarios_modulos WHERE usuario_id = ? AND modulo = ? AND habilitado = 1",
            (usuario_id, modulo)
        )
        return bool(rows)

    def _cargar_permisos(self, usuario_id: int) -> Dict[str, Set[str]]:
        if usuario_id in self._cache:
            return self._cache[usuario_id]
        permisos: Dict[str, Set[str]] = {}

        # Permisos directos
        rows = self.db.fetch_data(
            """
            SELECT p.modulo, p.codigo, up.concedido
            FROM pal_usuarios_permisos up
            JOIN pal_permisos p ON p.id = up.permiso_id
            WHERE up.usuario_id = ?
            """,
            (usuario_id,)
        )
        for modulo, codigo, concedido in rows or []:
            mod = str(modulo)
            if concedido:
                permisos.setdefault(mod, set()).add(str(codigo).split(".")[-1])
            else:
                # denegado explícito: asegura ausencia
                permisos.setdefault(mod, set()).discard(str(codigo).split(".")[-1])

        # Permisos por roles
        rows = self.db.fetch_data(
            """
            SELECT p.modulo, p.codigo
            FROM pal_usuarios_roles ur
            JOIN pal_roles_permisos rp ON rp.rol_id = ur.rol_id
            JOIN pal_permisos p ON p.id = rp.permiso_id
            WHERE ur.usuario_id = ?
            """,
            (usuario_id,)
        )
        for modulo, codigo in rows or []:
            mod = str(modulo)
            permisos.setdefault(mod, set()).add(str(codigo).split(".")[-1])

        self._cache[usuario_id] = permisos
        return permisos

    def tiene_permiso(self, usuario_id: int, modulo: str, accion: str) -> bool:
        # 0) módulo debe estar habilitado
        if not self.modulo_habilitado(usuario_id, modulo):
            return False
        perms = self._cargar_permisos(usuario_id)
        acciones = perms.get(modulo, set())
        return accion in acciones

    def obtener_permisos_usuario(self, usuario_id: int) -> Dict[str, Set[str]]:
        # Solo devolver permisos para módulos habilitados
        habilitados = set(self.obtener_modulos_disponibles(usuario_id))
        perms = self._cargar_permisos(usuario_id)
        return {m: a for m, a in perms.items() if m in habilitados}

    def obtener_modulos_disponibles(self, usuario_id: int) -> List[str]:
        rows = self.db.fetch_data(
            "SELECT modulo FROM pal_usuarios_modulos WHERE usuario_id = ? AND habilitado = 1",
            (usuario_id,)
        )
        return [str(r[0]) for r in (rows or [])]

    def asignar_permiso_directo(self, usuario_id: int, permiso_codigo: str, concedido: bool = True):
        # Buscar permiso_id
        rows = self.db.fetch_data(
            "SELECT id FROM pal_permisos WHERE codigo = ?",
            (permiso_codigo,)
        )
        if not rows:
            return False
        permiso_id = int(rows[0][0])
        # Upsert simple
        updated = self.db.execute_query(
            """
            IF EXISTS (SELECT 1 FROM pal_usuarios_permisos WHERE usuario_id = ? AND permiso_id = ?)
                UPDATE pal_usuarios_permisos SET concedido = ? WHERE usuario_id = ? AND permiso_id = ?
            ELSE
                INSERT INTO pal_usuarios_permisos (usuario_id, permiso_id, concedido) VALUES (?, ?, ?)
            """,
            (usuario_id, permiso_id, 1 if concedido else 0, usuario_id, permiso_id, usuario_id, permiso_id, 1 if concedido else 0)
        )
        self.limpiar_cache_usuario(usuario_id)
        return updated
