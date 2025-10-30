"""
AuditDB: almacenamiento de auditoría en BD (pal_auditoria_accesos)
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime

from ..infrastructure.database import DatabaseManager

class AuditDB:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def log_access(
        self,
        accion: str,
        usuario_id: Optional[int] = None,
        exitoso: bool = True,
        ip_address: Optional[str] = None,
        modulo: Optional[str] = None,
        detalle: Optional[str] = None,
    ) -> None:
        try:
            self.db.execute_query(
                """
                INSERT INTO pal_auditoria_accesos (usuario_id, accion, modulo, detalle, ip_address, exitoso, fecha)
                VALUES (?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
                """,
                (
                    usuario_id,
                    accion,
                    modulo,
                    detalle,
                    ip_address,
                    1 if exitoso else 0,
                ),
            )
        except Exception:
            # No romper el flujo si falla la auditoría
            pass

    # Alias semántico
    def log_action(
        self,
        accion: str,
        usuario_id: Optional[int] = None,
        modulo: Optional[str] = None,
        detalle: Optional[str] = None,
        exitoso: bool = True,
        ip_address: Optional[str] = None,
    ) -> None:
        self.log_access(
            accion=accion,
            usuario_id=usuario_id,
            exitoso=exitoso,
            ip_address=ip_address,
            modulo=modulo,
            detalle=detalle,
        )
