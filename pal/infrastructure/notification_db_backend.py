"""
Backend de persistencia para el sistema de notificaciones PAL.
Implementa NotificationDBBackend usando pyodbc (SQL Server / VAD10).

Tabla destino: pal_notificaciones  (creada por migración 010)

Uso típico en app.py:
    from pal.infrastructure.notification_db_backend import PyodbcNotificationBackend
    from pal.services.notifications import NotificationManager

    backend = PyodbcNotificationBackend(db_manager)
    self.notification_manager = NotificationManager(db_backend=backend)
    self.notification_manager.load_from_db(usuario=current_user)
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pal.services.notifications import Notification, NotificationDBBackend


class PyodbcNotificationBackend(NotificationDBBackend):
    """
    Implementación concreta de NotificationDBBackend que usa el
    DatabaseManager existente (pal/infrastructure/database.py) para
    persistir notificaciones en la tabla pal_notificaciones.
    """

    def __init__(self, db_manager):
        """
        Args:
            db_manager: Instancia de DatabaseManager ya conectada.
        """
        self._db = db_manager

    # ------------------------------------------------------------------
    # save — INSERT OR UPDATE
    # ------------------------------------------------------------------

    def save(self, notification: Notification) -> None:
        """
        Inserta la notificación en BD.  Si ya existe el mismo id, actualiza.
        """
        row = notification.to_db_dict()

        # Intentar UPDATE primero; si no afecta filas, hacer INSERT
        update_sql = """
            UPDATE pal_notificaciones SET
                titulo          = ?,
                mensaje         = ?,
                prioridad       = ?,
                modulo          = ?,
                modulo_ruta     = ?,
                accion_etiqueta = ?,
                datos_json      = ?,
                leida           = ?,
                descartada      = ?,
                tratada         = ?,
                c_usuario       = ?,
                c_usuario_trato = ?,
                f_leida         = ?,
                f_tratada       = ?,
                f_expiracion    = ?
            WHERE id = ?
        """
        update_params = (
            row["titulo"],
            row["mensaje"],
            row["prioridad"],
            row["modulo"],
            row["modulo_ruta"],
            row["accion_etiqueta"],
            row["datos_json"],
            row["leida"],
            row["descartada"],
            row["tratada"],
            row["c_usuario"],
            row["c_usuario_trato"],
            row["f_leida"],
            row["f_tratada"],
            row["f_expiracion"],
            row["id"],
        )

        # Atomic upsert using MERGE (SQL Server)
        merge_sql = """
            MERGE INTO pal_notificaciones AS target
            USING (SELECT ? AS id) AS source
            ON target.id = source.id
            WHEN MATCHED THEN
                UPDATE SET
                    titulo          = ?,
                    mensaje         = ?,
                    prioridad       = ?,
                    modulo          = ?,
                    modulo_ruta     = ?,
                    accion_etiqueta = ?,
                    datos_json      = ?,
                    leida           = ?,
                    descartada      = ?,
                    tratada         = ?,
                    c_usuario       = ?,
                    c_usuario_trato = ?,
                    f_leida         = ?,
                    f_tratada       = ?,
                    f_expiracion    = ?
            WHEN NOT MATCHED THEN
                INSERT (
                    id, titulo, mensaje, prioridad, modulo,
                    modulo_ruta, accion_etiqueta, datos_json,
                    leida, descartada, tratada,
                    c_usuario, c_usuario_trato,
                    f_creacion, f_leida, f_tratada, f_expiracion
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?
                )
        """
        merge_params = (
            row["id"],
            row["titulo"],
            row["mensaje"],
            row["prioridad"],
            row["modulo"],
            row["modulo_ruta"],
            row["accion_etiqueta"],
            row["datos_json"],
            row["leida"],
            row["descartada"],
            row["tratada"],
            row["c_usuario"],
            row["c_usuario_trato"],
            row["f_leida"],
            row["f_tratada"],
            row["f_expiracion"],
            row["id"],
            row["titulo"],
            row["mensaje"],
            row["prioridad"],
            row["modulo"],
            row["modulo_ruta"],
            row["accion_etiqueta"],
            row["datos_json"],
            row["leida"],
            row["descartada"],
            row["tratada"],
            row["c_usuario"],
            row["c_usuario_trato"],
            row["f_creacion"] or datetime.now(),
            row["f_leida"],
            row["f_tratada"],
            row["f_expiracion"],
        )
        self._db.execute_query(merge_sql, merge_params)

    # ------------------------------------------------------------------
    # update_status — solo campos de estado
    # ------------------------------------------------------------------

    def update_status(self, notification: Notification) -> None:
        """
        Actualiza únicamente los campos de estado de una notificación existente:
        leida, descartada, tratada, c_usuario_trato, f_leida, f_tratada.
        """
        sql = """
            UPDATE pal_notificaciones SET
                leida           = ?,
                descartada      = ?,
                tratada         = ?,
                c_usuario_trato = ?,
                f_leida         = ?,
                f_tratada       = ?
            WHERE id = ?
        """
        params = (
            1 if notification.read else 0,
            1 if notification.dismissed else 0,
            1 if notification.treated else 0,
            getattr(notification, "usuario_trato", None),
            notification.f_leida,
            notification.f_tratada,
            notification.id,
        )
        self._db.execute_query(sql, params)

    # ------------------------------------------------------------------
    # load_active — SELECT notificaciones activas
    # ------------------------------------------------------------------

    def load_active(self, usuario: Optional[str] = None) -> List[Dict]:
        """
        Carga notificaciones activas (no descartadas, no expiradas).
        Ordena por prioridad urgente primero, luego por fecha descendente.

        Args:
            usuario: Si se provee, filtra por c_usuario.

        Returns:
            Lista de dicts con las columnas de pal_notificaciones.
        """
        where_clauses = [
            "descartada = 0",
            "(f_expiracion IS NULL OR f_expiracion > GETDATE())",
        ]
        params: list = []

        if usuario:
            where_clauses.append("(c_usuario = ? OR c_usuario IS NULL)")
            params.append(usuario)

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT
                id, titulo, mensaje, prioridad, modulo,
                modulo_ruta, accion_etiqueta, datos_json,
                leida, descartada, tratada,
                c_usuario, c_usuario_trato,
                f_creacion, f_leida, f_tratada, f_expiracion
            FROM pal_notificaciones
            WHERE {where_sql}
            ORDER BY
                CASE prioridad
                    WHEN 'urgent'  THEN 1
                    WHEN 'warning' THEN 2
                    WHEN 'info'    THEN 3
                    WHEN 'success' THEN 4
                    ELSE 5
                END ASC,
                f_creacion DESC
        """

        rows = self._db.fetch_data(sql, params) or []

        # Convertir pyodbc.Row → dict
        columns = [
            "id", "titulo", "mensaje", "prioridad", "modulo",
            "modulo_ruta", "accion_etiqueta", "datos_json",
            "leida", "descartada", "tratada",
            "c_usuario", "c_usuario_trato",
            "f_creacion", "f_leida", "f_tratada", "f_expiracion",
        ]
        return [dict(zip(columns, row)) for row in rows]

    # ------------------------------------------------------------------
    # purge_expired — limpieza por política de retención
    # ------------------------------------------------------------------

    def purge_expired(self) -> int:
        """
        Elimina notificaciones cuya fecha de expiración ya pasó.
        Devuelve el número de filas eliminadas (0 si no se puede determinar).
        """
        sql = """
            DELETE FROM pal_notificaciones
            WHERE f_expiracion IS NOT NULL
              AND f_expiracion < GETDATE()
        """
        try:
            self._db.execute_query(sql)
            # fetch_data para contar no es necesario; retornamos 0 como indicador de éxito
            return 0
        except Exception as e:
            print(f"[PyodbcNotificationBackend] Error en purge_expired: {e}")
            return 0
