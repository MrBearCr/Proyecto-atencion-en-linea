-- ============================================================================
-- Migracion 003: Crear tabla de configuraciones globales
-- Fecha: 2025-12-23
-- Descripcion: Crea la tabla pal_global_settings para almacenar configuraciones
--              que se aplican a toda la aplicacion, como las exclusiones
--              de departamentos.
-- ============================================================================

USE VAD10; -- CAMBIAR POR EL NOMBRE DE TU BD
GO

PRINT 'Iniciando migracion 003: Crear tabla pal_global_settings...';
GO

-- ============================================================================
-- PASO 1: Crear la tabla pal_global_settings
-- ============================================================================

PRINT 'Paso 1/2: Creando la tabla pal_global_settings...';

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='pal_global_settings' and xtype='U')
BEGIN
    CREATE TABLE pal_global_settings (
        setting_key NVARCHAR(100) PRIMARY KEY,
        setting_value NVARCHAR(MAX) NOT NULL,
        description NVARCHAR(255) NULL,
        last_modified DATETIME DEFAULT GETDATE()
    );
    PRINT '  ✓ Tabla pal_global_settings creada';
END
ELSE
BEGIN
    PRINT '  ℹ Tabla pal_global_settings ya existe';
END
GO

-- ============================================================================
-- PASO 2: Insertar el ajuste inicial para exclusiones de departamentos
-- ============================================================================

PRINT 'Paso 2/2: Insertando la configuracion inicial para excluded_depts...';

IF NOT EXISTS (SELECT 1 FROM pal_global_settings WHERE setting_key = N'excluded_depts')
BEGIN
    INSERT INTO pal_global_settings (setting_key, setting_value, description, last_modified)
    VALUES (N'excluded_depts', N'[]', N'Lista de codigos de departamento excluidos globalmente de los reportes.', GETDATE());
    PRINT '  ✓ Configuracion inicial para excluded_depts insertada';
END
ELSE
BEGIN
    PRINT '  ℹ Configuracion para excluded_depts ya existe';
END
GO

-- ============================================================================
-- VERIFICACION: Mostrar la estructura y el contenido inicial de la tabla
-- ============================================================================

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACION: Estructura de la tabla pal_global_settings';
PRINT '============================================================================';

EXEC sp_columns pal_global_settings;

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACION: Contenido inicial de la tabla pal_global_settings';
PRINT '============================================================================';

SELECT * FROM pal_global_settings;

PRINT '';
PRINT '============================================================================';
PRINT 'Migracion 003 completada exitosamente ✓';
PRINT '============================================================================';
GO
