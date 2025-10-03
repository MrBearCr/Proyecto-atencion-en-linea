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

    def log_event(self, action, user, status, error_code=None):
        log_entry = f"USER: {user} | ACTION: {action} | STATUS: {status}"
        if error_code:
            log_entry += f" | ERROR: {error_code.code} - {error_code.description}"
        self.logger.info(log_entry)