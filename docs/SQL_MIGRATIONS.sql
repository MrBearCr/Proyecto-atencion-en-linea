/*
SQL Server migration script for Users, Roles, Permissions, Module Access, Sessions, and Audit (prefixed with pal_*)
Idempotent: safe to run multiple times
Note: Avoids GO statements for compatibility with pyodbc execution
*/

/* 1) Tables */

-- pal_usuarios
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_usuarios' AND type = 'U')
BEGIN
    CREATE TABLE pal_usuarios (
        id INT IDENTITY(1,1) PRIMARY KEY,
        username NVARCHAR(50) NOT NULL UNIQUE,
        password_hash NVARCHAR(255) NOT NULL,
        nombre_completo NVARCHAR(100) NOT NULL,
        email NVARCHAR(100) NULL,
        activo BIT NOT NULL DEFAULT 1,
        fecha_creacion DATETIME2 DEFAULT SYSUTCDATETIME(),
        fecha_ultimo_acceso DATETIME2 NULL,
        intentos_fallidos INT DEFAULT 0,
        bloqueado_hasta DATETIME2 NULL
    );
END

-- pal_roles
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_roles' AND type = 'U')
BEGIN
    CREATE TABLE pal_roles (
        id INT IDENTITY(1,1) PRIMARY KEY,
        nombre NVARCHAR(50) NOT NULL UNIQUE,
        descripcion NVARCHAR(MAX) NULL,
        es_sistema BIT NOT NULL DEFAULT 0
    );
END

-- pal_permisos
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_permisos' AND type = 'U')
BEGIN
    CREATE TABLE pal_permisos (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo NVARCHAR(50) NOT NULL UNIQUE,
        modulo NVARCHAR(50) NOT NULL,
        descripcion NVARCHAR(MAX) NULL,
        CONSTRAINT chk_perm_modulo CHECK (modulo IN (N'TRA', N'MBRP', N'STOCK', N'MENSAJES', N'ESTADISTICAS', N'CALENDARIO', N'ADMIN'))
    );
END

-- pal_usuarios_roles
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_usuarios_roles' AND type = 'U')
BEGIN
    CREATE TABLE pal_usuarios_roles (
        usuario_id INT NOT NULL,
        rol_id INT NOT NULL,
        fecha_asignacion DATETIME2 DEFAULT SYSUTCDATETIME(),
        asignado_por INT NULL,
        CONSTRAINT pk_pal_usuarios_roles PRIMARY KEY (usuario_id, rol_id),
        CONSTRAINT fk_pal_ur_usuario FOREIGN KEY (usuario_id) REFERENCES pal_usuarios(id) ON DELETE CASCADE,
        CONSTRAINT fk_pal_ur_rol FOREIGN KEY (rol_id) REFERENCES pal_roles(id) ON DELETE CASCADE,
        CONSTRAINT fk_pal_ur_asignado_por FOREIGN KEY (asignado_por) REFERENCES pal_usuarios(id)
    );
END

-- pal_roles_permisos
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_roles_permisos' AND type = 'U')
BEGIN
    CREATE TABLE pal_roles_permisos (
        rol_id INT NOT NULL,
        permiso_id INT NOT NULL,
        CONSTRAINT pk_pal_roles_permisos PRIMARY KEY (rol_id, permiso_id),
        CONSTRAINT fk_pal_rp_rol FOREIGN KEY (rol_id) REFERENCES pal_roles(id) ON DELETE CASCADE,
        CONSTRAINT fk_pal_rp_permiso FOREIGN KEY (permiso_id) REFERENCES pal_permisos(id) ON DELETE CASCADE
    );
END

