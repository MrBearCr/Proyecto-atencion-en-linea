# Sistema de Auditoría

## Eventos auditados
- Conexión/Desconexión a BD y operaciones de datos.
- Envíos (éxito/error) a WhatsApp.
- Cambios de configuración y acciones del usuario.
- Errores con códigos `ErrorCode`.

## Implementación (Python)
```python
from pal.core.audit import AuditLogger
from pal.core.errors import ErrorCode

audit = AuditLogger()
audit.log_event("LOGIN", user="admin", status="SUCCESS")
audit.log_event("DATABASE_QUERY", user="user", status="FAILED", error_code=ErrorCode.DB_QUERY_EXECUTION)
```

- Logger rotativo: archivo `audit.log`, 5MB, 3 backups, UTF-8.
- Formato estándar: fecha | nivel | mensaje.

## Retención
- Rotación local por tamaño. Para retención extendida, enviar a sistema externo de logs.

