# Seguridad y Manejo de Secretos

## Arquitectura
- Master key en Windows Credential Manager (keyring) bajo el servicio "DBClientApp".
- Datos sensibles (contraseñas, token de WhatsApp) cifrados con Fernet (cryptography).
- Timeout de sesión: 15 minutos; al expirar, se eliminan secretos temporales.

## Implementación (Python)
```python
from pal.core.credentials import SecureCredentialsManager

cred = SecureCredentialsManager()
# Guardar token
cred.store_whatsapp_token("<TOKEN>")
# Leer token
token = cred.get_whatsapp_token()
```

Generación/rotación de clave maestra:
```python
# Al primer uso
key = keyring.get_password("DBClientApp", "encryption_key")
if not key:
    key = Fernet.generate_key().decode()
    keyring.set_password("DBClientApp", "encryption_key", key)
```

## Sesiones
```python
from pal.core.session import SessionManager
session = SessionManager(root)
session.start_session()  # Monitorea actividad y expira tras 900s
```

## Buenas prácticas
- No registrar secretos en logs.
- Preferir variables de entorno para despliegues automatizados, o el keyring interactivo de la app.
- Rotar token de WhatsApp periódicamente.

