-- ============================================================================
-- Migración 014: Agregar campo IP secundaria a configuración de sedes
-- Fecha: 2026-07-08
-- Descripción: Agrega el campo 'ip_secundaria' a la tabla 'pal_sedes_configuracion'
--              para permitir fallback automático cuando la IP principal falla.
-- ============================================================================

PRINT 'Paso 1/1: Agregando campo ip_secundaria a pal_sedes_configuracion...';

IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID(N'[dbo].[pal_sedes_configuracion]') 
    AND name = 'ip_secundaria'
)
BEGIN
    ALTER TABLE [dbo].[pal_sedes_configuracion]
    ADD [ip_secundaria] [nvarchar](50) NULL;
    
    PRINT '  ✓ Campo ip_secundaria agregado exitosamente.';
END
ELSE
BEGIN
    PRINT '  ℹ Campo ip_secundaria ya existe.';
END
GO

PRINT '';
PRINT 'Verificación de estructura actual:';
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'pal_sedes_configuracion'
ORDER BY ORDINAL_POSITION;
GO

PRINT '';
PRINT 'Migración 014 completada.';
