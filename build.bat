@echo off
chcp 65001 >nul 2>&1
echo.
echo ============================================================
echo   BUILD CASAPRO NEXUS - NUITKA COMPILER
echo   Genera un ejecutable nativo de alto rendimiento
echo ============================================================
echo.

REM --- Verificar Python y Nuitka ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en el PATH.
    pause & exit /b 1
)

python -m nuitka --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Nuitka no esta instalado. Ejecuta: pip install nuitka
    pause & exit /b 1
)

echo [OK] Python y Nuitka encontrados.
echo.

REM --- Seleccionar modo de build ---
echo Seleccione el modo de build:
echo   [1] STANDALONE (carpeta app.dist/ - recomendado para pruebas)
echo   [2] ONEFILE    (ejecutable unico - para distribucion final)
echo.
set /p BUILD_MODE="Opcion (1 o 2): "

if "%BUILD_MODE%"=="1" (
    set NUITKA_MODE=--standalone
    set MODE_LABEL=STANDALONE
    echo.
    echo Modo: STANDALONE (carpeta app.dist/)
) else (
    set NUITKA_MODE=--standalone --onefile
    set MODE_LABEL=ONEFILE
    echo.
    echo Modo: ONEFILE (ejecutable unico)
)
echo.

REM --- Limpiar builds anteriores ---
echo Limpiando builds anteriores...
if exist "app.dist"          rmdir /s /q "app.dist"
if exist "app.build"         rmdir /s /q "app.build"
if exist "app.onefile-build" rmdir /s /q "app.onefile-build"
if exist "Casapro Nexus.exe" del /q "Casapro Nexus.exe"
echo [OK] Limpieza completada.
echo.

REM --- Exclusion temporal de Windows Defender ---
echo Agregando exclusion temporal de Windows Defender...
powershell -Command "Add-MpPreference -ExclusionPath '%CD%' -ErrorAction SilentlyContinue" 2>nul
echo [OK] Exclusion configurada.
echo.

REM --- Iniciar compilacion ---
echo Iniciando compilacion Nuitka (modo %MODE_LABEL%)...
echo IMPORTANTE: Este proceso puede tardar entre 15 y 45 minutos.
echo No cierres esta ventana.
echo.
set INICIO_BUILD=%TIME%

REM ============================================================
REM  COMANDO NUITKA
REM  NOTA SOBRE ARCHIVOS EXCLUIDOS:
REM    Los archivos de runtime (license_cache.json, favoritos_cache.json,
REM    db_config.ini, jerarquia_cache.json, productos_jerarquia_cache.json)
REM    NO se incluyen en el build. Estos archivos son generados/leidos
REM    por la aplicacion en tiempo de ejecucion desde el directorio de
REM    trabajo del usuario, NO deben ir embebidos en el ejecutable.
REM    El paso "post-build cleanup" elimina cualquier copia residual
REM    que Nuitka haya copiado desde el directorio fuente.
REM ============================================================
python -m nuitka ^
  %NUITKA_MODE% ^
  --enable-plugin=tk-inter ^
  --windows-icon-from-ico=pal/ui/image.ico ^
  --windows-uac-admin ^
  --windows-company-name="Casapro" ^
  --windows-product-name="Casapro Nexus" ^
  --windows-file-description="Casapro Nexus - Plataforma de Administracion Local" ^
  --windows-file-version=1.7.1.0 ^
  --windows-product-version=1.7.1.0 ^
  --onefile-tempdir-spec="{TEMP}/CasaproNexus" ^
  --include-package=cryptography ^
  --include-package=keyring ^
  --include-package=keyring.backends ^
  --include-package=keyring.backends.Windows ^
  --include-package=bcrypt ^
  --include-package=bcrypt._bcrypt ^
  --include-package=PIL ^
  --include-package=matplotlib ^
  --include-package=matplotlib.backends ^
  --include-package=matplotlib.backends.backend_tkagg ^
  --include-package=packaging ^
  --include-package=packaging.version ^
  --include-package=pyodbc ^
  --include-package=tkcalendar ^
  --include-package=win10toast ^
  --include-package=requests ^
  --include-package=openpyxl ^
  --include-data-files=casapro-icono.png=casapro-icono.png ^
  --include-data-dir=pal/ui/=pal/ui/ ^
  --include-data-dir=recursos/=recursos/ ^
  --windows-disable-console ^
  --output-filename="Casapro Nexus.exe" ^
  app.py

echo.
echo Hora de inicio: %INICIO_BUILD%
echo Hora de fin:    %TIME%
echo.

REM ============================================================
REM  POST-BUILD: Eliminar archivos sensibles / de runtime
REM  Estos archivos NO deben ir incluidos en la distribucion:
REM    - db_config.ini         : credenciales de BD (encriptadas, pero privadas)
REM    - license_cache.json    : cache de licencia, especifico de cada maquina
REM    - favoritos_cache.json  : preferencias de usuario, especificas de cada maquina
REM    - jerarquia_cache.json  : cache regenerable automaticamente
REM    - productos_jerarquia_cache.json : cache regenerable automaticamente
REM  La app los crea/recarga desde BD al iniciar si no existen.
REM ============================================================
if exist "app.dist" (
    echo Eliminando archivos de runtime/configuracion sensibles del build...

    if exist "app.dist\db_config.ini"                      del /q "app.dist\db_config.ini"
    if exist "app.dist\license_cache.json"                 del /q "app.dist\license_cache.json"
    if exist "app.dist\favoritos_cache.json"               del /q "app.dist\favoritos_cache.json"
    if exist "app.dist\jerarquia_cache.json"               del /q "app.dist\jerarquia_cache.json"
    if exist "app.dist\productos_jerarquia_cache.json"     del /q "app.dist\productos_jerarquia_cache.json"
    if exist "app.dist\audit.log"                          del /q "app.dist\audit.log"
    if exist "app.dist\updater_launcher.log"               del /q "app.dist\updater_launcher.log"

    echo [OK] Limpieza post-build completada.
    echo.
)

REM --- Verificar resultado ---
if "%BUILD_MODE%"=="1" (
    if exist "app.dist\Casapro Nexus.exe" (
        echo ============================================================
        echo   BUILD EXITOSO [STANDALONE]
        echo   Directorio generado: app.dist\
        echo   Ejecutable: app.dist\Casapro Nexus.exe
        echo ============================================================
        echo.
        echo Para probar: app.dist\"Casapro Nexus.exe"
        for %%A in ("app.dist\Casapro Nexus.exe") do echo Tamanio: %%~zA bytes
    ) else (
        echo ============================================================
        echo   BUILD FALLIDO [STANDALONE]
        echo   Revisa los mensajes de error anteriores.
        echo ============================================================
    )
) else (
    if exist "Casapro Nexus.exe" (
        echo ============================================================
        echo   BUILD EXITOSO [ONEFILE]
        echo   Ejecutable generado: "Casapro Nexus.exe"
        echo ============================================================
        echo.
        echo Copiando a dist\ para compatibilidad con setup_nuitka.iss...
        if not exist "dist" mkdir dist
        copy /Y "Casapro Nexus.exe" "dist\Casapro Nexus.exe" >nul
        echo [OK] Copia en dist\Casapro Nexus.exe
        echo.
        for %%A in ("Casapro Nexus.exe") do echo Tamanio: %%~zA bytes
    ) else (
        echo ============================================================
        echo   BUILD FALLIDO [ONEFILE]
        echo   Revisa los mensajes de error anteriores.
        echo   Consejo: Primero prueba con modo STANDALONE (opcion 1).
        echo ============================================================
    )
)

echo.
pause
