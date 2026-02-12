-- ============================================================================
-- Migración 008: Optimización de Índices para Módulo TRA (RI)
-- Fecha: 2026-02-11
-- Descripción: Crea índices no agrupados con prefijo PAL_ en TR_INVENTARIO 
--              y MA_PRODUCTOS para mejorar el rendimiento de consultas.
--              Elimina versiones anteriores sin el prefijo PAL_.
-- ============================================================================

USE VAD10; -- Ajustar según corresponda
GO

PRINT 'Iniciando migración 008: Optimización de Índices PAL...';
GO

-- ============================================================================
-- PASO 1: Limpieza de índices previos (sin prefijo PAL_)
-- ============================================================================

PRINT 'Paso 1/5: Eliminando índices antiguos si existen...';

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_TR_INVENTARIO_TRA_Optimizado' AND object_id = OBJECT_ID('TR_INVENTARIO'))
    DROP INDEX IX_TR_INVENTARIO_TRA_Optimizado ON TR_INVENTARIO;

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_TR_INVENTARIO_Codarticulo' AND object_id = OBJECT_ID('TR_INVENTARIO'))
    DROP INDEX IX_TR_INVENTARIO_Codarticulo ON TR_INVENTARIO;

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_MA_PRODUCTOS_Codigo_Jerarquia' AND object_id = OBJECT_ID('MA_PRODUCTOS'))
    DROP INDEX IX_MA_PRODUCTOS_Codigo_Jerarquia ON MA_PRODUCTOS;

PRINT '  ✓ Limpieza completada';
GO

-- ============================================================================
-- PASO 2: Índice Compuesto en TR_INVENTARIO (Prefijo PAL_)
-- ============================================================================

PRINT 'Paso 2/5: Creando índice PAL_TR_INVENTARIO_TRA...';

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'PAL_TR_INVENTARIO_TRA' AND object_id = OBJECT_ID('TR_INVENTARIO'))
BEGIN
    CREATE NONCLUSTERED INDEX PAL_TR_INVENTARIO_TRA
    ON TR_INVENTARIO (f_fecha, c_Deposito, c_Concepto)
    INCLUDE (c_Codarticulo, n_Cantidad)
    WITH (ONLINE = ON, FILLFACTOR = 90, SORT_IN_TEMPDB = ON);
    PRINT '  ✓ Índice PAL_TR_INVENTARIO_TRA creado';
END
GO

-- ============================================================================
-- PASO 3: Índice por Código en TR_INVENTARIO (Prefijo PAL_)
-- ============================================================================

PRINT 'Paso 3/5: Creando índice PAL_TR_INVENTARIO_Codarticulo...';

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'PAL_TR_INVENTARIO_Codarticulo' AND object_id = OBJECT_ID('TR_INVENTARIO'))
BEGIN
    CREATE NONCLUSTERED INDEX PAL_TR_INVENTARIO_Codarticulo
    ON TR_INVENTARIO (c_Codarticulo)
    INCLUDE (f_fecha, c_Deposito, c_Concepto, n_Cantidad)
    WITH (ONLINE = ON, FILLFACTOR = 90);
    PRINT '  ✓ Índice PAL_TR_INVENTARIO_Codarticulo creado';
END
GO

-- ============================================================================
-- PASO 4: Índice en MA_PRODUCTOS (Jerarquía + Marca + Prefijo PAL_)
-- ============================================================================

PRINT 'Paso 4/5: Creando índice PAL_MA_PRODUCTOS_Jerarquia_Marca...';

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'PAL_MA_PRODUCTOS_Jerarquia_Marca' AND object_id = OBJECT_ID('MA_PRODUCTOS'))
BEGIN
    CREATE NONCLUSTERED INDEX PAL_MA_PRODUCTOS_Jerarquia_Marca
    ON MA_PRODUCTOS (C_CODIGO)
    INCLUDE (C_DESCRI, cu_descripcion_corta, C_DEPARTAMENTO, C_GRUPO, C_SUBGRUPO, c_marca)
    WITH (ONLINE = ON, FILLFACTOR = 95);
    PRINT '  ✓ Índice PAL_MA_PRODUCTOS_Jerarquia_Marca creado';
END
GO

-- ============================================================================
-- PASO 5: Actualización de Estadísticas
-- ============================================================================

PRINT 'Paso 5/5: Actualizando estadísticas...';
UPDATE STATISTICS TR_INVENTARIO WITH FULLSCAN;
UPDATE STATISTICS MA_PRODUCTOS WITH FULLSCAN;
PRINT '  ✓ Estadísticas actualizadas';
GO

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Índices PAL Actualizados';
PRINT '============================================================================';

SELECT 
    OBJECT_NAME(i.object_id) AS Tabla,
    i.name AS Indice,
    i.type_desc AS Tipo
FROM sys.indexes i
WHERE i.name LIKE 'PAL_%'
  AND OBJECT_NAME(i.object_id) IN ('TR_INVENTARIO', 'MA_PRODUCTOS')
ORDER BY Tabla, Indice;

PRINT '';
PRINT 'Migración 008 completada exitosamente ✓';
GO
