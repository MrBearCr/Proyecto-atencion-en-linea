-- ============================================================================
-- Migración 010: Crear tabla de notificaciones persistentes
-- Fecha: 2026-02-17
-- Descripción: Crea la tabla 'pal_notificaciones' para persistir notificaciones
--              críticas (URGENT y WARNING) entre sesiones. Incluye soporte para
--              el campo 'modulo_ruta' que permite al botón "Tratar" redirigir
--              al usuario al módulo que requiere atención.
-- ============================================================================

USE VAD10; -- Ajustar según corresponda
GO

PRINT 'Iniciando migración 010: Crear tabla de notificaciones persistentes...';
GO

-- ============================================================================
-- PASO 1: Crear la tabla pal_notificaciones
-- ============================================================================

PRINT 'Paso 1/3: Creando la tabla pal_notificaciones...';

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[pal_notificaciones]') AND type IN (N'U'))
BEGIN
    CREATE TABLE [dbo].[pal_notificaciones] (
        -- Identificador único de la notificación
        [id]                  NVARCHAR(100)   NOT NULL,

        -- Contenido de la notificación
        [titulo]              NVARCHAR(200)   NOT NULL,
        [mensaje]             NVARCHAR(MAX)   NOT NULL,

        -- Clasificación
        [prioridad]           NVARCHAR(20)    NOT NULL
                              CONSTRAINT [CK_pal_notificaciones_prioridad]
                              CHECK ([prioridad] IN ('urgent', 'warning', 'info', 'success')),
        [modulo]              NVARCHAR(50)    NOT NULL,

        -- Ruta de navegación para el botón "Tratar"
        -- Ejemplos: 'stock', 'tra', 'mbrp', 'clientes', 'sedes_config', NULL
        [modulo_ruta]         NVARCHAR(100)   NULL,

        -- Etiqueta personalizada para el botón de acción (por defecto "Tratar")
        [accion_etiqueta]     NVARCHAR(100)   NOT NULL
                              CONSTRAINT [DF_pal_notificaciones_accion_etiqueta]
                              DEFAULT ('Tratar'),

        -- Datos JSON adicionales (contexto para el módulo destino)
        [datos_json]          NVARCHAR(MAX)   NULL,

        -- Auditoría de estado
        [leida]               BIT             NOT NULL
                              CONSTRAINT [DF_pal_notificaciones_leida]
                              DEFAULT (0),
        [descartada]          BIT             NOT NULL
                              CONSTRAINT [DF_pal_notificaciones_descartada]
                              DEFAULT (0),
        [tratada]             BIT             NOT NULL
                              CONSTRAINT [DF_pal_notificaciones_tratada]
                              DEFAULT (0),

        -- Auditoría de usuario
        [c_usuario]           NVARCHAR(100)   NULL,
        [c_usuario_trato]     NVARCHAR(100)   NULL,

        -- Auditoría temporal
        [f_creacion]          DATETIME        NOT NULL
                              CONSTRAINT [DF_pal_notificaciones_f_creacion]
                              DEFAULT (GETDATE()),
        [f_leida]             DATETIME        NULL,
        [f_tratada]           DATETIME        NULL,
        [f_expiracion]        DATETIME        NULL,

        CONSTRAINT [PK_pal_notificaciones] PRIMARY KEY CLUSTERED ([id] ASC)
    );
    PRINT '  ✓ Tabla pal_notificaciones creada exitosamente.';
END
ELSE
BEGIN
    PRINT '  ℹ Tabla pal_notificaciones ya existe. Verificando columnas nuevas...';

    -- Añadir columna modulo_ruta si no existe (para instancias que ya tenían la tabla)
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('pal_notificaciones') AND name = 'modulo_ruta')
    BEGIN
        ALTER TABLE [dbo].[pal_notificaciones] ADD [modulo_ruta] NVARCHAR(100) NULL;
        PRINT '  ✓ Columna modulo_ruta añadida.';
    END

    -- Añadir columna accion_etiqueta si no existe
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('pal_notificaciones') AND name = 'accion_etiqueta')
    BEGIN
        ALTER TABLE [dbo].[pal_notificaciones]
            ADD [accion_etiqueta] NVARCHAR(100) NOT NULL
            CONSTRAINT [DF_pal_notificaciones_accion_etiqueta] DEFAULT ('Tratar');
        PRINT '  ✓ Columna accion_etiqueta añadida.';
    END

    -- Añadir columna tratada si no existe
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('pal_notificaciones') AND name = 'tratada')
    BEGIN
        ALTER TABLE [dbo].[pal_notificaciones]
            ADD [tratada] BIT NOT NULL
            CONSTRAINT [DF_pal_notificaciones_tratada] DEFAULT (0);
        PRINT '  ✓ Columna tratada añadida.';
    END

    -- Añadir columna c_usuario_trato si no existe
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('pal_notificaciones') AND name = 'c_usuario_trato')
    BEGIN
        ALTER TABLE [dbo].[pal_notificaciones] ADD [c_usuario_trato] NVARCHAR(100) NULL;
        PRINT '  ✓ Columna c_usuario_trato añadida.';
    END

    -- Añadir columna f_tratada si no existe
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('pal_notificaciones') AND name = 'f_tratada')
    BEGIN
        ALTER TABLE [dbo].[pal_notificaciones] ADD [f_tratada] DATETIME NULL;
        PRINT '  ✓ Columna f_tratada añadida.';
    END

    -- Añadir columna datos_json si no existe
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('pal_notificaciones') AND name = 'datos_json')
    BEGIN
        ALTER TABLE [dbo].[pal_notificaciones] ADD [datos_json] NVARCHAR(MAX) NULL;
        PRINT '  ✓ Columna datos_json añadida.';
    END
