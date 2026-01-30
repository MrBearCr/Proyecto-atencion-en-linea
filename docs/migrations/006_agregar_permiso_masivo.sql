-- ============================================================================
-- Migración 006: Agregar permiso para reporte masivo (todos los productos)
-- Fecha: 2026-01-30
-- Descripción: Agrega permiso 'tra.masivo' para habilitar la opción de 
--              incluir productos sin ventas en el reporte TRA.
-- ============================================================================

USE VAD10; 
GO

PRINT 'Iniciando migración 006: Agregar permiso tra.masivo...';
GO

-- ============================================================================
-- PASO 1: Agregar nuevo permiso a pal_permisos
-- ============================================================================

PRINT 'Paso 1/2: Agregando permiso a pal_permisos...';

IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'tra.masivo')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'tra.masivo',
            N'TRA',
            N'Ver reporte masivo (incluye productos sin ventas)');
    PRINT '  ✓ Permiso tra.masivo creado';
END
ELSE
BEGIN
    PRINT '  ℹ Permiso tra.masivo ya existe';
END
GO

-- ============================================================================
-- PASO 2: Asignar permisos a roles (Administrador y Supervisor)
-- ============================================================================

PRINT 'Paso 2/2: Asignando permisos a roles...';

DECLARE @rol_admin_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Administrador');
DECLARE @rol_super_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Supervisor');
DECLARE @perm_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'tra.masivo');

IF @perm_id IS NOT NULL
BEGIN
    -- Asignar a Administrador
    IF @rol_admin_id IS NOT NULL
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_admin_id AND permiso_id = @perm_id)
        BEGIN
            INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (@rol_admin_id, @perm_id);
            PRINT '  ✓ Asignado a Administrador';
        END
    END

    -- Asignar a Supervisor
    IF @rol_super_id IS NOT NULL
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_super_id AND permiso_id = @perm_id)
        BEGIN
            INSERT INTO pal_roles_permisos (rol_id, permiso_id) VALUES (@rol_super_id, @perm_id);
            PRINT '  ✓ Asignado a Supervisor';
        END
    END
END
ELSE
BEGIN
    PRINT '  ⚠ Error: No se pudo obtener ID del permiso creado.';
END
GO

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Permisos tra.masivo';
PRINT '============================================================================';

SELECT 
    r.nombre AS Rol, 
    p.codigo, 
    p.modulo 
FROM pal_roles_permisos rp
JOIN pal_roles r ON r.id = rp.rol_id
JOIN pal_permisos p ON p.id = rp.permiso_id
WHERE p.codigo = 'tra.masivo'
ORDER BY r.nombre;

PRINT '';
PRINT 'Migración 006 completada exitosamente ✓';
GO
