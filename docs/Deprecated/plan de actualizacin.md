# Separación del Actualizador en un Ejecutable Independiente

Actualmente, la lógica de actualización reside dentro de la aplicación principal. Cuando se requiere elevar privilegios (UAC) para ejecutar el instalador de Inno Setup silenciosamente, la aplicación intenta hacer malabares usando scripts Batch y PowerShell. Esto es propenso a errores y dependiente de la configuración del sistema operativo.

El nuevo enfoque separará esta lógica en un pequeño ejecutable independiente (`nexus_updater.exe`) que se compilará pidiendo permisos de Administrador nativamente.

## Proposed Changes

### Componente: Aplicación Principal y Actualizador

#### [NEW] `updater_main.py`
Se creará un script dedicado para el actualizador. Este script:
1. Recibirá argumentos por línea de comandos: la ruta del archivo ZIP descargado y la ruta del ejecutable principal a reiniciar.
2. Esperará a que el proceso principal de la aplicación termine.
3. Extraerá el ZIP (si es necesario) y buscará el instalador `.exe`.
4. Ejecutará el instalador con los flags silenciosos (`/VERYSILENT /SUPPRESSMSGBOXES /FORCECLOSEAPPLICATIONS`).
5. Reiniciará la aplicación principal.

#### [MODIFY] `pal/core/updater.py`
La función `install_update` se simplificará drásticamente. En lugar de crear scripts VBScript, Batch o PowerShell, simplemente:
1. Ubicará `nexus_updater.exe` en el directorio de la aplicación.
2. Ejecutará `nexus_updater.exe` pasándole la ruta del ZIP descargado.
3. Cerrará la aplicación principal (`os._exit(0)`).

### Componente: Proceso de Construcción (Build)

#### [MODIFY] `build.bat`
Se modificará el script de compilación para que Nuitka compile **dos** ejecutables:
1. El ejecutable principal (`Casapro Nexus.exe`).
2. El ejecutable del actualizador (`nexus_updater.exe`). Para este, usaremos el flag `--windows-uac-admin` para que Windows lance el prompt de UAC automáticamente cada vez que se ejecute.

#### [MODIFY] `setup_nuitka.iss`
Se asegurará de que el archivo `nexus_updater.exe` se incluya en el instalador y se instale en el mismo directorio que la aplicación principal, para que la app principal pueda encontrarlo.

## User Review Required

> [!WARNING]
> Compilar dos ejecutables aumentará el tiempo total del proceso `build.bat` (Nuitka tendrá que compilar dos veces). Para mitigar esto, intentaremos compilar el actualizador con `--standalone --onefile` pero tratando de no incluir tantas dependencias pesadas como `matplotlib` o `tkcalendar` que no son necesarias para el actualizador. ¿Estás de acuerdo con este aumento en el tiempo de compilación?

## Verification Plan

### Manual Verification
- Compilar el proyecto entero usando el nuevo `build.bat`.
- Instalar la aplicación con Inno Setup.
- Simular una actualización (cambiando temporalmente la versión de prueba) y verificar que `nexus_updater.exe` lanza el prompt de UAC sin usar ventanas de consola extrañas y relanza la aplicación correctamente.
