# Convenciones de código

## Estilo
- Formato: PEP 8.
- Naming: `snake_case` para variables y funciones, `PascalCase` para clases.
- Imports: Usar imports absolutos (ej. `from pal.services.stock import ...`).

## Terminología de Sedes (Sucursales)
- **Sedes Numéricas**: Representan sucursales físicas individuales de la empresa, específicamente:
  - **01** = Barinas *(Nota: El depósito **0106** es un caso especial, actúa como el Centro de Distribución (CDT) aunque pertenezca a la sede 01).*
  - **03** = Cabudare
  - **04** = Guanare
  - **05** = Araure
- **ICH**: Sigla utilizada para referirse a la **Consulta Global** o consolidado de todas las sedes conjuntas. En el sistema, internamente suele equivaler a "00 - ICH" o al uso del comodín `%`. Representa el inventario y ventas globales de toda la empresa como una sola entidad (Inventory Consolidated Hub / Todas las sedes).
- **TODO / 00**: A menudo sinónimo de ICH en reportes o filtros, indicando que no se excluye ninguna sede del cálculo.


## Patrones que SÍ usamos
- **Normalización de códigos**: `str(value).strip().lstrip('0')` para comparar códigos consistentemente.
- **Batch Processing**: Procesamiento en chunks para consultas grandes en la BD (`for i in range(0, len(codigos), chunk_size):`).
- **Fallback en descripciones**: Si no hay descripción corta, usar larga, si no "SIN DESCRIPCIÓN".
- **Gestión segura de credenciales**: `SecureCredentialsManager` en vez de contraseñas en texto plano.
- **Logging con contexto**: Uso de `get_logger(__name__)` para auditoría y debug.
- **Callbacks para UI**: Uso de callbacks (ej. `progress_cb(i, total)`) para reportar el progreso de operaciones largas.

## Patrones PROHIBIDOS
- **NO almacenar credenciales en texto plano**.
- **NO bloquear la interfaz de usuario**: Usar hilos (Threads/Pools) para consultas pesadas a la BD.
- **NO ignorar validación de conexión a BD**: Siempre usar `ensure_connection()` antes de operar.

## Tests
- Dónde van: Carpeta `tests/`.
- Qué se testea sí o sí: [PENDIENTE: Definir casos críticos obligatorios].

## Commits
- Formato: Conventional Commits (ej. `feat: ...`, `chore: ...`, `fix: ...`).