-- pal_usuarios_permisos (permisos directos)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_usuarios_permisos' AND type = 'U')
BEGIN
    CREATE TABLE pal_usuarios_permisos (
        usuario_id INT NOT NULL,
        permiso_id INT NOT NULL,
        concedido BIT NOT NULL DEFAULT 1,
        fecha_asignacion DATETIME2 DEFAULT SYSUTCDATETIME(),
        asignado_por INT NULL,
        CONSTRAINT pk_pal_usuarios_permisos PRIMARY KEY (usuario_id, permiso_id),
        CONSTRAINT fk_pal_up_usuario FOREIGN KEY (usuario_id) REFERENCES pal_usuarios(id) ON DELETE CASCADE,
        CONSTRAINT fk_pal_up_permiso FOREIGN KEY (permiso_id) REFERENCES pal_permisos(id) ON DELETE CASCADE,
        CONSTRAINT fk_pal_up_asignado_por FOREIGN KEY (asignado_por) REFERENCES pal_usuarios(id)
    );
END

-- pal_usuarios_modulos (control de entrada por usuario)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_usuarios_modulos' AND type = 'U')
BEGIN
    CREATE TABLE pal_usuarios_modulos (
        usuario_id INT NOT NULL,
        modulo NVARCHAR(50) NOT NULL,
        habilitado BIT NOT NULL DEFAULT 1,
        fecha_asignacion DATETIME2 DEFAULT SYSUTCDATETIME(),
        asignado_por INT NULL,
        CONSTRAINT pk_pal_usuarios_modulos PRIMARY KEY (usuario_id, modulo),
        CONSTRAINT fk_pal_um_usuario FOREIGN KEY (usuario_id) REFERENCES pal_usuarios(id) ON DELETE CASCADE,
        CONSTRAINT fk_pal_um_asignado_por FOREIGN KEY (asignado_por) REFERENCES pal_usuarios(id),
        CONSTRAINT chk_pal_um_modulo CHECK (modulo IN (N'TRA', N'MBRP', N'STOCK', N'MENSAJES', N'ESTADISTICAS', N'CALENDARIO', N'ADMIN'))
    );
END

-- pal_auditoria_accesos
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_auditoria_accesos' AND type = 'U')
BEGIN
    CREATE TABLE pal_auditoria_accesos (
        id INT IDENTITY(1,1) PRIMARY KEY,
        usuario_id INT NULL,
        accion NVARCHAR(100) NOT NULL,
        modulo NVARCHAR(50) NULL,
        detalle NVARCHAR(MAX) NULL,
        ip_address NVARCHAR(45) NULL,
        exitoso BIT NOT NULL,
        fecha DATETIME2 DEFAULT SYSUTCDATETIME(),
        CONSTRAINT fk_pal_aud_usuario FOREIGN KEY (usuario_id) REFERENCES pal_usuarios(id)
    );
END

-- pal_sesiones
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_sesiones' AND type = 'U')
BEGIN
    CREATE TABLE pal_sesiones (
        id INT IDENTITY(1,1) PRIMARY KEY,
        usuario_id INT NOT NULL,
        token NVARCHAR(255) NOT NULL UNIQUE,
        ip_address NVARCHAR(45) NULL,
        fecha_inicio DATETIME2 DEFAULT SYSUTCDATETIME(),
        fecha_expiracion DATETIME2 NOT NULL,
        activa BIT NOT NULL DEFAULT 1,
        CONSTRAINT fk_pal_ses_usuario FOREIGN KEY (usuario_id) REFERENCES pal_usuarios(id) ON DELETE CASCADE
    );
END

