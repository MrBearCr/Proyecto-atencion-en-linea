-- ============================================================================
-- Migración 011: Permisos de Proveedores y Análisis Económico para STOCK
-- Fecha: 2026-02-18
-- Descripción: Agrega permisos 'stock.ver_proveedores' y asegura
--              'stock.ver_costo_utilidad' para el módulo STOCK.
--              (Eliminado stock.ver_ventas_dolares por no ser necesario).
-- ============================================================================

USE VAD10; 
GO

PRINT 'Iniciando migración 011: Permisos STOCK v3...';
GO

-- ============================================================================
-- PASO 1: Agregar nuevos permisos a pal_permisos
-- ============================================================================

PRINT 'Paso 1/2: Agregando permisos a pal_permisos...';

-- 1.1 Ver Proveedores en STOCK
IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'stock.ver_proveedores')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'stock.ver_proveedores', N'STOCK', N'Ver último proveedor asociado a un producto en módulo STOCK');
    PRINT '  ✓ Permiso stock.ver_proveedores creado';
END
ELSE
BEGIN
    PRINT '  ℹ Permiso stock.ver_proveedores ya existe';
END

-- 1.2 Ver Costo/Utilidad (Asegurar existencia)
IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'stock.ver_costo_utilidad')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'stock.ver_costo_utilidad', N'STOCK', N'Ver costo y utilidad en reportes de STOCK');
    PRINT '  ✓ Permiso stock.ver_costo_utilidad creado';
END
GO

-- ============================================================================
-- PASO 2: Asignar permisos a roles (Administrador y Supervisor)
-- ============================================================================

PRINT 'Paso 2/2: Asignando permisos a roles...';

DECLARE @rol_admin_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Administrador');
DECLARE @rol_super_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Supervisor');

-- Lista de permisos para procesar
DECLARE @perm_prov_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'stock.ver_proveedores');
DECLARE @perm_costo_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'stock.ver_costo_utilidad');

-- Asignar stock.ver_proveedores
IF @perm_prov_id IS NOT NULL
BEGIN
    IF @rol_admin_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_admin_id AND permiso_id = @perm_prov_id)
        INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (@rol_admin_id, @perm_prov_id);
    
    IF @rol_super_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_super_id AND permiso_id = @perm_prov_id)
        INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (@rol_super_id, @perm_prov_id);
    
    PRINT '  ✓ Permiso stock.ver_proveedores asignado';
END

-- Asignar stock.ver_costo_utilidad
IF @perm_costo_id IS NOT NULL
BEGIN
    IF @rol_admin_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_admin_id AND permiso_id = @perm_costo_id)
        INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (@rol_admin_id, @perm_costo_id);
    
    IF @rol_super_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_super_id AND permiso_id = @perm_costo_id)
        INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (@rol_super_id, @perm_costo_id);
    
    PRINT '  ✓ Permiso stock.ver_costo_utilidad asignado/verificado';
END
GO

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Permisos STOCK (Refinado)';
PRINT '============================================================================';

SELECT 
    r.nombre AS Rol, 
    p.codigo, 
    p.modulo 
FROM pal_roles_permisos rp
JOIN pal_roles r ON r.id = rp.rol_id
JOIN pal_permisos p ON p.id = rp.permiso_id
WHERE p.codigo IN ('stock.ver_proveedores', 'stock.ver_costo_utilidad')
ORDER BY p.codigo, r.nombre;

PRINT '';
PRINT 'Migración 011 completada exitosamente ✓';
GO
