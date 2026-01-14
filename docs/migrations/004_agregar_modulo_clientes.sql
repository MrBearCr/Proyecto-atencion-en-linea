-- ============================================================================
-- Migración 004: Agregar módulo y permiso base para Clientes (v2 - Corregido)
-- Fecha: 2026-01-09
-- Descripción: Agrega el módulo 'CLIENTES' a las restricciones CHECK de las
--              tablas pal_permisos y pal_usuarios_modulos. Luego, agrega el 
--              permiso base y lo asigna al rol de Administrador.
-- ============================================================================

USE VAD10; -- CAMBIAR POR EL NOMBRE DE TU BD
GO

PRINT 'Iniciando migración 004: Agregar módulo de Clientes (v2 - Corregido)...';
GO

-- ============================================================================
-- PASO 1: Actualizar la restricción en la tabla de PERMISOS
-- ============================================================================

PRINT 'Paso 1/4: Actualizando la restricción chk_perm_modulo en [pal_permisos]...';
GO

-- Dropear la restricción existente si existe
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'chk_perm_modulo')
BEGIN
    ALTER TABLE pal_permisos DROP CONSTRAINT chk_perm_modulo;
    PRINT '  ✓ Restricción chk_perm_modulo eliminada.';
END
ELSE
BEGIN
    PRINT '  ℹ Restricción chk_perm_modulo no encontrada, se creará una nueva.';
END
GO

-- Volver a crear la restricción con 'CLIENTES' añadido
ALTER TABLE pal_permisos ADD CONSTRAINT chk_perm_modulo
CHECK (modulo IN ('TRA', 'MBRP', 'STOCK', 'MENSAJES', 'ESTADISTICAS', 'CALENDARIO', 'ADMIN', 'CLIENTES'));
PRINT '  ✓ Restricción chk_perm_modulo creada/actualizada para incluir CLIENTES.';
GO

-- ============================================================================
-- PASO 2: Actualizar la restricción en la tabla de USUARIOS-MODULOS
-- ============================================================================

PRINT 'Paso 2/4: Actualizando la restricción chk_pal_um_modulo en [pal_usuarios_modulos]...';
GO

-- Dropear la restricción existente si existe
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'chk_pal_um_modulo')
BEGIN
    ALTER TABLE pal_usuarios_modulos DROP CONSTRAINT chk_pal_um_modulo;
    PRINT '  ✓ Restricción chk_pal_um_modulo eliminada.';
END
ELSE
BEGIN
    PRINT '  ℹ Restricción chk_pal_um_modulo no encontrada, se creará una nueva.';
END
GO

-- Volver a crear la restricción con 'CLIENTES' añadido
ALTER TABLE pal_usuarios_modulos ADD CONSTRAINT chk_pal_um_modulo
CHECK (modulo IN ('TRA', 'MBRP', 'STOCK', 'MENSAJES', 'ESTADISTICAS', 'CALENDARIO', 'ADMIN', 'CLIENTES'));
PRINT '  ✓ Restricción chk_pal_um_modulo creada/actualizada para incluir CLIENTES.';
GO

-- ============================================================================
-- PASO 3: Agregar el permiso base 'clientes.ver' a pal_permisos
-- ============================================================================

PRINT 'Paso 3/4: Agregando permiso a pal_permisos...';

-- Verificar y agregar permiso clientes.ver
IF NOT EXISTS (SELECT 1 FROM pal_permisos WHERE codigo = N'clientes.ver')
BEGIN
    INSERT INTO pal_permisos (codigo, modulo, descripcion)
    VALUES (N'clientes.ver', N'CLIENTES', N'Acceso principal al módulo de Clientes');
    PRINT '  ✓ Permiso clientes.ver creado';
END
ELSE
BEGIN
    PRINT '  ℹ Permiso clientes.ver ya existe';
END
GO

-- ============================================================================
-- PASO 4: Asignar el nuevo permiso al rol de Administrador
-- ============================================================================

PRINT 'Paso 4/4: Asignando permiso al rol Administrador...';

DECLARE @rol_admin_id INT = (SELECT id FROM pal_roles WHERE nombre = N'Administrador');
DECLARE @perm_clientes_id INT = (SELECT id FROM pal_permisos WHERE codigo = N'clientes.ver');

IF @rol_admin_id IS NOT NULL AND @perm_clientes_id IS NOT NULL
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pal_roles_permisos WHERE rol_id = @rol_admin_id AND permiso_id = @perm_clientes_id)
    BEGIN
        INSERT INTO pal_roles_permisos (rol_id, permiso_id)
        VALUES (@rol_admin_id, @perm_clientes_id);
        PRINT '  ✓ Permiso de Clientes asignado a Administrador';
    END
    ELSE
    BEGIN
        PRINT '  ℹ Permiso de Clientes ya asignado a Administrador';
    END
END
ELSE
BEGIN
    PRINT '  ⚠ Rol Administrador o permiso clientes.ver no encontrado, no se pudo asignar.';
END
GO

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

PRINT '';
PRINT '============================================================================';
PRINT 'VERIFICACIÓN: Permiso de Clientes';
PRINT '============================================================================';

SELECT 
    r.nombre AS Rol,
    p.codigo AS Permiso,
    p.descripcion AS Descripcion
FROM pal_roles_permisos rp
INNER JOIN pal_roles r ON rp.rol_id = r.id
INNER JOIN pal_permisos p ON rp.permiso_id = p.id
WHERE p.codigo = N'clientes.ver' AND r.nombre = N'Administrador';

PRINT '';
PRINT '============================================================================';
PRINT 'Migración 004 completada exitosamente ✓';
PRINT '============================================================================';
GO
