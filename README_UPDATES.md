# Sistema de Actualizaciones Automáticas

Este documento explica cómo funciona el sistema de actualizaciones automáticas integrado en la aplicación.

## Características

- ✅ Verificación automática de actualizaciones en segundo plano
- ✅ Notificación al usuario cuando hay actualizaciones disponibles
- ✅ Descarga e instalación de actualizaciones con confirmación del usuario
- ✅ Interfaz de usuario para gestionar actualizaciones manualmente
- ✅ Permisos de administrador al iniciar la aplicación (UAC)

## Configuración

### 1. Instalación de Dependencias

Asegúrate de tener `pyautoupdate` instalado:

```bash
pip install -r requirements.txt
```

### 2. Configurar URL de Actualizaciones

Edita `app.py` y configura la URL base donde se alojarán las actualizaciones:

```python
UPDATE_URL = "https://tu-servidor.com/updates/"  # Cambiar por tu URL real
```

### 3. Estructura del Servidor de Actualizaciones

El servidor debe tener la siguiente estructura:

```
updates/
├── version.json          # Información de la versión actual
└── app-1.0.1.zip        # Archivo ZIP con la nueva versión
```

### 4. Formato de version.json

El archivo `version.json` debe tener el siguiente formato:

```json
{
  "version": "1.0.1",
  "url": "https://tu-servidor.com/updates/app-1.0.1.zip",
  "changelog": "Descripción de los cambios en esta versión"
}
```

## Uso

### Verificación Automática

La aplicación verifica automáticamente actualizaciones cada hora en segundo plano. Si encuentra una actualización, mostrará una notificación al usuario.

### Verificación Manual

1. Abre la aplicación
2. Ve a **Configuración** > **Actualizaciones**
3. Haz clic en **"Verificar actualizaciones ahora"**

### Instalación de Actualizaciones

1. Cuando se detecte una actualización, se mostrará un diálogo
2. Si aceptas, la aplicación:
   - Descargará la actualización
   - La instalará
   - Reiniciará la aplicación automáticamente

## Pruebas Locales

Para probar el sistema de actualizaciones localmente:

### 1. Iniciar Servidor de Prueba

```bash
python test_updates.py
```

Esto iniciará un servidor HTTP local en `http://localhost:8000`

### 2. Configurar URL Temporal

Temporalmente cambia `UPDATE_URL` en `app.py`:

```python
UPDATE_URL = "http://localhost:8000/updates/"  # Solo para pruebas
```

### 3. Probar Actualizaciones

1. Ejecuta la aplicación principal
2. Ve a **Configuración** > **Actualizaciones**
3. Haz clic en **"Verificar actualizaciones ahora"**
4. Deberías ver que hay una actualización disponible (versión 1.0.1)

## Permisos de Administrador

La aplicación está configurada para solicitar permisos de administrador al iniciar mediante UAC (User Account Control) de Windows.

Esto se configura en `app.spec` con:

```python
uac_admin=True,  # Solicitar permisos de administrador al iniciar
```

**Nota:** Esto significa que Windows mostrará un diálogo de UAC cada vez que se inicie la aplicación, solicitando permisos de administrador.

### Alternativa: Permisos Opcionales

Si prefieres que la aplicación solo solicite permisos cuando sea necesario (no al iniciar), puedes:

1. Cambiar `uac_admin=True` a `uac_admin=False` en `app.spec`
2. Solicitar permisos programáticamente cuando sea necesario usando `ctypes.windll.shell32.ShellExecuteW`

## Compilación con PyInstaller

Para compilar la aplicación con las actualizaciones y permisos de administrador:

```bash
pyinstaller app.spec
```

O directamente:

```bash
pyinstaller --uac-admin --onefile --windowed --icon=pal/ui/image.ico app.py
```

## Solución de Problemas

### Error: "pyautoupdate no está instalado"

```bash
pip install pyautoupdate
```

### Error: "No se pudo verificar actualizaciones"

- Verifica que la URL de actualizaciones sea accesible
- Asegúrate de que el archivo `version.json` esté disponible en la URL
- Verifica la conexión a internet

### La aplicación no solicita permisos de administrador

- Verifica que `uac_admin=True` esté en `app.spec`
- Recompila la aplicación con PyInstaller
- Asegúrate de que el manifest esté incluido en el ejecutable

## Archivos Relacionados

- `pal/core/updater.py` - Módulo principal de actualizaciones
- `app.py` - Integración del sistema de actualizaciones
- `app.spec` - Configuración de PyInstaller con UAC
- `test_updates.py` - Script de prueba local
- `app.manifest` - Manifest XML para permisos de administrador

## Versión Actual

La versión actual de la aplicación se define en `app.py`:

```python
APP_VERSION = "1.0.0"
```

Asegúrate de incrementar esta versión cuando publiques una nueva actualización.
