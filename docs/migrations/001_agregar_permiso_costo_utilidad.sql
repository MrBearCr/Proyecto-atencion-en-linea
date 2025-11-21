-- ============================================================================
-- Migración 001: Agregar permisos ver_costo_utilidad
-- Fecha: 2025-01-14
-- Descripción: Agrega permisos granulares para ver información de costo y 
--              utilidad en reportes TRA, MBRP y Stock
-- ============================================================================

USE VAD10; -- CAMBIAR POR EL NOMBRE DE TU BD
GO

PRINT 'Iniciando migración 001: Agregar permisos ver_costo_utilidad...';
GO

-- ============================================================================
-- PASO 1: Agregar nuevos permisos a pal_permisos
-- ============================================================================

PRINT 'Paso 1/3: Agregando permisos a pal_permisos...';

-- Verificar y agregar permiso TRA.ver_costo_utilidad
IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'tra.ver_costo_utilidad')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'tra.ver_costo_utilidad', N'TRA', N'Ver costo y utilidad en reportes');
    PRINT '  ✓ Permiso tra.ver_costo_utilidad creado';
END
ELSE
BEGIN
    PRINT '  ℹ Permiso tra.ver_costo_utilidad ya existe';
END

-- Verificar y agregar permiso MBRP.ver_costo_utilidad
IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'mbrp.ver_costo_utilidad')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'mbrp.ver_costo_utilidad', N'MBRP', N'Ver costo y utilidad en reportes');
    PRINT '  ✓ Permiso mbrp.ver_costo_utilidad creado';
END
ELSE
BEGIN
    PRINT '  ℹ Permiso mbrp.ver_costo_utilidad ya existe';
END

-- Verificar y agregar permiso STOCK.ver_costo_utilidad
IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'stock.ver_costo_utilidad')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'stock.ver_costo_utilidad', N'STOCK', N'Ver costo y utilidad en reportes');
    PRINT '  ✓ Permiso stock.ver_costo_utilidad creado';
END
ELSE
BEGIN
    PRINT '  ℹ Permiso stock.ver_costo_utilidad ya existe';
END
GO

-- ============================================================================
-- PASO 2: Asignar permisos al rol Administrador (todos los permisos por defecto)
-- ============================================================================

PRINT 'Paso 2/3: Asignando permisos al rol Administrador...';

DECLARE @rol_admin_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Administrador');
DECLARE @perm_tra_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'tra.ver_costo_utilidad');
DECLARE @perm_mbrp_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'mbrp.ver_costo_utilidad');
DECLARE @perm_stock_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'stock.ver_costo_utilidad');

-- TRA
IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_admin_id AND permiso_id = @perm_tra_id)
BEGIN
    INSERT INTO pal_roles_permisos (rol_id, permiso_id)
    VALUES (@rol_admin_id, @perm_tra_id);
    PRINT '  ✓ Permiso TRA asignado a Administrador';
END
ELSE
    PRINT '  ℹ Permiso TRA ya asignado a Administrador';

-- MBRP
IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_admin_id AND permiso_id = @perm_mbrp_id)
BEGIN
    INSERT INTO pal_roles_permisos (rol_id, permiso_id)
    VALUES (@rol_admin_id, @perm_mbrp_id);
    PRINT '  ✓ Permiso MBRP asignado a Administrador';
END
ELSE
    PRINT '  ℹ Permiso MBRP ya asignado a Administrador';

-- STOCK
IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_admin_id AND permiso_id = @perm_stock_id)
BEGIN
    INSERT INTO pal_roles_permisos (rol_id, permiso_id)
    VALUES (@rol_admin_id, @perm_stock_id);
    PRINT '  ✓ Permiso STOCK asignado a Administrador';
END
ELSE
    PRINT '  ℹ Permiso STOCK ya asignado a Administrador';

GO

-- ============================================================================
-- PASO 3 (OPCIONAL): Asignar permisos al rol Supervisor
-- ============================================================================

PRINT 'Paso 3/3: Asignando permisos al rol Supervisor (opcional)...';

DECLARE @rol_super_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Supervisor');
DECLARE @perm_tra_id_2 INT = (SELECT id FROM pal_permisos WHERE codigo = N'tra.ver_costo_utilidad');
DECLARE @perm_mbrp_id_2 INT = (SELECT id FROM pal_permisos WHERE codigo = N'mbrp.ver_costo_utilidad');
DECLARE @perm_stock_id_2 INT = (SELECT id FROM pal_permisos WHERE codigo = N'stock.ver_costo_utilidad');

IF @rol_super_id IS NOT NULL
BEGIN
    -- TRA
    IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_super_id AND permiso_id = @perm_tra_id_2)
    BEGIN
        INSERT INTO pal_roles_permisos (rol_id, permiso_id)
        VALUES (@rol_super_id, @perm_tra_id_2);
        PRINT '  ✓ Permiso TRA asignado a Supervisor';
    END
    ELSE
        PRINT '  ℹ Permiso TRA ya asignado a Supervisor';

    -- MBRP
    IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_super_id AND permiso_id = @perm_mbrp_id_2)
    BEGIN
        INSERT INTO pal_roles_permisos (rol_id, permiso_id)
        VALUES (@rol_super_id, @perm_mbrp_id_2);
        PRINT '  ✓ Permiso MBRP asignado a Supervisor';
    END
    ELSE
        PRINT '  ℹ Permiso MBRP ya asignado a Supervisor';

    -- STOCK
    IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_super_id AND permiso_id = @perm_stock_id_2)
    BEGIN
        INSERT INTO pal_roles_permisos (rol_id, permiso_id)
        VALUES (@rol_super_id, @perm_stock_id_2);
        PRINT '  ✓ Permiso STOCK asignado a Supervisor';
    END
    ELSE
        PRINT '  ℹ Permiso STOCK ya asignado a Supervisor';
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
PRINT 'VERIFICACIÓN: Permisos creados';
PRINT '============================================================================';

SELECT 
    p.id,
    p.codigo,
    p.modulo,
    p.descripcion
FROM pal_permisos p
WHERE p.codigo IN (
    N'tra.ver_costo_utilidad', 
    N'mbrp.ver_costo_utilidad', 
    N'stock.ver_costo_utilidad'
);

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Asignaciones de roles';
PRINT '============================================================================';

SELECT 
    r.nombre AS Rol,
    p.codigo AS Permiso,
    p.descripcion AS Descripcion
FROM pal_roles_permisos rp
INNER JOIN pal_roles r ON rp.rol_id = r.id
INNER JOIN pal_permisos p ON rp.permiso_id = p.id
WHERE p.codigo IN (
    N'tra.ver_costo_utilidad', 
    N'mbrp.ver_costo_utilidad', 
    N'stock.ver_costo_utilidad'
)
ORDER BY r.nombre, p.codigo;

PRINT '';
PRINT '============================================================================';
PRINT 'Migración 001 completada exitosamente ✓';
PRINT '============================================================================';
GO
