# Arquitectura del Sistema

## Diagrama de Componentes
```mermaid
graph TD
    subgraph UI
        A[Interfaz Gráfica]
    end

    subgraph Backend
        B[DatabaseManager]
        C[SessionManager]
        D[SecureCredentialsManager]
        H[AuditLogger]
    end

    subgraph Storage
        E[SQL Server]
        I[TEMP_ENVIO]
    end

    subgraph External
        F[WhatsApp API]
        G[System Keyring]
    end

    A -->|Maneja sesión| C
    A -->|Encripta credenciales| D
    A -->|Consulta DB| B
    A -->|Envía logs| H
    B -->|Accede| E
    B -->|Usa| I
    C -->|Guarda sesión| G
    D -->|Guarda credenciales| G
    D -->|Accede a token| F
    B -->|Envía datos| F
    H -->|Registra eventos| E

```
    
```   
> **Nota Técnica**: El sistema usa _connection pooling_ para manejar hasta 50 solicitudes 
concurrentes a la base de datos, optimizando el uso de recursos durante operaciones masivas.
```