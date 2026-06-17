"""
Módulo de auditoría para la aplicación PAL
"""
import logging
from logging.handlers import RotatingFileHandler

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)

        handler = RotatingFileHandler(
            'audit.log',
            maxBytes=5*1024*1024, # 5MB
            backupCount= 3,
            encoding='utf-8'
        )

        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_event(self, action, user, status, error_code=None, extra_detail: str = ""):
        """
        Registra un evento en el log de auditoría.

        Args:
            action      : Nombre de la acción (e.g. 'DB_CONNECTION_ERROR').
            user        : Usuario que realiza la acción.
            status      : 'SUCCESS' | 'FAILED' | cualquier cadena de estado.
            error_code  : ErrorCode enum con .code y .description (opcional).
            extra_detail: Texto libre adicional, p.ej. el mensaje real de la excepción
                          o un traceback resumido. Se añade al final de la línea.
        """
        log_entry = f"USER: {user} | ACTION: {action} | STATUS: {status}"
        if error_code:
            log_entry += f" | ERROR: {error_code.code} - {error_code.description}"
        if extra_detail:
            # Colapsar saltos de línea para que quede en una sola línea de log
            detail_inline = extra_detail.replace("\r\n", " ").replace("\n", " ").strip()
            log_entry += f" | DETAIL: {detail_inline}"

        if status == "FAILED" or (error_code is not None):
            self.logger.error(log_entry)
        else:
            self.logger.info(log_entry)