END
GO

-- ============================================================================
-- PASO 2: Índices de optimización
-- ============================================================================

PRINT 'Paso 2/3: Creando índices de optimización...';

-- Índice para consultas de bandeja: notificaciones activas por usuario
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_pal_notificaciones_bandeja' AND object_id = OBJECT_ID('pal_notificaciones'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_pal_notificaciones_bandeja]
    ON [dbo].[pal_notificaciones] ([leida], [descartada], [tratada], [f_creacion] DESC)
    INCLUDE ([titulo], [prioridad], [modulo], [modulo_ruta], [c_usuario]);
    PRINT '  ✓ Índice IX_pal_notificaciones_bandeja creado.';
END
ELSE
BEGIN
    PRINT '  ℹ Índice IX_pal_notificaciones_bandeja ya existe.';
END

-- Índice para filtrar por prioridad (urgentes primero)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_pal_notificaciones_prioridad' AND object_id = OBJECT_ID('pal_notificaciones'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_pal_notificaciones_prioridad]
    ON [dbo].[pal_notificaciones] ([prioridad], [leida], [descartada])
    INCLUDE ([titulo], [modulo], [f_creacion]);
    PRINT '  ✓ Índice IX_pal_notificaciones_prioridad creado.';
END
ELSE
BEGIN
    PRINT '  ℹ Índice IX_pal_notificaciones_prioridad ya existe.';
END

-- Índice para limpieza automática por fecha de expiración
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_pal_notificaciones_expiracion' AND object_id = OBJECT_ID('pal_notificaciones'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_pal_notificaciones_expiracion]
    ON [dbo].[pal_notificaciones] ([f_expiracion])
    WHERE [f_expiracion] IS NOT NULL;
    PRINT '  ✓ Índice IX_pal_notificaciones_expiracion creado.';
END
ELSE
BEGIN
    PRINT '  ℹ Índice IX_pal_notificaciones_expiracion ya existe.';
END
GO

-- ============================================================================
-- PASO 3: Política de retención — limpieza de notificaciones expiradas
-- ============================================================================

PRINT 'Paso 3/3: Aplicando política de retención inicial...';

-- Eliminar notificaciones INFO/SUCCESS con más de 7 días (si la tabla ya tenía datos)
DELETE FROM [dbo].[pal_notificaciones]
WHERE [prioridad] IN ('info', 'success')
  AND [f_creacion] < DATEADD(DAY, -7, GETDATE());

PRINT '  ✓ Notificaciones INFO/SUCCESS con más de 7 días eliminadas.';

-- Eliminar notificaciones URGENT/WARNING descartadas con más de 30 días
DELETE FROM [dbo].[pal_notificaciones]
WHERE [prioridad] IN ('urgent', 'warning')
  AND [descartada] = 1
  AND [f_creacion] < DATEADD(DAY, -30, GETDATE());

PRINT '  ✓ Notificaciones URGENT/WARNING descartadas con más de 30 días eliminadas.';
GO

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Estructura de la tabla pal_notificaciones';
PRINT '============================================================================';

SELECT
    c.name                          AS columna,
    tp.name                         AS tipo,
    c.max_length                    AS longitud,
    c.is_nullable                   AS acepta_nulo,
    OBJECT_DEFINITION(c.default_object_id) AS valor_defecto
FROM sys.columns c
JOIN sys.types tp ON c.user_type_id = tp.user_type_id
WHERE c.object_id = OBJECT_ID(N'pal_notificaciones')
ORDER BY c.column_id;

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Índices creados';
PRINT '============================================================================';

SELECT
    i.name      AS indice,
    i.type_desc AS tipo
FROM sys.indexes i
WHERE i.object_id = OBJECT_ID(N'pal_notificaciones')
  AND i.name IS NOT NULL
ORDER BY i.index_id;

PRINT '';
PRINT '============================================================================';
PRINT 'Migración 010 completada exitosamente ✓';
PRINT '============================================================================';
PRINT '';
PRINT 'NOTA: La columna [modulo_ruta] almacena el identificador de pestaña/módulo';
PRINT 'al que el botón "Tratar" debe navegar. Valores esperados:';
PRINT '  stock        → Módulo de Inventario / Quiebre de Stock';
PRINT '  tra          → Módulo TRA / Rotación';
PRINT '  mbrp         → Módulo MBRP';
PRINT '  clientes     → Módulo de Clientes';
PRINT '  sedes_config → Configuración de Sedes';
PRINT '  NULL         → Sin navegación (solo informativa)';
GO
