-- ============================================================================
-- Migración 009: Creación de Tabla para Persistencia de Rotación (RI) - v2 (Contextual)
-- Fecha: 2026-02-12
-- Descripción: Crea la tabla pal_productos_rotacion para almacenar el cálculo 
--              ABC y promedios diarios por SEDE y RANGO DE DÍAS.
-- ============================================================================

USE VAD10; -- Ajustar según corresponda
GO

PRINT 'Iniciando migración 009: Creación de Tabla de Rotación PAL (Contextual)...';
GO

-- ============================================================================
-- PASO 1: Creación/Modificación de la Tabla
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[pal_productos_rotacion]') AND type in (N'U'))
BEGIN
    PRINT 'Creando nueva tabla pal_productos_rotacion...';
    CREATE TABLE [dbo].[pal_productos_rotacion] (
        [c_codigo] VARCHAR(20) NOT NULL,
        [c_sede] VARCHAR(10) NOT NULL,
        [n_dias_rango] INT NOT NULL,
        [n_neto] FLOAT DEFAULT 0,
        [n_promedio_diario] FLOAT DEFAULT 0,
        [n_porcentaje_representacion] FLOAT DEFAULT 0,
        [c_clasificacion] VARCHAR(10),
        [f_ultima_actualizacion] DATETIME DEFAULT GETDATE(),
        [c_usuario_nodo] VARCHAR(100),
        CONSTRAINT [PK_pal_productos_rotacion] PRIMARY KEY CLUSTERED 
        (
            [c_codigo] ASC,
            [c_sede] ASC,
            [n_dias_rango] ASC
        )
    );
END
ELSE
BEGIN
    PRINT 'La tabla ya existe, verificando columnas para contexto...';
    -- Añadir c_sede si no existe
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('pal_productos_rotacion') AND name = 'c_sede')
    BEGIN
        -- Si ya hay datos, primero limpiamos para poder cambiar la PK
        DELETE FROM pal_productos_rotacion;
        
        -- Intentar quitar la PK antigua si existe
        DECLARE @PKName nvarchar(200);
        SELECT @PKName = name FROM sys.key_constraints WHERE type = 'PK' AND parent_object_id = OBJECT_ID('pal_productos_rotacion');
        IF @PKName IS NOT NULL EXEC('ALTER TABLE pal_productos_rotacion DROP CONSTRAINT ' + @PKName);

        ALTER TABLE pal_productos_rotacion ADD [c_sede] VARCHAR(10) NOT NULL DEFAULT 'GLOBAL';
        ALTER TABLE pal_productos_rotacion ADD [n_dias_rango] INT NOT NULL DEFAULT 365;
        
        -- Crear nueva PK compuesta
        ALTER TABLE pal_productos_rotacion ADD CONSTRAINT [PK_pal_productos_rotacion] PRIMARY KEY CLUSTERED ([c_codigo], [c_sede], [n_dias_rango]);
        PRINT '  ✓ Contexto de Sede y Rango añadido a la tabla';
    END
END
GO

-- ============================================================================
-- PASO 2: Índices de Optimización
-- ============================================================================

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_pal_rotacion_clasificacion' AND object_id = OBJECT_ID('pal_productos_rotacion'))
    DROP INDEX IX_pal_rotacion_clasificacion ON pal_productos_rotacion;

CREATE NONCLUSTERED INDEX IX_pal_rotacion_contexto
ON [dbo].[pal_productos_rotacion] ([c_sede], [n_dias_rango], [c_clasificacion])
INCLUDE ([c_codigo], [n_promedio_diario]);
GO

PRINT 'Migración 009 v2 completada exitosamente ✓';
GO
