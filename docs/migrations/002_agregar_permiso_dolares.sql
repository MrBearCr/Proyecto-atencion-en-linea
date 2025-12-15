-- ============================================================================
-- Migración 002: Agregar permisos ver_ventas_dolares
-- Fecha: 2025-12-15
-- Descripción: Agrega permisos para ver ventas en dólares
--              en los módulos TRA y MBRP
-- ============================================================================

USE VAD10; 
GO

PRINT 'Iniciando migración 002: Agregar permisos ver_ventas_dolares...';
GO

-- ============================================================================
-- PASO 1: Agregar nuevos permisos a pal_permisos
-- ============================================================================

PRINT 'Paso 1/3: Agregando permisos a pal_permisos...';

-- Verificar y agregar permiso tra.ver_ventas_dolares
IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'tra.ver_ventas_dolares')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'tra.ver_ventas_dolares',
            N'TRA',
            N'Ver ventas y valores en dólares en reportes TRA');
    PRINT '  ✓ Permiso tra.ver_ventas_dolares creado';
END
ELSE
BEGIN
    PRINT '  ℹ Permiso tra.ver_ventas_dolares ya existe';
END

-- Verificar y agregar permiso mbrp.ver_ventas_dolares
IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'mbrp.ver_ventas_dolares')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'mbrp.ver_ventas_dolares',
            N'MBRP',
            N'Ver ventas y valores en dólares en reportes MBRP');
    PRINT '  ✓ Permiso mbrp.ver_ventas_dolares creado';
END
ELSE
BEGIN
    PRINT '  ℹ Permiso mbrp.ver_ventas_dolares ya existe';
END
GO

-- ============================================================================
-- PASO 2: Asignar permisos al rol Administrador
-- ============================================================================

PRINT 'Paso 2/3: Asignando permisos al rol Administrador...';

DECLARE @rol_admin_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Administrador');
DECLARE @perm_tra_dol_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'tra.ver_ventas_dolares');
DECLARE @perm_mbrp_dol_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'mbrp.ver_ventas_dolares');

-- TRA.ver_ventas_dolares -> Administrador
IF @rol_admin_id IS NOT NULL AND @perm_tra_dol_id IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pal_roles_permisos
        WHERE rol_id = @rol_admin_id AND permiso_id = @perm_tra_dol_id
    )
    BEGIN
        INSERT INTO pal_roles_permisos (rol_id, permiso_id)
        VALUES (@rol_admin_id, @perm_tra_dol_id);
        PRINT '  ✓ Permiso TRA.ver_ventas_dolares asignado a Administrador';
    END
    ELSE
    BEGIN
        PRINT '  ℹ Permiso TRA.ver_ventas_dolares ya asignado a Administrador';
    END
END
ELSE
BEGIN
    PRINT '  ⚠ No se encontró rol Administrador o permiso tra.ver_ventas_dolares';
END

-- MBRP.ver_ventas_dolares -> Administrador
IF @rol_admin_id IS NOT NULL AND @perm_mbrp_dol_id IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pal_roles_permisos
        WHERE rol_id = @rol_admin_id AND permiso_id = @perm_mbrp_dol_id
    )
    BEGIN
        INSERT INTO pal_roles_permisos (rol_id, permiso_id)
        VALUES (@rol_admin_id, @perm_mbrp_dol_id);
        PRINT '  ✓ Permiso MBRP.ver_ventas_dolares asignado a Administrador';
    END
    ELSE
    BEGIN
        PRINT '  ℹ Permiso MBRP.ver_ventas_dolares ya asignado a Administrador';
    END
END
ELSE
BEGIN
    PRINT '  ⚠ No se encontró rol Administrador o permiso mbrp.ver_ventas_dolares';
END
GO

-- ============================================================================
-- PASO 3 (OPCIONAL): Asignar permisos al rol Supervisor
-- ============================================================================

PRINT 'Paso 3/3: Asignando permisos al rol Supervisor (opcional)...';

DECLARE @rol_super_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Supervisor');
DECLARE @perm_tra_dol_id_2 INT = (SELECT id FROM pal_permisos WHERE codigo = N'tra.ver_ventas_dolares');
DECLARE @perm_mbrp_dol_id_2 INT = (SELECT id FROM pal_permisos WHERE codigo = N'mbrp.ver_ventas_dolares');

IF @rol_super_id IS NOT NULL
BEGIN
    -- TRA.ver_ventas_dolares -> Supervisor
    IF @perm_tra_dol_id_2 IS NOT NULL
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pal_roles_permisos
            WHERE rol_id = @rol_super_id AND permiso_id = @perm_tra_dol_id_2
        )
        BEGIN
            INSERT INTO pal_roles_permisos (rol_id, permiso_id)
            VALUES (@rol_super_id, @perm_tra_dol_id_2);
            PRINT '  ✓ Permiso TRA.ver_ventas_dolares asignado a Supervisor';
        END
        ELSE
        BEGIN
            PRINT '  ℹ Permiso TRA.ver_ventas_dolares ya asignado a Supervisor';
        END
    END

    -- MBRP.ver_ventas_dolares -> Supervisor
    IF @perm_mbrp_dol_id_2 IS NOT NULL
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pal_roles_permisos
            WHERE rol_id = @rol_super_id AND permiso_id = @perm_mbrp_dol_id_2
        )
        BEGIN
            INSERT INTO pal_roles_permisos (rol_id, permiso_id)
            VALUES (@rol_super_id, @perm_mbrp_dol_id_2);
            PRINT '  ✓ Permiso MBRP.ver_ventas_dolares asignado a Supervisor';
        END
        ELSE
        BEGIN
            PRINT '  ℹ Permiso MBRP.ver_ventas_dolares ya asignado a Supervisor';
        END
    END
END
ELSE
BEGIN
    PRINT '  ⚠ Rol Supervisor no encontrado, saltando asignación';
END
GO

-- ============================================================================
-- VERIFICACIÓN: Mostrar permisos creados y asignaciones
-- ============================================================================

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Permisos ver_ventas_dolares creados';
PRINT '============================================================================';

SELECT
    p.id,
    p.codigo,
    p.modulo,
    p.descripcion
FROM pal_permisos p
WHERE p.codigo IN (
    N'tra.ver_ventas_dolares',
    N'mbrp.ver_ventas_dolares'
);

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Asignaciones de roles para ver_ventas_dolares';
PRINT '============================================================================';

SELECT
    r.nombre AS Rol,
    p.codigo AS Permiso,
    p.descripcion AS Descripcion
FROM pal_roles_permisos rp
INNER JOIN pal_roles r ON rp.rol_id = r.id
INNER JOIN pal_permisos p ON rp.permiso_id = p.id
WHERE p.codigo IN (
    N'tra.ver_ventas_dolares',
    N'mbrp.ver_ventas_dolares'
)
ORDER BY r.nombre, p.codigo;

PRINT '';
PRINT '============================================================================';
PRINT 'Migración 002 completada exitosamente ✓';
PRINT '============================================================================';
GO