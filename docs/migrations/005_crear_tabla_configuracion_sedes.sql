-- ============================================================================
-- Migración 005: Crear tabla de configuración de sedes
-- Fecha: 2026-01-09
-- Descripción: Crea la tabla 'pal_sedes_configuracion' para almacenar de 
--              forma centralizada los datos de conexión a las bases de datos
--              distribuidas (VAD20) de cada sede.
-- ============================================================================

USE VAD10; -- CAMBIAR POR EL NOMBRE DE TU BD
GO

PRINT 'Iniciando migración 005: Crear tabla de configuración de sedes...';
GO

-- ============================================================================
-- PASO 1: Crear la tabla 'pal_sedes_configuracion'
-- ============================================================================

PRINT 'Paso 1/2: Creando la tabla pal_sedes_configuracion...';

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[pal_sedes_configuracion]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[pal_sedes_configuracion](
        [id] [int] IDENTITY(1,1) NOT NULL,
        [nombre_sede] [nvarchar](100) NOT NULL,
        [ip_servidor] [nvarchar](50) NOT NULL,
        [nombre_bd] [nvarchar](50) NOT NULL,
        [usuario_bd] [nvarchar](100) NOT NULL,
        [password_bd_enc] [nvarchar](512) NULL,
        [activa] [bit] NOT NULL CONSTRAINT [DF_pal_sedes_configuracion_activa] DEFAULT (1),
        [fecha_creacion] [datetime] NOT NULL CONSTRAINT [DF_pal_sedes_configuracion_fecha_creacion] DEFAULT (GETDATE()),
        [fecha_modificacion] [datetime] NOT NULL CONSTRAINT [DF_pal_sedes_configuracion_fecha_modificacion] DEFAULT (GETDATE()),
        CONSTRAINT [PK_pal_sedes_configuracion] PRIMARY KEY CLUSTERED ([id] ASC),
        CONSTRAINT [UQ_pal_sedes_configuracion_nombre_sede] UNIQUE NONCLUSTERED ([nombre_sede] ASC)
    );
    PRINT '  ✓ Tabla pal_sedes_configuracion creada exitosamente.';
END
ELSE
BEGIN
    PRINT '  ℹ Tabla pal_sedes_configuracion ya existe.';
END
GO

-- ============================================================================
-- PASO 2: Insertar datos de ejemplo (opcional)
-- ============================================================================

PRINT 'Paso 2/2: Insertando datos de ejemplo...';

-- Ejemplo para la Sede Central
IF NOT EXISTS (SELECT 1 FROM pal_sedes_configuracion WHERE nombre_sede = N'Sede Central')
BEGIN
    INSERT INTO pal_sedes_configuracion (nombre_sede, ip_servidor, nombre_bd, usuario_bd, password_bd_enc)
    VALUES (N'Sede Central', N'192.168.5.2', N'VAD20', N'report_user', N'--placeholder--');
    PRINT '  ✓ Datos de ejemplo para Sede Central insertados.';
END
ELSE
BEGIN
    PRINT '  ℹ Datos de ejemplo para Sede Central ya existen.';
END

-- Ejemplo para Guanare
IF NOT EXISTS (SELECT 1 FROM pal_sedes_configuracion WHERE nombre_sede = N'Guanare')
BEGIN
    INSERT INTO pal_sedes_configuracion (nombre_sede, ip_servidor, nombre_bd, usuario_bd, password_bd_enc)
    VALUES (N'Guanare', N'192.168.6.2', N'VAD20', N'report_user', N'--placeholder--');
    PRINT '  ✓ Datos de ejemplo para Guanare insertados.';
END
ELSE
BEGIN
    PRINT '  ℹ Datos de ejemplo para Guanare ya existen.';
END
GO

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Contenido de la tabla de configuración de sedes';
PRINT '============================================================================';

SELECT 
    id,
    nombre_sede,
    ip_servidor,
    nombre_bd,
    usuario_bd,
    activa,
    fecha_creacion
FROM pal_sedes_configuracion;

PRINT '';
PRINT 'NOTA: La columna de la contraseña se deja como un placeholder.';
PRINT 'La aplicación deberá gestionar la encriptación y actualización de este campo.';
PRINT '';
PRINT '============================================================================';
PRINT 'Migración 005 completada exitosamente ✓';
PRINT '============================================================================';
GO
