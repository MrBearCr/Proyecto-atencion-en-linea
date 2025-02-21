# Gestión de Registros

Módulo para administrar clientes y sus productos asociados.

## Operaciones Básicas
### Crear Registro
1. Ingresar número de cliente (1-11 dígitos)
2. Ingresar código de producto
3. Validación automática:
   - Formato numérico
   - Prevención de SQL injection
4. Click en **💾 Guardar**

```python
# Ejemplo de validación
def validate_input(self):
    if not re.match(r'^\d{1,11}$', self.num_cliente.get()):
        raise ValueError(ErrorCode.INVALID_CLIENT_NUMBER)