# Sistema de Gestión de Errores

## Estructura de la Clase ErrorCode
```python
class ErrorCode(Enum):
    DB_CONNECTION_FAILED = (1001, "Error de conexión a la base de datos")
    
    def __init__(self, code, description):
        self.code = code
        self.description = description
        
    def __str__(self):
        return f"[{self.code}] {self.description}"
```

| Código | Tipo                  | Descripción                                      | Posibles Soluciones                  |
|--------|-----------------------|-------------------------------------------------|---------------------------------------|
| 1001   | Base de Datos         | Error de conexión a la base de datos            | Verificar credenciales y servidor    |
| 1002   | Base de Datos         | Error al ejecutar consulta SQL                  | Revisar sintaxis SQL                 |
| 2001   | Validación            | Número de cliente inválido                      | Usar solo números (1-11 dígitos)     |
| 2003   | Validación            | Entrada con caracteres peligrosos               | Evitar caracteres especiales         |
| 3001   | Cifrado               | Error al cifrar datos                           | Verificar clave de cifrado           |
| 4002   | API                   | Token de API inválido o expirado                | Actualizar token en configuración    |
| 5002   | Sesión                | Sesión expirada por inactividad                 | Reingresar al sistema                |
| 6001   | Configuración         | Configuración faltante                          | Verificar archivo de configuración   |