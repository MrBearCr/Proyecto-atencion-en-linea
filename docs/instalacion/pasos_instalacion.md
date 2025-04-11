# Guía de Instalación y Despliegue

Esta guía proporciona los pasos necesarios para instalar y configurar el Sistema de Gestión de Clientes en un entorno de producción.

## Preparación del Entorno

1. **Verificación de Requisitos**
   - Confirme que cumple con todos los [requisitos del sistema](./requisitos.md)
   - Prepare los servidores según las especificaciones recomendadas

2. **Configuración del Servidor de Base de Datos**
   - Instale SQL Server 2019+ en el servidor designado
   - Configure las opciones de memoria y almacenamiento según recomendaciones
   - Habilite el protocolo TCP/IP en Configuration Manager
   - Abra el puerto SQL Server (por defecto 1433) en el firewall

3. **Configuración del Servidor Web**
   - Instale el sistema operativo Windows Server con las últimas actualizaciones
   - Habilite el rol de IIS en el servidor
   - Instale los componentes de .NET según la versión utilizada
   - Configure HTTPS con un certificado válido

## Pasos de Instalación

### 1. Preparación de Base de Datos

   ```sql
   -- Ejecutar script de creación de base de datos
   CREATE DATABASE GestionClientes;
   GO
   USE GestionClientes;
   GO
   
   -- Ejecutar scripts de creación de objetos (tablas, procedimientos, etc.)
   -- Ver carpeta /scripts/sql/setup.sql
   ```

   - Ejecute los scripts adicionales para crear usuarios de base de datos
   - Configure backups automáticos y plan de mantenimiento

### 2. Configuración de la Aplicación

   a. Extraiga los archivos de la aplicación en la carpeta del sitio web
   
   b. Modifique el archivo `appsettings.json` con los parámetros específicos:

   ```json
   {
     "ConnectionStrings": {
       "DefaultConnection": "Server=servidor;Database=GestionClientes;User Id=usuario;Password=contraseña;Trusted_Connection=False;Encrypt=True;"
     },
     "WhatsAppAPI": {
       "TokenEndpoint": "https://graph.facebook.com/v13.0/",
       "PhoneNumberId": "su-numero-de-telefono",
       "AccessToken": "token-de-acceso-whatsapp-api"
     },
     "Seguridad": {
       "VectorInicializacion": "vector-inicializacion-base64",
       "SemillaClaveAES": "semilla-clave-aes"
     }
   }
   ```

   c. Verifique permisos en archivos y directorios:
   - Asegure que la cuenta de servicio de IIS tenga permisos adecuados
   - Proteja archivos de configuración con ACLs restrictivas

### 3. Despliegue en IIS

   a. Cree un nuevo sitio web en IIS:
   - Nombre: Gestión de Clientes
   - Ruta física: [ruta a la aplicación]
   - Puerto: 443 (HTTPS)

   b. Configure el certificado SSL para conexión segura

   c. Configure grupo de aplicaciones:
   - Versión de .NET: .NET CLR v4.0 o No Managed Code (para .NET Core)
   - Modo de pipeline: Integrado
   - Identidad: ApplicationPoolIdentity o cuenta específica

   d. Configure los límites de aplicación:
   - Tiempo de espera: 120 segundos
   - Límites de memoria: según recursos disponibles
   - Reciclaje periódico: cada 24 horas en horario de baja actividad

### 4. Configuración de WhatsApp API

   a. Complete el proceso de verificación de negocio en Facebook Business Manager
   
   b. Configure el número de teléfono de WhatsApp Business
   
   c. Cree las plantillas de mensajes necesarias y envíelas para aprobación
   
   d. Configure webhooks para recepción de eventos (opcional)
   
   e. Actualice el token en la configuración de la aplicación

### 5. Configuración de Seguridad Adicional

   a. Configure la auditoría del sistema
   
   b. Establezca políticas de contraseñas
   
   c. Configure firewall para permitir solo conexiones necesarias
   
   d. Implemente monitoreo de seguridad

## Verificación de la Instalación

1. **Pruebas de Conexión**
   - Verifique la conexión a la base de datos
   - Compruebe el acceso a la aplicación web desde la red

2. **Pruebas Func

# Guía de Instalación y Despliegue

## Pasos de Instalación

1. **Preparación de Base de Datos**

   ```sql
   -- Ejecutar script de creación de base de datos
   CREATE DATABASE GestionClientes;
   GO
   USE GestionClientes;
   GO
   
   -- Ejecutar scripts de creación de objetos (tablas, procedimientos, etc.)
   -- Ver carpeta /scripts/sql/setup.sql
   ```

2. **Configuración de la Aplicación**

   a. Modificar el archivo `appsettings.json` con los parámetros específicos:

   ```json
   {
     "ConnectionStrings": {
       "DefaultConnection": "Server=servidor;Database=GestionClientes;Trusted_Connection=True;"
     },
     "WhatsAppAPI": {
       "TokenEndpoint": "https://graph.facebook.com/v13.0/",
       "PhoneNumberId": "su-numero-de-telefono",
       "AccessToken": "token-de-acceso-whatsapp-api"
     },
     "Seguridad": {
       "VectorInicializacion": "vector-inicializacion-base64",
       "SemillaClaveAES": "semilla-clave-aes"
     }
   }
   ```

   b. Verificar permisos en archivos y directorios:
   - Asegurar que la cuenta de servicio tenga permisos adecuados
   - Proteger archivos de configuración con ACLs restrictivas

3. **Despliegue en IIS**

   a. Crear un nuevo sitio web en IIS:
   - Nombre: Gestión de Clientes
   - Ruta física: [ruta a la aplicación]
   - Puerto: 443 (HTTPS)

   b. Configurar certificado SSL para conexión segura

   c. Configurar grupo de aplicaciones:
   - Versión de .NET: .NET CLR v4.0 o No Managed Code (para .NET Core)
   - Modo de pipeline: Integrado
   - Identidad: ApplicationPoolIdentity o cuenta específica

4. **Verificación de la Instalación**

   a. Realizar pruebas de conexión a la base de datos
   b. Verificar envío de mensajes de prueba por WhatsApp
   c. Comprobar registro correcto de eventos de auditoría
   d. Validar funcionamiento del sistema de seguridad y sesiones

## Resolución de Problemas Comunes

- **Error de conexión a base de datos**: Verificar cadena de conexión y credenciales
- **Fallos en envío de WhatsApp**: Comprobar token de acceso y permisos de API
- **Problemas de rendimiento**: Revisar configuración de IIS y recursos de servidor

