# Plan de Pruebas para la Migración

## 1. Objetivo

El objetivo de este plan es garantizar que la migración de la aplicación a una nueva arquitectura (backend desacoplado + UI moderna) se realice sin regresiones funcionales. Se busca verificar que toda la lógica de negocio existente y probada en la aplicación actual siga funcionando correctamente después de cada fase de la refactorización.

## 2. Metodología

Adoptaremos un enfoque de **Pruebas de Regresión Basadas en Baseline**.

1.  **Crear un Baseline (Línea Base):** Antes de iniciar la migración, desarrollaremos un conjunto exhaustivo de pruebas que validen el comportamiento actual de la aplicación. Estas pruebas se escribirán contra la estructura de código existente.
2.  **Refactorizar y Adaptar Pruebas:** A medida que cada componente sea refactorizado (por ejemplo, al mover una función de servicio a un endpoint de API), la prueba correspondiente será adaptada para validar el nuevo componente (el endpoint).
3.  **Mantener Pruebas en Verde:** El objetivo es que el conjunto de pruebas se mantenga "en verde" (pasando exitosamente) durante todo el proceso de migración. Una prueba que falle indicará una regresión que debe ser solucionada antes de continuar.

## 3. Herramientas Recomendadas

*   **Framework de Pruebas:** `pytest` (para todo el testing de backend).
*   **Cliente HTTP para Pruebas de API:** `httpx` (para interactuar con los endpoints de FastAPI).
*   **Mocks y Fakes:** `unittest.mock` (incluido en Python) para aislar componentes y simular dependencias.
*   **Pruebas End-to-End (E2E) de UI:** `Playwright` o `Selenium` (para probar la nueva interfaz web).

## 4. Estructura del Directorio de Pruebas

Se creará un nuevo directorio `tests/` en la raíz del proyecto, con una estructura que replique la del paquete `pal/`.

```
/
|-- pal/
|-- tests/
|   |-- __init__.py
|   |-- core/
|   |   |-- test_auth.py
|   |   |-- test_permissions.py
|   |-- services/
|   |   |-- test_exports.py
|   |   |-- test_mbrp.py
|   |-- infrastructure/
|   |   |-- test_database.py
|   |-- api/
|   |   |-- test_endpoints_clientes.py
|   |-- e2e/
|   |   |-- test_login_flow.py
|-- posmigra/
|-- ... (resto de archivos)
```

## 5. Alcance de las Pruebas y Casos de Prueba Clave

A continuación se listan las áreas funcionales críticas a cubrir. Para cada área, se deben desarrollar pruebas unitarias y/o de integración.

### 5.1. Core (Lógica Central)

*   **Módulo:** `pal.core.auth`
    *   `test_login_successful`: Un usuario con credenciales correctas puede iniciar sesión.
    *   `test_login_failed`: Un usuario con credenciales incorrectas no puede iniciar sesión.
    *   `test_password_hashing`: Las contraseñas se hashean correctamente al crear usuarios y se verifican durante el login.
*   **Módulo:** `pal.core.permissions`
    *   `test_user_has_permission`: Verificar que un usuario tiene los permisos asignados.
    *   `test_user_lacks_permission`: Verificar que una comprobación de permisos falla si el usuario no tiene el rol adecuado.
*   **Módulo:** `pal.core.user_management`
    *   `test_create_user`: Se puede crear un nuevo usuario.
    *   `test_delete_user`: Se puede eliminar un usuario.

### 5.2. Services (Lógica de Negocio)

Estas son las pruebas más importantes para evitar regresiones.

*   **Módulo:** `pal.services.exports`
    *   `test_export_to_excel`: Verificar que se genera un archivo Excel con los datos correctos para una entrada dada.
    *   `test_export_filters_applied`: Verificar que la exportación respeta los filtros aplicados.
*   **Módulo:** `pal.services.filters`
    *   `test_filter_logic`: Para cada tipo de filtro, verificar que el conjunto de datos resultante es el esperado.
*   **Módulos de Negocio (`mbrp`, `stock`, `tra`)**
    *   Para cada módulo, identificar las 1-3 funciones más críticas (ej. `calculate_mbrp`, `get_stock_availability`).
    *   `test_module_calculation_correct`: Crear pruebas que validen que los cálculos y procesamientos de datos devuelven resultados conocidos y correctos para un conjunto de datos de entrada fijo.

### 5.3. Infrastructure (Base de Datos)

*   **Módulo:** `pal.infrastructure.database`
    *   `test_db_connection`: Se puede establecer una conexión con la base de datos de prueba.
    *   `test_crud_operations`: Para las tablas más importantes (ej. Clientes, Usuarios), verificar que las operaciones básicas (Crear, Leer, Actualizar, Eliminar) funcionan como se espera.

### 5.4. API Endpoints (Durante la Migración)

A medida que se construya la API con FastAPI, las pruebas de servicios se migrarán a pruebas de API.

*   **Ejemplo para `clientes`:**
    *   `test_get_clientes_success`: Una petición `GET /api/clientes` devuelve un código 200 y una lista de clientes.
    *   `test_get_clientes_unauthorized`: Una petición sin un token de autenticación válido devuelve un código 401 o 403.
    *   `test_create_cliente_validation_error`: Una petición `POST /api/clientes` con datos incompletos devuelve un código 422 (error de validación de FastAPI).

### 5.5. Pruebas End-to-End (Fase Final)

Estas pruebas simularán el flujo de un usuario real en la nueva interfaz.

*   `test_full_login_logout_flow`: El usuario puede abrir la aplicación, iniciar sesión, ver el dashboard y cerrar sesión.
*   `test_generate_mbrp_report_e2e`: El usuario puede navegar a la pestaña MBRP, aplicar filtros, hacer clic en "Generar" y ver el reporte resultante en la pantalla.
*   `test_export_stock_to_excel_e2e`: El usuario puede ir a la pestaña de Stock, aplicar filtros y exportar los datos a un archivo Excel, verificando que el archivo se descarga.

## 6. Plan de Ejecución

1.  **Fase 0: Configuración y Baseline**
    *   [ ] Instalar `pytest` y `pytest-cov` (para medir cobertura).
    *   [ ] Crear la estructura de directorios `tests/`.
    *   [ ] Escribir el conjunto inicial de pruebas unitarias y de integración para los módulos `core` y `services`. **En este punto, todas las pruebas deben pasar.**

2.  **Fase 1: Migración a API**
    *   [ ] Iniciar el desarrollo de la API con FastAPI.
    *   [ ] Por cada función de servicio migrada a un endpoint, convertir su prueba unitaria en una prueba de API.
    *   [ ] Ejecutar continuamente el conjunto de pruebas para asegurar que no hay regresiones.

3.  **Fase 2: Migración de UI y Pruebas E2E**
    *   [ ] Desarrollar la nueva interfaz de usuario.
    *   [ ] Configurar `Playwright` o `Selenium`.
    *   [ ] Escribir los scripts de pruebas E2E que validen los flujos de usuario críticos.
    *   [ ] Ejecutar el conjunto completo de pruebas (unitarias, integración y E2E) antes de cada lanzamiento.
