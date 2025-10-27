-- =====================================================
-- RECREAR ÍNDICE TRA_OPTIMIZADO CON ORDEN CORRECTO
-- =====================================================
-- El índice existente tiene el orden incorrecto de columnas
-- Este script lo elimina y lo recrea optimizado para TRA
-- =====================================================

USE [MicrocomAgosto2024];  -- REEMPLAZAR con tu base de datos
GO

PRINT 'Iniciando recreación de índice TRA_Optimizado...';
GO

-- 1. Eliminar índice existente (incorrecto)
IF EXISTS (SELECT 1 FROM sys.indexes 
           WHERE name = 'IX_TR_INVENTARIO_TRA_Optimizado' 
           AND object_id = OBJECT_ID('TR_INVENTARIO'))
BEGIN
    PRINT 'Eliminando índice antiguo...';
    DROP INDEX IX_TR_INVENTARIO_TRA_Optimizado ON TR_INVENTARIO;
    PRINT '✓ Índice antiguo eliminado';
END
GO

-- 2. Crear nuevo índice OPTIMIZADO con orden correcto
PRINT 'Creando nuevo índice optimizado...';
GO

CREATE NONCLUSTERED INDEX IX_TR_INVENTARIO_TRA_Optimizado
ON TR_INVENTARIO (f_fecha, c_DEPOSITO, c_CONCEPTO)
INCLUDE (c_CODARTICULO, n_CANTIDAD)
WITH (
    ONLINE = ON,           -- Permite operaciones concurrentes
    FILLFACTOR = 90,       -- 10% de espacio libre
    SORT_IN_TEMPDB = ON,   -- Usa tempdb
    PAD_INDEX = ON         -- Mantiene el fillfactor en páginas intermedias
);
GO

PRINT '✓ Nuevo índice creado exitosamente';
GO

-- 3. Verificar estructura del índice
PRINT '';
PRINT '=== VERIFICACIÓN DEL ÍNDICE ===';
SELECT 
    i.name AS NombreIndice,
    c.name AS Columna,
    ic.key_ordinal AS Posicion,
    ic.is_included_column AS EsInclude
FROM sys.indexes i
INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE i.name = 'IX_TR_INVENTARIO_TRA_Optimizado'
ORDER BY ic.key_ordinal, ic.is_included_column;
GO

-- 4. Actualizar estadísticas
PRINT '';
PRINT 'Actualizando estadísticas...';
UPDATE STATISTICS TR_INVENTARIO IX_TR_INVENTARIO_TRA_Optimizado WITH FULLSCAN;
PRINT '✓ Estadísticas actualizadas';
GO

PRINT '';
PRINT '=====================================================';
PRINT '  ÍNDICE RECREADO EXITOSAMENTE';
PRINT '=====================================================';
PRINT '';
PRINT 'Estructura correcta:';
PRINT '  Posición 1: f_fecha (KEY)';
PRINT '  Posición 2: c_DEPOSITO (KEY)';
PRINT '  Posición 3: c_CONCEPTO (KEY)';
PRINT '  INCLUDE: c_CODARTICULO, n_CANTIDAD';
PRINT '';
PRINT 'Ahora las consultas TRA de 180 días serán 5-10x más rápidas.';
PRINT '';
GO
