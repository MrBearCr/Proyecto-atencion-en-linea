"""
Gestor seguro de credenciales para la aplicación PAL
"""
import sys as _sys

# --- Compatibilidad con ejecutables compilados (Nuitka / PyInstaller) ---
# Cuando la app corre como binario compilado, el mecanismo de auto-detección
# del backend de keyring falla. Se fuerza el backend de Windows explícitamente.
_is_compiled = getattr(_sys, 'frozen', False) or '__compiled__' in dir()
if _is_compiled:
    try:
        import keyring.backends.Windows
        import keyring
        keyring.set_keyring(keyring.backends.Windows.WinVaultKeyring())
    except Exception:
        import keyring  # Fallback: dejar que keyring intente auto-detectar
else:
    import keyring

from cryptography.fernet import Fernet
from .errors import ErrorCode

class SecureCredentialsManager:
    def __init__(self):
        self.service_name = "DBClientApp"
        self.key = self.get_or_create_key()
        
    def get_or_create_key(self):
        key = keyring.get_password(self.service_name, "encryption_key")
        if not key:    
            key = Fernet.generate_key().decode()
            keyring.set_password(self.service_name, "encryption_key", key)  
        return key.encode()

    def encrypt(self, data):
        try:
            return Fernet(self.key).encrypt(data.encode()).decode()
        except Exception as e:
            error_msg = f"{ErrorCode.ENCRYPTION_FAILED}: {str(e)}"
            raise Exception(error_msg) from e

    def decrypt(self, encrypted_data):
        try:
            return Fernet(self.key).decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            error_msg = f"{ErrorCode.DECRYPTION_FAILED}: {str(e)}"
            raise Exception(error_msg) from e

    def store_temp_password(self, password):
        if password:
            encrypted = self.encrypt(password)
            keyring.set_password(self.service_name, "temp_pass", encrypted)

    def get_temp_password(self):
        encrypted = keyring.get_password(self.service_name, "temp_pass")
        return self.decrypt(encrypted) if encrypted else None

    def get_whatsapp_token(self):
        encrypted_token = keyring.get_password(self.service_name, "whatsapp_token")
        return self.decrypt(encrypted_token) if encrypted_token else None

    def store_whatsapp_token(self, token):
        try:
            encrypted = self.encrypt(token) if token else ""
            keyring.set_password(self.service_name, "whatsapp_token", encrypted)
        except Exception as e:
            error_msg = f"{ErrorCode.ENCRYPTION_FAILED}: {str(e)}"
            raise Exception(error_msg) from e
