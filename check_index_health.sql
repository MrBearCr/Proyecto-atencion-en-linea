
-- SQL Script para chequear la salud de los índices en SQL Server

-- Este script proporciona varias consultas para identificar problemas comunes de salud de índices:
-- 1. Fragmentación de índices
-- 2. Índices no utilizados (estadísticas de uso)
-- 3. Índices duplicados o redundantes

-- ====================================================================================
-- SECCIÓN 1: CHEQUEAR FRAGMENTACIÓN DE ÍNDICES
-- La fragmentación puede degradar seriamente el rendimiento de las consultas.
-- Un porcentaje de fragmentación superior al 30% generalmente requiere reconstrucción,
-- entre 5% y 30% puede requerir reorganización.
-- ====================================================================================
SELECT
    OBJECT_NAME(ips.object_id) AS TableName,
    i.name AS IndexName,
    ips.index_type_desc,
    ips.avg_fragmentation_in_percent,
    ips.page_count
FROM
    sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') AS ips
INNER JOIN
    sys.indexes AS i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
WHERE
    ips.avg_fragmentation_in_percent > 5 -- Solo mostrar índices con más del 5% de fragmentación
    AND ips.index_id > 0 -- Excluir montones (heaps)
ORDER BY
    ips.avg_fragmentation_in_percent DESC;

-- Acciones recomendadas:
-- ALTER INDEX [IndexName] ON [TableName] REORGANIZE; (para fragmentación entre 5-30%)
-- ALTER INDEX [IndexName] ON [TableName] REBUILD; (para fragmentación > 30%)
-- ALTER INDEX ALL ON [TableName] REBUILD; (para reconstruir todos los índices de una tabla)
-- ALTER DATABASE CURRENT SET RECOVERY SIMPLE; (si se hace un REBUILD offline en una base de datos muy grande)

-- ====================================================================================
-- SECCIÓN 2: CHEQUEAR ÍNDICES NO UTILIZADOS
-- Los índices no utilizados consumen espacio en disco y recursos (CPU/IO)
-- durante las operaciones DML (INSERT, UPDATE, DELETE).
-- ====================================================================================
SELECT
    OBJECT_NAME(s.object_id) AS TableName,
    i.name AS IndexName,
    i.type_desc AS IndexType,
    s.user_seeks,
    s.user_scans,
    s.user_lookups,
    s.user_updates,
    s.last_user_seek,
    s.last_user_scan,
    s.last_user_lookup,
    s.last_user_update
FROM
    sys.dm_db_index_usage_stats AS s
INNER JOIN
    sys.indexes AS i ON s.object_id = i.object_id AND s.index_id = i.index_id
WHERE
    OBJECTPROPERTY(s.object_id, 'IsUserTable') = 1
    AND i.name IS NOT NULL
    AND s.database_id = DB_ID()
    AND s.user_seeks = 0
    AND s.user_scans = 0
    AND s.user_lookups = 0
ORDER BY
    s.user_updates DESC; -- Ordenar por actualizaciones (costo de mantener el índice)

-- Interpretación:
-- user_seeks, user_scans, user_lookups: Indican lecturas del índice.
-- user_updates: Indican escrituras en el índice (INSERT, UPDATE, DELETE).
-- Si user_seeks, user_scans y user_lookups son 0 y user_updates es alto,
-- el índice es un candidato para eliminación, ya que solo añade sobrecarga.

-- Acciones recomendadas:
-- DROP INDEX [IndexName] ON [TableName];
-- Considerar la eliminación después de un período de monitoreo, ya que
-- las estadísticas se restablecen al reiniciar el servicio o al reconstruir el índice.

-- ====================================================================================
-- SECCIÓN 3: CHEQUEAR ÍNDICES DUPLICADOS O REDUNDANTES
-- Los índices duplicados son aquellos que tienen exactamente las mismas columnas clave
-- y de inclusión (si las hay). Los redundantes son subconjuntos de otros índices.
-- ====================================================================================
WITH IndexColumns AS (
    SELECT
        ic.object_id,
        ic.index_id,
        i.name AS IndexName,
        i.type_desc,
        STUFF((
            SELECT ',' + c.name + CASE WHEN ic2.is_descending_key = 1 THEN ' DESC' ELSE '' END
            FROM sys.index_columns AS ic2
            INNER JOIN sys.columns AS c ON ic2.object_id = c.object_id AND ic2.column_id = c.column_id
            WHERE ic2.object_id = ic.object_id AND ic2.index_id = ic.index_id AND ic2.is_included_column = 0
            ORDER BY ic2.key_ordinal
            FOR XML PATH('')
        ), 1, 1, '') AS KeyColumns,
        STUFF((
            SELECT ',' + c.name
            FROM sys.index_columns AS ic2
            INNER JOIN sys.columns AS c ON ic2.object_id = c.object_id AND ic2.column_id = c.column_id
            WHERE ic2.object_id = ic.object_id AND ic2.index_id = ic.index_id AND ic2.is_included_column = 1
            ORDER BY ic2.column_id
            FOR XML PATH('')
        ), 1, 1, '') AS IncludedColumns
    FROM
        sys.index_columns AS ic
    INNER JOIN
        sys.indexes AS i ON ic.object_id = i.object_id AND ic.index_id = i.index_id
    WHERE i.is_primary_key = 0 AND i.is_unique_constraint = 0 -- Excluir PKs y Unique Constraints
    GROUP BY ic.object_id, ic.index_id, i.name, i.type_desc
)
SELECT
    OBJECT_NAME(ic1.object_id) AS TableName,
    ic1.IndexName AS Index1,
    ic2.IndexName AS Index2,
    ic1.KeyColumns,
    ic1.IncludedColumns
FROM
    IndexColumns AS ic1
INNER JOIN
    IndexColumns AS ic2 ON ic1.object_id = ic2.object_id
                        AND ic1.index_id < ic2.index_id -- Para evitar duplicados y compararse a sí mismo
                        AND ic1.KeyColumns = ic2.KeyColumns
                        AND ISNULL(ic1.IncludedColumns, '') = ISNULL(ic2.IncludedColumns, '')
WHERE ic1.KeyColumns IS NOT NULL
ORDER BY TableName, KeyColumns;

-- Interpretación:
-- Esta consulta busca índices que tienen las mismas KeyColumns y las mismas IncludedColumns.
-- Si un índice secundario (no PK/UNIQUE) es idéntico a otro, uno de ellos es redundante.
-- Si un índice A tiene las columnas (col1, col2) y un índice B tiene (col1, col2, col3),
-- el índice A es redundante para cualquier consulta que pueda usar el índice B
-- siempre que la consulta solo necesite col1 y col2. Sin embargo, esta consulta solo
-- detecta duplicados exactos. La detección de redundancia parcial es más compleja
-- y a menudo requiere un análisis del plan de ejecución.

-- Acciones recomendadas:
-- DROP INDEX [Index2Name] ON [TableName]; (Eliminar el duplicado menos utilizado o más nuevo)
-- Siempre verificar el impacto antes de eliminar índices.
-- ====================================================================================
