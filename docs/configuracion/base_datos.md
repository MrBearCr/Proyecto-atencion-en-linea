# Configuración de Base de Datos SQL Server

## Versión y Edición

- SQL Server 2019 o posterior (Standard o Enterprise, gestor de base de datos relacional de Microsoft)
- Compatibilidad con SQL Server Express para entornos de desarrollo (versión gratuita con funcionalidades limitadas)

## Esquema de Base de Datos

La base de datos principal (`GestionClientes`) contiene las siguientes tablas principales:

```sql
-- Estructura simplificada de las tablas principales
CREATE TABLE Clientes (
    ClienteID INT PRIMARY KEY IDENTITY(1,1),
    Nombre NVARCHAR(100) NOT NULL,
    Apellido NVARCHAR(100) NOT NULL,
    Email NVARCHAR(150) UNIQUE,
    Telefono NVARCHAR(15),
    FechaRegistro DATETIME DEFAULT GETDATE(),
    UltimaActualizacion DATETIME,
    Activo BIT DEFAULT 1
);

CREATE TABLE MensajesWhatsApp (
    MensajeID INT PRIMARY KEY IDENTITY(1,1),
    ClienteID INT FOREIGN KEY REFERENCES Clientes(ClienteID),
    Contenido NVARCHAR(MAX),
    FechaEnvio DATETIME,
    Estado NVARCHAR(20),
    IDMensajeWhatsApp NVARCHAR(100)
);

CREATE TABLE LogAuditoria (
    LogID INT PRIMARY KEY IDENTITY(1,1),
    UsuarioID INT,
    Accion NVARCHAR(50),
    Tabla NVARCHAR(50),
    Detalle NVARCHAR(MAX),
    FechaHora DATETIME DEFAULT GETDATE(),
    DireccionIP NVARCHAR(50)
);
```

## Procedimientos Almacenados

Se utilizan procedimientos almacenados para todas las operaciones CRUD principales, incluyendo:

- `sp_InsertarCliente`
- `sp_ActualizarCliente`
- `sp_EliminarCliente`
- `sp_ConsultarCliente`
- `sp_RegistrarMensajeWhatsApp`

## Configuración de Conexión

La cadena de conexión (string de configuración para conectar con la base de datos) se estructura de la siguiente manera:

```
Server=nombreServidor;Database=GestionClientes;User Id=usuario;Password=contraseña;Trusted_Connection=False;Encrypt=True;
```

Los parámetros principales son:
- Server: nombre del servidor de base de datos
- Database: nombre de la base de datos a utilizar
- User Id/Password: credenciales de acceso
- Trusted_Connection: indica si se usa autenticación de Windows
- Encrypt: activa el cifrado de conexión

Las credenciales de conexión se almacenan cifradas en el archivo de configuración y se descifran en tiempo de ejecución.

