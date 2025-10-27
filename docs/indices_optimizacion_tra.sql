-- =====================================================
-- ÍNDICES RECOMENDADOS PARA OPTIMIZACIÓN DE TRA
-- =====================================================
-- Este script crea índices que mejorarán significativamente
-- el rendimiento de las consultas TRA, especialmente
-- para consultas con mayor cantidad de tiempo 
--
--
--}
-- =====================================================

USE [VAD10];  -- REEMPLAZAR con el nombre real
GO

-- =====================================================
-- 1. VERIFICAR ÍNDICES EXISTENTES
-- =====================================================
-- Ejecuta esto primero para ver qué índices ya existen

SELECT 
    OBJECT_NAME(i.object_id) AS NombreTabla,
    i.name AS NombreIndice,
    i.type_desc AS TipoIndice,
    c.name AS Columna,
    ic.key_ordinal AS Posicion
FROM sys.indexes i
INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE OBJECT_NAME(i.object_id) IN ('TR_INVENTARIO', 'MA_PRODUCTOS')
ORDER BY NombreTabla, i.name, ic.key_ordinal;
GO

-- =====================================================
-- 2. ÍNDICE COMPUESTO PRINCIPAL PARA TR_INVENTARIO
-- =====================================================
-- Este es el MÁS IMPORTANTE para TRA
-- Cubre: WHERE f_fecha + c_Deposito + c_Concepto

IF NOT EXISTS (SELECT 1 FROM sys.indexes 
               WHERE name = 'IX_TR_INVENTARIO_TRA_Optimizado' 
               AND object_id = OBJECT_ID('TR_INVENTARIO'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_TR_INVENTARIO_TRA_Optimizado
    ON TR_INVENTARIO (f_fecha, c_Deposito, c_Concepto)
    INCLUDE (c_Codarticulo, n_Cantidad)
    WITH (
        ONLINE = ON,           -- Permite operaciones concurrentes
        FILLFACTOR = 90,       -- 10% de espacio libre para inserts
        SORT_IN_TEMPDB = ON    -- Usa tempdb para ordenamiento
    );
    
    PRINT '✓ Índice IX_TR_INVENTARIO_TRA_Optimizado creado exitosamente';
END
ELSE
BEGIN
    PRINT '⚠ Índice IX_TR_INVENTARIO_TRA_Optimizado ya existe';
END
GO

-- =====================================================
-- 3. ÍNDICE PARA BÚSQUEDA POR CÓDIGO DE ARTÍCULO
-- =====================================================
-- Optimiza JOINs con MA_PRODUCTOS

IF NOT EXISTS (SELECT 1 FROM sys.indexes 
               WHERE name = 'IX_TR_INVENTARIO_Codarticulo' 
               AND object_id = OBJECT_ID('TR_INVENTARIO'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_TR_INVENTARIO_Codarticulo
    ON TR_INVENTARIO (c_Codarticulo)
    INCLUDE (f_fecha, c_Deposito, c_Concepto, n_Cantidad)
    WITH (
        ONLINE = ON,
        FILLFACTOR = 90
    );
    
    PRINT '✓ Índice IX_TR_INVENTARIO_Codarticulo creado exitosamente';
END
ELSE
BEGIN
    PRINT '⚠ Índice IX_TR_INVENTARIO_Codarticulo ya existe';
END
GO

-- =====================================================
-- 4. ÍNDICE PARA MA_PRODUCTOS (si no existe)
-- =====================================================
-- Optimiza el LEFT JOIN en las consultas TRA

IF NOT EXISTS (SELECT 1 FROM sys.indexes 
               WHERE name = 'IX_MA_PRODUCTOS_Codigo_Jerarquia' 
               AND object_id = OBJECT_ID('MA_PRODUCTOS'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_MA_PRODUCTOS_Codigo_Jerarquia
    ON MA_PRODUCTOS (C_CODIGO)
    INCLUDE (C_DESCRI, cu_descripcion_corta, C_DEPARTAMENTO, C_GRUPO, C_SUBGRUPO)
    WITH (
        ONLINE = ON,
        FILLFACTOR = 95    -- Tabla más estable, menos inserts
    );
    
    PRINT '✓ Índice IX_MA_PRODUCTOS_Codigo_Jerarquia creado exitosamente';
END
ELSE
BEGIN
    PRINT '⚠ Índice IX_MA_PRODUCTOS_Codigo_Jerarquia ya existe';
END
GO

-- =====================================================
-- 5. ESTADÍSTICAS DE ÍNDICES (OPCIONAL)
-- =====================================================
-- Actualiza las estadísticas para mejor plan de ejecución

UPDATE STATISTICS TR_INVENTARIO WITH FULLSCAN;
UPDATE STATISTICS MA_PRODUCTOS WITH FULLSCAN;
PRINT '✓ Estadísticas actualizadas';
GO

-- =====================================================
-- 6. VERIFICACIÓN POST-CREACIÓN
-- =====================================================
-- Verifica que los índices se crearon correctamente

SELECT 
    OBJECT_NAME(i.object_id) AS Tabla,
    i.name AS Indice,
    i.type_desc AS Tipo,
    CAST(s.avg_fragmentation_in_percent AS DECIMAL(5,2)) AS Fragmentacion_Pct,
    s.page_count AS Paginas,
    CAST(s.page_count * 8.0 / 1024 AS DECIMAL(10,2)) AS Tamaño_MB
FROM sys.indexes i
INNER JOIN sys.dm_db_index_physical_stats(
    DB_ID(), NULL, NULL, NULL, 'LIMITED'
) s ON i.object_id = s.object_id AND i.index_id = s.index_id
WHERE OBJECT_NAME(i.object_id) IN ('TR_INVENTARIO', 'MA_PRODUCTOS')
    AND i.name LIKE 'IX_%TRA%' OR i.name LIKE 'IX_%Codigo%'
ORDER BY Tabla, Indice;
GO

-- =====================================================
-- 7. ANÁLISIS DE IMPACTO (OPCIONAL - SOLO LECTURA)
-- =====================================================
-- Ve qué consultas se beneficiarán de estos índices

SELECT 
    qt.text AS Consulta,
    qs.execution_count AS Ejecuciones,
    CAST(qs.total_elapsed_time / 1000000.0 AS DECIMAL(10,2)) AS Tiempo_Total_Seg,
    CAST(qs.total_elapsed_time / qs.execution_count / 1000.0 AS DECIMAL(10,2)) AS Tiempo_Promedio_MS
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) qt
WHERE qt.text LIKE '%TR_INVENTARIO%'
    AND qt.text LIKE '%f_fecha%'
ORDER BY qs.total_elapsed_time DESC;
GO

PRINT '';
PRINT '=====================================================';
PRINT '  OPTIMIZACIÓN COMPLETADA';
PRINT '=====================================================';
PRINT 'Índices creados/verificados exitosamente.';
PRINT '';
PRINT '. Monitorea el uso de índices con sys.dm_db_index_usage_stats';
PRINT '. Considera mantenimiento periódico (REBUILD si fragmentación > 30%)';
PRINT '';
GO
