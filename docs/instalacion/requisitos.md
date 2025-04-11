# Requisitos del Sistema

## Entorno de Desarrollo

- **Sistema Operativo**: 
  - Windows 10/11 Professional o Enterprise
  - Windows Server 2019/2022 (recomendado para entorno de producción)

- **Entorno de Desarrollo Integrado (IDE)**:
  - Visual Studio 2022 o posterior
  - Extensiones recomendadas:
    - SQL Server Data Tools
    - Web Essentials
    - ReSharper (opcional)

- **Control de Versiones**:
  - Git 2.30 o posterior
  - Cliente Git compatible (Git Bash, GitHub Desktop, etc.)

- **Lenguajes de Programación**:
  - C# (.NET Framework 4.8 o .NET 6.0+)
  - SQL para procedimientos almacenados y consultas
  - JavaScript/TypeScript para componentes front-end
  - HTML5/CSS3 para interfaces de usuario

## Dependencias y Librerías

| Biblioteca | Versión | Propósito |
|------------|---------|-----------|
| EntityFramework | 6.4.4+ | ORM para acceso a datos (mapeo objeto-relacional) |
| Newtonsoft.Json | 13.0.1+ | Procesamiento de JSON para servicios web y configuración |
| BCrypt.Net | 4.0.2+ | Cifrado seguro de credenciales de usuario |
| WhatsApp.Business.API | 2.1.0+ | Integración con la plataforma de mensajería WhatsApp |
| log4net | 2.0.14+ | Sistema de registro para auditoría y diagnóstico |
| Microsoft.AspNet.Identity | 2.2.3+ | Marco de trabajo para gestión de identidad y sesiones |
| Bootstrap | 5.1.0+ | Framework CSS para interfaz de usuario responsiva |
| jQuery | 3.6.0+ | Biblioteca JavaScript para manipulación DOM y AJAX |

## Requerimientos de Hardware

### Entorno de Desarrollo
- **Procesador**: Intel Core i5/i7 o AMD Ryzen 5/7 (8ª generación o superior)
- **Memoria RAM**: 16GB mínimo
- **Almacenamiento**: 256GB SSD
- **Conectividad**: Internet de banda ancha

### Servidor de Aplicación (Producción)
- **Procesador**: 4 núcleos, 2.5GHz o superior
- **Memoria RAM**: 8GB mínimo, 16GB recomendado
- **Almacenamiento**: 100GB SSD
- **Red**: Conexión de red dedicada, 100Mbps mínimo

### Servidor de Base de Datos (Producción)
- **Procesador**: 8 núcleos, 3.0GHz o superior
- **Memoria RAM**: 16GB mínimo, 32GB recomendado
- **Almacenamiento**: 500GB SSD con configuración RAID para respaldo
- **Red**: Conexión de red dedicada, preferiblemente separada del tráfico de aplicaciones

## Requisitos Previos para Instalación

1. **Base de Datos**:
   - SQL Server 2019 o posterior (Standard o Enterprise)
   - SQL Server Management Studio (SSMS) para administración

2. **Framework y Runtime**:
   - .NET Framework 4.8 Runtime o .NET 6.0+ SDK
   - ASP.NET Core Runtime

3. **Servidor Web**:
   - IIS 10.0+ configurado con el módulo ASP.NET
   - Certificado SSL válido para HTTPS

4. **WhatsApp Business API**:
   - Cuenta de desarrollador de Facebook
   - Número de teléfono verificado para WhatsApp Business
   - Aprobación de plantillas de mensajes (para mensajes iniciales)

5. **Seguridad**:
   - Firewall configurado para permitir conexiones necesarias
   - Antivirus/antimalware actualizado
   - Políticas de seguridad conformes a normativas aplicables

Para instrucciones detalladas sobre la instalación, consulte la [Guía de Instalación](./pasos_instalacion.md).

# Requisitos Técnicos

## Entorno de Desarrollo

- **Sistema Operativo**: Windows 10/11 o Server 2019/2022
- **IDE**: Visual Studio 2022 o posterior
- **Control de Versiones**: Git 2.30 o posterior
- **Lenguajes de Programación**:
  - C# (.NET Framework 4.8 o .NET 6.0+)
  - SQL
  - JavaScript (para componentes front-end)

## Dependencias y Librerías

| Biblioteca | Versión | Propósito |
|------------|---------|-----------|
| EntityFramework | 6.4.4+ | ORM para acceso a datos |
| Newtonsoft.Json | 13.0.1+ | Procesamiento de JSON |
| BCrypt.Net | 4.0.2+ | Cifrado de credenciales |
| WhatsApp.Business.API | 2.1.0+ | Integración con WhatsApp |
| log4net | 2.0.14+ | Sistema de logs para auditoría |
| Microsoft.AspNet.Identity | 2.2.3+ | Manejo de sesiones y autenticación |

## Requerimientos de Hardware Recomendados

- **Servidor de Aplicación**:
  - CPU: 4 núcleos, 2.5GHz o superior
  - RAM: 8GB mínimo, 16GB recomendado
  - Almacenamiento: 100GB SSD

- **Servidor de Base de Datos**:
  - CPU: 8 núcleos, 3.0GHz o superior
  - RAM: 16GB mínimo, 32GB recomendado
  - Almacenamiento: 500GB SSD con respaldo

## Requisitos Previos para Instalación

1. SQL Server 2019+ instalado y configurado
2. .NET Framework 4.8 o .NET 6.0+ instalado
3. IIS 10.0+ configurado (para despliegue en Windows Server)
4. Cuenta de WhatsApp Business API activa

