## Configuración de Base de Datos

1. Crear archivo `db_config.ini`:
```ini
[Database]
server = <valor_cifrado>
database = <valor_cifrado>
user = <valor_cifrado>

# Arquitectura de Base de Datos

## Clase DatabaseManager (db/manager.py)
```python
class DatabaseManager:
    def __init__(self):
        self.conn: pyodbc.Connection = None
        self.cursor: pyodbc.Cursor = None
        self.config = configparser.ConfigParser()
        
    def connect(self, server, database, user, password):
        conn_str = f"DRIVER={{SQL Server}};SERVER={server};"
        if database:
            conn_str += f"DATABASE={database};"
        # ... lógica de conexión ...
```