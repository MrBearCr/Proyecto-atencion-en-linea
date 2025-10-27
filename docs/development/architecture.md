# Arquitectura del Sistema

## Diagrama de Componentes (actual)
```mermaid
graph TD
    subgraph UI [Capa de Presentación (Tkinter)]
        U1[pal.ui.header]
        U2[pal.ui.sidebar]
        U3[pal.ui.tabs.*]
        U4[pal.ui.splash]
    end

    subgraph Core [Capa de Núcleo]
        C1[pal.core.session.SessionManager]
        C2[pal.core.credentials.SecureCredentialsManager]
        C3[pal.core.errors.ErrorCode]
        C4[pal.core.audit.AuditLogger]
        C5[pal.core.log]
    end

    subgraph Services [Capa de Servicios]
        S1[pal.services.stock]
        S2[pal.services.tra]
        S3[pal.services.mbrp]
        S4[pal.services.filters]
        S5[pal.services.envios]
        S6[pal.services.cache]
    end

    subgraph Infra [Infraestructura]
        I1[pal.infrastructure.database.DatabaseManager]
    end

    subgraph External [Servicios Externos]
        E1[SQL Server]
        E2[WhatsApp Graph API]
        E3[Windows Keyring]
    end

    U3 --> S1
    U3 --> S2
    U3 --> S3
    U1 --> C5
    U2 --> C5
    U3 --> C1
    C1 --> C2
    C2 --> E3
    S5 --> E2
    I1 --> E1
    S1 --> I1
    S2 --> I1
    S3 --> I1
    C4 --> I1
```

- app.py orquesta la inicialización (splash, sesión, UI, programador de envíos) y delega en módulos pal/*.
- Los servicios encapsulan lógica de dominio (stock/TRA/MBRP) y reutilizan filtros unificados.
- DatabaseManager usa pyodbc y validación de estado de conexión; credenciales/token se guardan con keyring + Fernet.
