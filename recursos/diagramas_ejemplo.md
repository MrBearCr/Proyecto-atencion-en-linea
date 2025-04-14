# Ejemplos de Diagramas Renderizados

A continuacion se muestran ejemplos de como deberían verse los diagramas después de ser renderizados a PNG utilizando Mermaid.

## Arquitectura del Sistema

```mermaid
graph TD
    subgraph "Capa de Presentacion"
        A[Interfaz Web]
        B[Formularios]
        C[Panel Admin]
    end
    
    subgraph "Capa de Negocio"
        D[Servicios]
        E[Logica de Negocio]
        F[Gestion de Mensajes]
    end
    
    subgraph "Capa de Datos"
        G[Acceso a Datos]
        H[(SQL Server)]
    end
    
    subgraph "Servicios Externos"
        I[API WhatsApp]
    end
    
    A --> B
    A --> C
    B --> D
    C --> D
    D --> E
    E --> F
    D --> G
    E --> G
    F --> G
    F --> I
    G --> H
```

## Flujo de Mensajes

```mermaid
sequenceDiagram
    Cliente->>Sistema: Solicita envío
    Sistema->>Base de Datos: Verifica datos
    Base de Datos-->>Sistema: Retorna informacion
    Sistema->>WhatsApp API: Envía mensaje
    WhatsApp API-->>Sistema: Confirma recepcion
    Sistema->>Auditoría: Registra operacion
    Sistema-->>Cliente: Muestra confirmacion
```

Los diagramas reales deben ser convertidos a PNG siguiendo las instrucciones en [nota_conversion.md](nota_conversion.md) y luego referenciados en la documentación.

