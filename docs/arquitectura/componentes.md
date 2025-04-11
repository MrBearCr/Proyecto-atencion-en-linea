# Componentes del Sistema

![Diagrama de Componentes](../../recursos/componentes_diagrama.png)

## Capa de Presentación

La capa de presentación gestiona la interfaz de usuario y la interacción con el usuario final:

- **Interfaz de Usuario Web**: Desarrollada con [HTML5, CSS3 y JavaScript]
  - Formularios de registro y gestión de clientes
  - Panel de administración
  - Visualización de reportes y estadísticas

- **Validación de Datos de Entrada**:
  - Validación del lado del cliente mediante JavaScript
  - Validación del lado del servidor mediante anotaciones de datos
  - Filtrado de entrada para prevenir inyecciones

- **Gestión de Eventos de Usuario**:
  - Captura de eventos mediante controladores
  - Respuestas asíncronas para mejorar la experiencia de usuario

## Capa de Negocio

La capa de negocio contiene la lógica principal del sistema:

- **Procesamiento de Datos de Clientes**:
  - Servicios de gestión de clientes
  - Reglas de negocio para validación de datos
  - Procesamiento de solicitudes y respuestas

- **Módulo de Notificaciones por WhatsApp**:
  - Generación de mensajes personalizados
  - Programación de envíos
  - Gestión de respuestas y estados

- **Servicios de Autenticación y Autorización**:
  - Gestión de identidad de usuarios
  - Control de acceso basado en roles
  - Verificación de permisos para operaciones

- **Motor de Reglas de Negocio**:
  - Definición de reglas configurables
  - Evaluación dinámica de condiciones
  - Aplicación automática de políticas empresariales

## Capa de Datos

La capa de datos maneja el acceso y almacenamiento de información:

- **Acceso a SQL Server**:
  - Repositorios para cada entidad del sistema
  - Mapeo objeto-relacional mediante Entity Framework
  - Procedimientos almacenados para operaciones complejas

- **Gestión de Credenciales**:
  - Almacenamiento seguro de credenciales cifradas
  - Políticas de acceso y restricción

- **Sistema de Logs para Auditoría**:
  - Registro detallado de operaciones
  - Almacenamiento seguro de eventos
  - Consulta y análisis de actividades

## Servicios Externos

El sistema se integra con varios servicios externos:

- **API de WhatsApp Business**:
  - Envío y recepción de mensajes
  - Gestión de plantillas
  - Seguimiento de estados de entrega

- **Servicios de Notificación Adicionales**:
  - Integración con servicios de correo electrónico
  - Notificaciones push (opcional)
  - Alertas SMS (opcional)

## Diagramas de Interacción

### Flujo de Envío de Mensajes
```
Cliente Web → Controlador → Servicio de Mensajes → Repositorio de Clientes
                                    ↓
                             API de WhatsApp → Destinatario
                                    ↓
                            Sistema de Auditoría
```

### Proceso de Autenticación
```
Usuario → Formulario de Login → Controlador de Autenticación → Servicio de Identidad
                                            ↓
                                    Validación de Credenciales
                                            ↓
                                    Generación de Token/Sesión
                                            ↓
                                    Registro en Auditoría
```

Para más detalles sobre la configuración de estos componentes, consulte las secciones de [Configuración](../configuracion/base_datos.md) y [Seguridad](../configuracion/seguridad.md).

