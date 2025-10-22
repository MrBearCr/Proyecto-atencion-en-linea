@echo off
echo ================================
echo  INSTALACION DE SOPORTE EXCEL
echo ================================
echo.
echo Instalando openpyxl para exportacion Excel...
echo.

pip install openpyxl

if %ERRORLEVEL% equ 0 (
    echo.
    echo ================================
    echo  INSTALACION EXITOSA
    echo ================================
    echo.
    echo El soporte para Excel ha sido instalado correctamente.
    echo Ahora puede usar la exportacion Excel en el sistema PAL.
    echo.
    echo Presione cualquier tecla para continuar...
    pause > nul
) else (
    echo.
    echo ================================
    echo  ERROR EN INSTALACION
    echo ================================
    echo.
    echo Hubo un error al instalar openpyxl.
    echo Verifique su conexion a internet e intente nuevamente.
    echo.
    echo Presione cualquier tecla para continuar...
    pause > nul
)