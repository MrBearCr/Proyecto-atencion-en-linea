# Guía de Instalación

## 1) Requisitos
- Verificar [requisitos](./requisitos.md).
- Instalar Microsoft ODBC Driver for SQL Server.

## 2) Preparar entorno Python
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt  # si existe
# o instalar manualmente
pip install pyodbc tkinter cryptography keyring matplotlib tkcalendar requests win10toast pillow
```

## 3) Configurar conexión y token
- Ejecutar `python app.py` y abrir Settings → Conexión para guardar servidor/BD/usuario.
- En Settings → API WhatsApp, pegar token si se usará mensajería.

## 4) Primer arranque
```powershell
python app.py
```
- La app creará tablas necesarias (clientes, envios_programados, etc.).
- Validar logs y que no aparezcan errores de conexión.

## 5) Problemas comunes
- ODBC Driver faltante: instalar desde Microsoft.
- Token inválido: renovar en Meta y volver a guardar.
- Sin datos de ERP: confirmar permisos de lectura a tablas `MA_PRODUCTOS` y `MA_DEPOPROD`.

