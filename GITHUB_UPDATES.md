# Actualizaciones Automáticas con GitHub + Inno Setup

Guía para configurar actualizaciones automáticas cuando usas **PyInstaller + Inno Setup** para crear instaladores de Windows.

## 📋 Tu Flujo de Trabajo Actual

1. **PyInstaller**: Compila `app.py` → genera `Casapro Nexus.exe` (con permisos de administrador)
2. **Inno Setup**: Crea instalador `NEXUS-Setup.exe` que instala en `Program Files`
3. **GitHub Releases**: Publicas el instalador para distribución

## 🚀 Configuración para Actualizaciones

### Paso 1: Estructura del Repositorio

```
tu-repo/
├── updates/
│   └── version.json
├── app.py
├── app.spec
├── setup.iss
└── ...
```

### Paso 2: Crear archivo version.json

Crea `updates/version.json` con este formato:

```json
{
  "version": "1.0.1",
  "url": "https://github.com/tu-usuario/tu-repo/releases/download/v1.0.1/NEXUS-Setup-1.0.1.zip",
  "changelog": "Versión 1.0.1:\n- Nuevas funcionalidades\n- Corrección de errores"
}
```

**Importante:**
- `version`: Debe ser mayor que `APP_VERSION` en `app.py`
- `url`: URL del ZIP que contiene el instalador `NEXUS-Setup.exe`

### Paso 3: Preparar el Instalador para GitHub

Cuando compiles con Inno Setup, crea un ZIP con el instalador:

```powershell
# Después de compilar con Inno Setup
# El instalador estará en: dist\NEXUS-Setup.exe

# Crear ZIP con el instalador
Compress-Archive -Path "dist\NEXUS-Setup.exe" -DestinationPath "dist\NEXUS-Setup-1.0.1.zip"
```

**Estructura del ZIP:**
```
NEXUS-Setup-1.0.1.zip
└── NEXUS-Setup.exe
```

### Paso 4: Publicar en GitHub Releases

1. Ve a tu repositorio → **Releases** → **Create a new release**
2. Completa:
   - **Tag version**: `v1.0.1`
   - **Release title**: `Versión 1.0.1`
   - **Description**: Changelog
3. Arrastra `NEXUS-Setup-1.0.1.zip` a "Attach binaries"
4. Publica el release

### Paso 5: Obtener URL de descarga

1. En la página del release, haz clic derecho en `NEXUS-Setup-1.0.1.zip`
2. **Copy link address**
3. Usa esa URL en `version.json`:
   ```json
   {
     "version": "1.0.1",
     "url": "https://github.com/tu-usuario/tu-repo/releases/download/v1.0.1/NEXUS-Setup-1.0.1.zip"
   }
   ```

### Paso 6: Servir version.json

#### Opción A: GitHub Pages (Recomendado)

1. **Settings** → **Pages** → Selecciona rama `main`
2. Tu `version.json` estará en:
   ```
   https://tu-usuario.github.io/tu-repo/updates/version.json
   ```
3. URL base para la app:
   ```
   https://tu-usuario.github.io/tu-repo/updates/
   ```

#### Opción B: Raw GitHub

URL directa:
```
https://raw.githubusercontent.com/tu-usuario/tu-repo/main/updates/version.json
```

URL base para la app:
```
https://raw.githubusercontent.com/tu-usuario/tu-repo/main/updates/
```

### Paso 7: Configurar la aplicación

1. Abre la aplicación
2. **Configuración** → **Actualizaciones**
3. Ingresa la URL base (termina con `/updates/`)
4. **Guardar URL**
5. **Verificar actualizaciones ahora** para probar

## 🔄 Flujo Completo de Publicación

### Cuando quieras publicar una nueva versión:

#### 1. Actualizar versión en código

En `app.py`:
```python
APP_VERSION = "1.0.1"  # Nueva versión
```

En `setup.iss`:
```iss
#define MyAppVersion "1.0.1"
```

#### 2. Compilar con PyInstaller

```powershell
pyinstaller app.spec
```

Esto genera: `dist\Casapro Nexus.exe`

#### 3. Compilar instalador con Inno Setup

```powershell
# Abrir Inno Setup Compiler
# O desde línea de comandos:
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
```

Esto genera: `dist\NEXUS-Setup.exe`

#### 4. Crear ZIP del instalador

```powershell
# PowerShell
$version = "1.0.1"
Compress-Archive -Path "dist\NEXUS-Setup.exe" -DestinationPath "dist\NEXUS-Setup-$version.zip" -Force
```

#### 5. Actualizar version.json

```json
{
  "version": "1.0.1",
  "url": "https://github.com/tu-usuario/tu-repo/releases/download/v1.0.1/NEXUS-Setup-1.0.1.zip",
  "changelog": "Versión 1.0.1:\n- Descripción de cambios"
}
```

