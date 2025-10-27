# Gestión de Registros

Módulo para administrar clientes y sus productos asociados (tabla `clientes`).

## Operaciones Básicas
- Crear: número de cliente (1-11 dígitos) + código de producto.
- Buscar/Actualizar/Eliminar con filtros por número/código.

```python
import re
from pal.core.errors import ErrorCode

# Validación de número de cliente
def validate_num(num: str):
    if not re.match(r"^\d{1,11}$", num):
        raise ValueError(ErrorCode.INVALID_CLIENT_NUMBER)
```

- Todas las consultas usan parámetros; la UI evita entradas peligrosas.
