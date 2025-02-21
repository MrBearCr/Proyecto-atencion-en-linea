# Arquitectura del Sistema

## Diagrama de Componentes
```mermaid
graph TD
    A[Interfaz Gráfica] --> B[DatabaseManager]
    A --> C[SessionManager]
    A --> D[SecureCredentialsManager]
    B --> E[SQL Server]
    A --> F[WhatsApp API]
    C --> G[System Keyring]

    > **Nota Técnica**: El sistema usa _connection pooling_ para manejar hasta 50 solicitudes concurrentes a la base de datos, optimizando el uso de recursos durante operaciones masivas.