#### 6. Subir a GitHub

```powershell
# Subir version.json actualizado
git add updates/version.json
git commit -m "Actualizar a versión 1.0.1"
git push

# Crear release en GitHub (manual o con GitHub CLI)
```

#### 7. Crear Release en GitHub

1. Ve a **Releases** → **Create a new release**
2. Tag: `v1.0.1`
3. Sube `NEXUS-Setup-1.0.1.zip`
4. Publica

#### 8. Los usuarios recibirán la notificación automáticamente

La aplicación:
- Detectará la nueva versión
- Descargará el ZIP
- Extraerá el instalador
- Lo ejecutará con permisos de administrador
- Cerrará la app actual
- El instalador actualizará la instalación existente
- El usuario puede reiniciar la app manualmente

## 📝 Script de Automatización (Opcional)

Crea `build_and_release.ps1`:

```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

Write-Host "Construyendo versión $Version..." -ForegroundColor Green

# 1. Actualizar versión en app.py (manual o con script)
Write-Host "1. Actualizando APP_VERSION en app.py..." -ForegroundColor Yellow
# (Hacer manualmente o usar sed/regex)

# 2. Compilar con PyInstaller
Write-Host "2. Compilando con PyInstaller..." -ForegroundColor Yellow
pyinstaller app.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error en PyInstaller" -ForegroundColor Red
    exit 1
}

# 3. Compilar con Inno Setup
Write-Host "3. Compilando instalador con Inno Setup..." -ForegroundColor Yellow
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error en Inno Setup" -ForegroundColor Red
    exit 1
}

# 4. Crear ZIP
Write-Host "4. Creando ZIP..." -ForegroundColor Yellow
$zipName = "NEXUS-Setup-$Version.zip"
Compress-Archive -Path "dist\NEXUS-Setup.exe" -DestinationPath "dist\$zipName" -Force

Write-Host "✅ Build completado!" -ForegroundColor Green
Write-Host "Archivo: dist\$zipName" -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "1. Actualizar updates/version.json con la nueva versión"
Write-Host "2. Subir version.json a GitHub"
Write-Host "3. Crear release en GitHub y subir $zipName"
```

Uso:
```powershell
.\build_and_release.ps1 -Version "1.0.1"
```

## ⚙️ Configuración del Instalador Inno Setup

Para que el instalador actualice correctamente, asegúrate en `setup.iss`:

```iss
[Setup]
AppId={228B5B49-524C-4328-8A33-524787258525}  ; Mismo AppId = actualiza instalación existente
DefaultDirName={autopf}\{#MyAppName}
; ... resto de configuración
```

**Importante:** El `AppId` debe ser el mismo en todas las versiones para que Inno Setup actualice en lugar de instalar de nuevo.

## 🔧 Mejoras Opcionales

### Modo Silencioso para Actualizaciones

El instalador se ejecuta con `/SILENT` para actualizaciones automáticas. Si quieres más control:

En `setup.iss`, puedes agregar:
```iss
[Setup]
; Permitir actualización silenciosa
DisableProgramGroupPage=yes
DisableDirPage=yes
```

### Verificar Versión del Instalador

Puedes agregar verificación de versión en el instalador para evitar downgrades.

## ⚠️ Notas Importantes

1. **AppId constante**: El `AppId` en `setup.iss` debe ser el mismo siempre
2. **Versiones**: Usa formato semántico (1.0.0, 1.0.1, 1.1.0)
3. **Permisos**: El instalador se ejecuta con permisos de administrador (UAC)
4. **Cierre de app**: La aplicación se cierra automáticamente antes de instalar
5. **Reinicio**: El usuario debe reiniciar la app manualmente después de la actualización

## 🧪 Probar Localmente

```bash
# Terminal 1: Servidor de prueba
python test_updates.py

# Terminal 2: Aplicación
python app.py
```

Configura URL temporal: `http://localhost:8000/updates/`

## 📚 Recursos

- [Inno Setup Documentation](https://jrsoftware.org/ishelp/)
- [GitHub Releases API](https://docs.github.com/en/rest/releases)
- [PyInstaller Documentation](https://pyinstaller.org/)

---

**Checklist de Publicación:**
- ✅ Actualizar `APP_VERSION` en `app.py`
- ✅ Actualizar `MyAppVersion` en `setup.iss`
- ✅ Compilar con PyInstaller
- ✅ Compilar instalador con Inno Setup
- ✅ Crear ZIP del instalador
- ✅ Actualizar `version.json` con nueva versión y URL
- ✅ Subir `version.json` a GitHub
- ✅ Crear Release en GitHub con el ZIP
- ✅ Verificar que la URL de descarga funcione
