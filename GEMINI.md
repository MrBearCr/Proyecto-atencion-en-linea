# GEMINI.md - Contexto de Instrucción del Proyecto PAL

## Visión General del Proyecto
Este proyecto es una aplicación de escritorio desarrollada en **Python** para la **Gestión de Clientes y Logística (PAL)**. Su propósito principal es administrar eficientemente la información de clientes, el stock global y la cadena de suministro (abastecimiento), integrándose con una base de datos **SQL Server** y proporcionando capacidades de comunicación masiva a través de **WhatsApp**.

### Tecnologías Principales
*   **Lenguaje:** Python 3.x
*   **Interfaz Gráfica (GUI):** Tkinter (con temas modernos y componentes personalizados)
*   **Base de Datos:** SQL Server (mediante `pyodbc`)
*   **Seguridad y Cifrado:** `cryptography` (Fernet), `keyring` (para almacenamiento seguro de claves en el sistema), `bcrypt` (para hashes de contraseñas).
*   **Pruebas:** `pytest`, `pytest-cov`.
*   **Otras:** `requests` (comunicación API), `matplotlib` (gráficos de estadísticas), `Pillow` (manejo de imágenes).

### Arquitectura del Sistema
El proyecto sigue una estructura modular dentro del directorio `pal/`:
*   `pal/core/`: Lógica de negocio fundamental (autenticación, auditoría, gestión de credenciales seguras, licencias, sesiones y actualizaciones).
*   `pal/infrastructure/`: Capa de acceso a datos (`database.py`), manejo de drivers ODBC y esquemas de base de datos.
*   `pal/services/`: Servicios especializados (Abastecimiento, Rotación de inventario TRA/MBRP, Gestión de Stock, Notificaciones de WhatsApp, Exportaciones a Excel).
*   `pal/ui/`: Componentes de la interfaz de usuario (tabs, popups, temas y pantallas de inicio/login).
*   `app.py`: Punto de entrada principal que orquestra la inicialización de la aplicación y el bucle principal de la GUI.

---

## Instalación y Ejecución

### Requisitos Previos
*   Python 3.x instalado.
*   Servidor SQL Server accesible.
*   Driver ODBC de SQL Server instalado (la aplicación detecta automáticamente la mejor versión disponible).

### Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### Configuración de la Base de Datos
La aplicación utiliza un archivo `db_config.ini` en la raíz para almacenar la configuración del servidor, base de datos y usuario. **Importante:** Estos valores se almacenan **encriptados** por motivos de seguridad, utilizando una clave generada dinámicamente y guardada en el `keyring` del sistema operativo.

### Ejecución de la Aplicación
```bash
python app.py
```

---

## Convenciones de Desarrollo

### Seguridad y Credenciales
*   **Nunca** almacenes credenciales en texto plano. Utiliza siempre `SecureCredentialsManager` (`pal/core/credentials.py`) para cifrar/descifrar datos sensibles antes de guardarlos en archivos de configuración.
*   Las contraseñas de usuario en la base de datos se manejan con hashes `bcrypt`.

### Manejo de Base de Datos
*   El `DatabaseManager` (`pal/infrastructure/database.py`) se encarga de la creación automática de tablas y migraciones de esquema al iniciar la conexión.
*   Se utiliza un sistema de pools de conexión por hilo para garantizar que las operaciones en segundo plano (como la carga de datos masivos o alertas) no bloqueen la interfaz de usuario.

### Estilo de Código y Errores
*   Sigue las guías de estilo PEP 8.
*   Utiliza el sistema de códigos de error definido en `pal/core/errors.py` para proporcionar retroalimentación precisa al usuario y facilitar el soporte técnico.
*   Toda acción crítica debe ser registrada a través del `AuditLogger` para mantener un historial de eventos.

### Pruebas
*   Ejecuta las pruebas unitarias utilizando `pytest`.
*   Asegúrate de que las nuevas funcionalidades incluyan sus respectivos casos de prueba en el directorio `tests/`.

---

## Módulos de Negocio Clave
*   **Abastecimiento (`abastecimiento.py`):** Sugerencias de transferencia entre sedes basadas en rotación y stock mínimo.
*   **Rotación de Inventario (TRA/MBRP):** Análisis profundo de ventas y rotación de productos para optimizar el inventario.
*   **Mensajería WhatsApp:** Integración para envío de notificaciones y mensajes programados a clientes.
*   **Exportaciones (`exports.py`):** Generación de reportes complejos en formato Excel con alto rendimiento.
