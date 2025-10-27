# Gestión de Sesiones (Aplicación de Escritorio)

## Comportamiento
- Timeout de inactividad: 15 minutos (configurable) → cierra la app y purga secretos temporales.
- Detección de actividad: teclas, clics y movimiento del mouse en Tkinter.

## Implementación
```python
from pal.core.session import SessionManager

session = SessionManager(root)
session.start_session()           # Inicia el monitoreo
root.bind('<Key>', session.update_activity)
root.bind('<Button>', session.update_activity)
root.bind('<Motion>', session.update_activity)
```

## Seguridad
- Eliminación de contraseña temporal del keyring al expirar.
- No persiste tokens/credenciales en texto plano.

