# Decisiones tomadas

> Una entrada por decisión. Lo importante es el "por qué" y el "qué descartamos".

## [2025-04-11] · SQL Crudo vs ORM
- **Decisión:** Usar consultas SQL crudas con `pyodbc` (`DatabaseManager`).
- **Por qué:** Mayor rendimiento y control sobre esquemas legacy complejos de SQL Server, facilidad para crear tablas automáticas (migraciones básicas incorporadas).
- **Descartado:** SQLAlchemy u otro ORM pesado, debido a la sobrecarga y las estructuras legacy de la base de datos (MA_PRODUCTOS, MA_DEPARTAMENTOS).
- **Estado:** Vigente.

## [2025-04-11] · Cifrado en SO vs Archivo Local
- **Decisión:** Almacenar la llave maestra de encriptación en el sistema operativo mediante la librería `keyring`.
- **Por qué:** Para evitar tener el archivo `db_config.ini` con credenciales de SQL Server en texto plano, delegando la seguridad al SO del cliente.
- **Descartado:** Guardar un `.key` en la carpeta o usar variables de entorno locales sin cifrado.
- **Estado:** Vigente.

## [2025-04-11] · Empaquetado con Nuitka
- **Decisión:** Compilar y empaquetar la aplicación usando Nuitka (se refleja en configuración de compilación `setup_nuitka.iss`).
- **Por qué:** Mejor rendimiento, ofuscación de código y empaquetado de dependencias complejas (Tkinter, pyodbc).
- **Descartado:** PyInstaller exclusivamente, se priorizó Nuitka para el binario final (aunque Pyinstaller se use para dependencias secundarias como el updater).
- **Estado:** Vigente.
