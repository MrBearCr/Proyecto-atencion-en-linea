-- ============================================================================
-- Migración 007: Agregar permisos para ver proveedores en RI y MBRP
-- Fecha: 2026-02-04
-- Descripción: Agrega permisos 'tra.ver_proveedores' y 'mbrp.ver_proveedores'
--              para habilitar el menú contextual de visualización de proveedores.
-- ============================================================================

USE VAD10; 
GO

PRINT 'Iniciando migración 007: Agregar permisos ver_proveedores...';
GO

-- ============================================================================
-- PASO 1: Agregar nuevos permisos a pal_permisos
-- ============================================================================

PRINT 'Paso 1/2: Agregando permisos a pal_permisos...';

-- Permiso para TRA (RI)
IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'tra.ver_proveedores')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'tra.ver_proveedores',
            N'TRA',
            N'Ver proveedores asociados a un producto en módulo RI');
    PRINT '  ✓ Permiso tra.ver_proveedores creado';
END
ELSE
BEGIN
    PRINT '  ℹ Permiso tra.ver_proveedores ya existe';
END

-- Permiso para MBRP
IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'mbrp.ver_proveedores')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'mbrp.ver_proveedores',
            N'MBRP',
            N'Ver proveedores asociados a un producto en módulo MBRP');
    PRINT '  ✓ Permiso mbrp.ver_proveedores creado';
END
ELSE
BEGIN
    PRINT '  ℹ Permiso mbrp.ver_proveedores ya existe';
END
GO

-- ============================================================================
-- PASO 2: Asignar permisos a roles (Administrador y Supervisor)
-- ============================================================================

PRINT 'Paso 2/2: Asignando permisos a roles...';

DECLARE @rol_admin_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Administrador');
DECLARE @rol_super_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Supervisor');

-- Asignar tra.ver_proveedores
DECLARE @perm_tra_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'tra.ver_proveedores');
IF @perm_tra_id IS NOT NULL
BEGIN
    IF @rol_admin_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_admin_id AND permiso_id = @perm_tra_id)
        INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (@rol_admin_id, @perm_tra_id);
    
    IF @rol_super_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_super_id AND permiso_id = @perm_tra_id)
        INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (@rol_super_id, @perm_tra_id);
    
    PRINT '  ✓ Permiso tra.ver_proveedores asignado';
END

-- Asignar mbrp.ver_proveedores
DECLARE @perm_mbrp_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'mbrp.ver_proveedores');
IF @perm_mbrp_id IS NOT NULL
BEGIN
    IF @rol_admin_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_admin_id AND permiso_id = @perm_mbrp_id)
        INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (@rol_admin_id, @perm_mbrp_id);
    
    IF @rol_super_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_super_id AND permiso_id = @perm_mbrp_id)
        INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (@rol_super_id, @perm_mbrp_id);
    
    PRINT '  ✓ Permiso mbrp.ver_proveedores asignado';
END
GO

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Permisos ver_proveedores';
PRINT '============================================================================';

SELECT 
    r.nombre AS Rol, 
    p.codigo, 
    p.modulo 
FROM pal_roles_permisos rp
JOIN pal_roles r ON r.id = rp.rol_id
JOIN pal_permisos p ON p.id = rp.permiso_id
WHERE p.codigo IN ('tra.ver_proveedores', 'mbrp.ver_proveedores')
ORDER BY p.codigo, r.nombre;

PRINT '';
PRINT 'Migración 007 completada exitosamente ✓';
GO