/* 2) Indexes */

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_usuarios_username')
    CREATE INDEX idx_pal_usuarios_username ON pal_usuarios(username);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_usuarios_activo')
    CREATE INDEX idx_pal_usuarios_activo ON pal_usuarios(activo);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_sesiones_token')
    CREATE INDEX idx_pal_sesiones_token ON pal_sesiones(token);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_sesiones_activa')
    CREATE INDEX idx_pal_sesiones_activa ON pal_sesiones(activa);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_auditoria_usuario')
    CREATE INDEX idx_pal_auditoria_usuario ON pal_auditoria_accesos(usuario_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_auditoria_fecha')
    CREATE INDEX idx_pal_auditoria_fecha ON pal_auditoria_accesos(fecha);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_usuarios_modulos_usuario')
    CREATE INDEX idx_pal_usuarios_modulos_usuario ON pal_usuarios_modulos(usuario_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pal_usuarios_modulos_modulo')
    CREATE INDEX idx_pal_usuarios_modulos_modulo ON pal_usuarios_modulos(modulo);

/* 3) Seed Roles */

IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Administrador')
    INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Administrador', N'Acceso total al sistema', 1);
IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Supervisor')
    INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Supervisor', N'Operación y consulta avanzada', 1);
IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Analista')
    INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Analista', N'Consulta y exportación', 1);
IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Operador Stock')
    INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Operador Stock', N'Gestión de stock', 1);
IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Mensajería')
    INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Mensajería', N'Envío y gestión de mensajes', 1);
IF NOT EXISTS (SELECT 1 FROM pal_roles WHERE nombre = N'Consulta')
    INSERT INTO pal_roles (nombre, descripcion, es_sistema) VALUES (N'Consulta', N'Solo lectura', 1);

/* 4) Seed Permissions */

DECLARE @perm TABLE(codigo NVARCHAR(50), modulo NVARCHAR(50), descripcion NVARCHAR(MAX));
INSERT INTO @perm (codigo, modulo, descripcion)
VALUES
 (N'tra.ver', N'TRA', N'Ver datos de rotación')
,(N'tra.exportar', N'TRA', N'Exportar reportes')
,(N'tra.configurar', N'TRA', N'Configurar parámetros')
,(N'mbrp.ver', N'MBRP', N'Ver datos MBRP')
,(N'mbrp.exportar', N'MBRP', N'Exportar reportes')
,(N'mbrp.configurar', N'MBRP', N'Configurar umbrales')
,(N'stock.ver', N'STOCK', N'Ver alertas de stock')
,(N'stock.editar', N'STOCK', N'Marcar favoritos / edición')
,(N'stock.exportar', N'STOCK', N'Exportar reportes')
,(N'stock.configurar', N'STOCK', N'Configurar alertas')
,(N'mensajes.ver', N'MENSAJES', N'Ver mensajes programados')
,(N'mensajes.crear', N'MENSAJES', N'Crear mensajes')
,(N'mensajes.enviar', N'MENSAJES', N'Enviar mensajes')
,(N'mensajes.eliminar', N'MENSAJES', N'Eliminar mensajes')
,(N'mensajes.configurar', N'MENSAJES', N'Configurar plantillas')
,(N'estadisticas.ver', N'ESTADISTICAS', N'Ver gráficos y reportes')
,(N'estadisticas.exportar', N'ESTADISTICAS', N'Exportar reportes')
,(N'calendario.ver', N'CALENDARIO', N'Ver eventos')
,(N'calendario.crear', N'CALENDARIO', N'Crear eventos')
,(N'calendario.editar', N'CALENDARIO', N'Editar eventos')
,(N'calendario.eliminar', N'CALENDARIO', N'Eliminar eventos')
,(N'admin.usuarios', N'ADMIN', N'Gestionar usuarios')
,(N'admin.roles', N'ADMIN', N'Gestionar roles')
,(N'admin.permisos', N'ADMIN', N'Gestionar permisos')
,(N'admin.sistema', N'ADMIN', N'Configuración general')
,(N'admin.auditoria', N'ADMIN', N'Ver logs de auditoría');

INSERT INTO pal_permisos (codigo, modulo, descripcion)
SELECT p.codigo, p.modulo, p.descripcion
FROM @perm p
LEFT JOIN pal_permisos pe ON pe.codigo = p.codigo
WHERE pe.id IS NULL;

/* 5) Assign permissions to roles */

DECLARE @rol_admin INT = (SELECT id FROM pal_roles WHERE nombre = N'Administrador');
DECLARE @rol_super INT = (SELECT id FROM pal_roles WHERE nombre = N'Supervisor');
DECLARE @rol_analista INT = (SELECT id FROM pal_roles WHERE nombre = N'Analista');
DECLARE @rol_stock INT = (SELECT id FROM pal_roles WHERE nombre = N'Operador Stock');
DECLARE @rol_msg INT = (SELECT id FROM pal_roles WHERE nombre = N'Mensajería');
DECLARE @rol_consulta INT = (SELECT id FROM pal_roles WHERE nombre = N'Consulta');

DECLARE @rp TABLE(rol_id INT, perm_code NVARCHAR(50));
-- Administrador: todos los permisos
INSERT INTO @rp(rol_id, perm_code)
SELECT @rol_admin, codigo FROM pal_permisos;

-- Supervisor
INSERT INTO @rp(rol_id, perm_code)
SELECT @rol_super, codigo FROM pal_permisos WHERE codigo IN (
    N'tra.ver', N'tra.exportar',
    N'mbrp.ver', N'mbrp.exportar',
    N'stock.ver', N'stock.editar', N'stock.exportar',
    N'mensajes.ver', N'mensajes.crear', N'mensajes.enviar',
    N'estadisticas.ver'
);

-- Analista
INSERT INTO @rp(rol_id, perm_code)
SELECT @rol_analista, codigo FROM pal_permisos WHERE codigo IN (
    N'tra.ver', N'tra.exportar',
    N'mbrp.ver', N'mbrp.exportar',
    N'stock.ver',
    N'estadisticas.ver'
);

-- Operador Stock
INSERT INTO @rp(rol_id, perm_code)
SELECT @rol_stock, codigo FROM pal_permisos WHERE codigo IN (
    N'stock.ver', N'stock.editar'
);

-- Mensajería
INSERT INTO @rp(rol_id, perm_code)
SELECT @rol_msg, codigo FROM pal_permisos WHERE codigo IN (
    N'mensajes.ver', N'mensajes.crear', N'mensajes.enviar'
);

-- Consulta (solo lectura: ver)
INSERT INTO @rp(rol_id, perm_code)
SELECT @rol_consulta, codigo FROM pal_permisos WHERE codigo IN (
    N'tra.ver', N'mbrp.ver', N'stock.ver', N'estadisticas.ver', N'calendario.ver', N'mensajes.ver'
);

-- Upsert into pal_roles_permisos
INSERT INTO pal_roles_permisos (rol_id, permiso_id)
SELECT r.rol_id, p.id
FROM @rp r
JOIN pal_permisos p ON p.codigo = r.perm_code
LEFT JOIN pal_roles_permisos rp ON rp.rol_id = r.rol_id AND rp.permiso_id = p.id
WHERE rp.rol_id IS NULL;

/* 6) Create initial admin user and enable modules */

IF NOT EXISTS (SELECT 1 FROM pal_usuarios WHERE username = N'admin')
BEGIN
    -- Placeholder bcrypt-like length (to be updated by application on first login/reset)
    DECLARE @admin_pwd NVARCHAR(255) = N'$2b$12$PLACEHOLDER_PLACEHOLDER_PLACEHOLDER_PLACEHOLDER_PL';
    INSERT INTO pal_usuarios (username, password_hash, nombre_completo, email, activo)
    VALUES (N'admin', @admin_pwd, N'Administrador del Sistema', NULL, 1);
END

-- Assign Administrador role to admin user
DECLARE @admin_user_id INT = (SELECT id FROM pal_usuarios WHERE username = N'admin');
IF @admin_user_id IS NOT NULL AND @rol_admin IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pal_usuarios_roles WHERE usuario_id = @admin_user_id AND rol_id = @rol_admin
    )
    INSERT INTO pal_usuarios_roles (usuario_id, rol_id, asignado_por)
    VALUES (@admin_user_id, @rol_admin, @admin_user_id);
END

-- Enable all modules for admin
DECLARE @mods TABLE(modulo NVARCHAR(50));
INSERT INTO @mods(modulo)
VALUES (N'TRA'),(N'MBRP'),(N'STOCK'),(N'MENSAJES'),(N'ESTADISTICAS'),(N'CALENDARIO'),(N'ADMIN');

INSERT INTO pal_usuarios_modulos (usuario_id, modulo, habilitado, asignado_por)
SELECT @admin_user_id, m.modulo, 1, @admin_user_id
FROM @mods m
LEFT JOIN pal_usuarios_modulos um ON um.usuario_id = @admin_user_id AND um.modulo = m.modulo
WHERE um.usuario_id IS NULL;

/* END OF MIGRATIONS */
