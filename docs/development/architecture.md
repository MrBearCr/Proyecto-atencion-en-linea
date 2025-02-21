# Arquitectura del Sistema


## Diagrama de Componentes
```mermaid
graph TD
    %% Secciones del sistema %%
    subgraph UI
        A[Interfaz Gráfica]
        A1[TreeView UI]
        A2[Notificaciones]
    end

    subgraph Backend
        B[DatabaseManager]
        C[SessionManager]
        D[SecureCredentialsManager]
        H[AuditLogger]
        J[ConfigManager]
        K[NotificationManager]
        L[ErrorCode]
    end

    subgraph Storage
        E[SQL Server]
        I[TEMP_ENVIO]
        M[db_config.ini]
    end

    subgraph External
        F[WhatsApp API]
        G[System Keyring]
    end

    %% Conexiones entre componentes %%
    A -->|Maneja sesión| C
    A -->|Encripta credenciales| D
    A -->|Consulta DB| B
    A -->|Muestra errores| K
    A -->|Carga Configuración| J
    A1 -->|Carga datos desde| B
    A2 -->|Muestra alertas| K
    A -->|Envía logs| H

    B -->|Accede| E
    B -->|Usa| I
    B -->|Lee Configuración| M
    B -->|Notifica errores| L
    B -->|Envía datos| F

    C -->|Guarda sesión| G
    D -->|Guarda credenciales| G
    D -->|Accede a token| F

    H -->|Registra eventos| E
    J -->|Lee y escribe en| M
    K -->|Muestra errores y alertas| A2
    L -->|Proporciona códigos de error| K
    #	modified:   docs/development/architecture.md

```
    
```   
> **Nota Técnica**: El sistema usa _connection pooling_ para manejar hasta 50 solicitudes 
concurrentes a la base de datos, optimizando el uso de recursos durante operaciones masivas.
```
