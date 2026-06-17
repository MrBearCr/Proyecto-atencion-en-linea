@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   BUILD CASAPRO NEXUS - NUITKA COMPILER
echo   Genera un ejecutable nativo de alto rendimiento
echo ============================================================
echo.

REM ─── Verificar que Python y Nuitka estén disponibles ──────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en el PATH.
    pause & exit /b 1
)

python -m nuitka --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Nuitka no está instalado. Ejecuta: pip install nuitka
    pause & exit /b 1
)

echo [OK] Python y Nuitka encontrados.
echo.

REM ─── Seleccionar modo de build ────────────────────────────────────────────
echo Seleccione el modo de build:
echo   [1] STANDALONE (carpeta - MAS RAPIDO para depuracion)
echo   [2] ONEFILE    (ejecutable unico - para distribucion)
echo.
set /p BUILD_MODE="Opcion (1 o 2): "

if "%BUILD_MODE%"=="1" (
    set NUITKA_MODE=--standalone
    set MODE_LABEL=STANDALONE
    echo.
    echo Modo seleccionado: STANDALONE (carpeta app.dist/)
) else (
    set NUITKA_MODE=--standalone --onefile
    set MODE_LABEL=ONEFILE
    echo.
    echo Modo seleccionado: ONEFILE (ejecutable unico)
)
echo.

REM ─── Limpiar builds anteriores ────────────────────────────────────────────
echo Limpiando builds anteriores...
if exist "app.dist"          rmdir /s /q "app.dist"
if exist "app.build"         rmdir /s /q "app.build"
if exist "app.onefile-build" rmdir /s /q "app.onefile-build"
if exist "Casapro Nexus.exe" del /q "Casapro Nexus.exe"
echo [OK] Limpieza completada.
echo.

REM ─── Excluir del Windows Defender durante build ───────────────────────────
echo Agregando exclusion temporal de Windows Defender...
powershell -Command "Add-MpPreference -ExclusionPath '%CD%' -ErrorAction SilentlyContinue" 2>nul
echo [OK] Exclusion de Defender configurada (se puede revertir manualmente).
echo.

REM ─── Información del build ────────────────────────────────────────────────
echo Iniciando compilacion con Nuitka (modo %MODE_LABEL%)...
echo IMPORTANTE: Este proceso puede tardar entre 15 y 45 minutos.
echo No cierres esta ventana.
echo.
set INICIO_BUILD=%TIME%

REM ─── Comando de compilación ───────────────────────────────────────────────
python -m nuitka ^
  %NUITKA_MODE% ^
  --enable-plugin=tk-inter ^
  --windows-icon-from-ico=pal/ui/image.ico ^
  --windows-uac-admin ^
  --windows-company-name="Casapro" ^
  --windows-product-name="Casapro Nexus" ^
  --windows-file-description="Casapro Nexus - Plataforma de Administracion Local" ^
  --windows-file-version=1.6.9.0 ^
  --windows-product-version=1.6.9.0 ^
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

REM ─── Verificar resultado ──────────────────────────────────────────────────
if "%BUILD_MODE%"=="1" (
    REM Standalone: verificar carpeta app.dist
    if exist "app.dist\Casapro Nexus.exe" (
        echo ============================================================
        echo   BUILD EXITOSO [STANDALONE]
        echo   Directorio generado: app.dist\
        echo   Ejecutable: app.dist\Casapro Nexus.exe
        echo ============================================================
        echo.
        echo Para probar:  app.dist\"Casapro Nexus.exe"
        for %%A in ("app.dist\Casapro Nexus.exe") do echo Tamanio: %%~zA bytes
    ) else (
        echo ============================================================
        echo   BUILD FALLIDO [STANDALONE]
        echo   Revisa los mensajes de error anteriores.
        echo ============================================================
    )
) else (
    REM Onefile: verificar .exe en la raíz
    if exist "Casapro Nexus.exe" (
        echo ============================================================
        echo   BUILD EXITOSO [ONEFILE]
        echo   Ejecutable generado: "Casapro Nexus.exe"
        echo ============================================================
        echo.
        echo Copiando a dist\ para compatibilidad con setup.iss...
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
