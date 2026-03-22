-- Migración: Soporte para Recepciones Parciales (TRS -> REC)

-- 1. Tabla Maestra de Recepciones
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_recepciones_maestro' AND type = 'U')
BEGIN
    CREATE TABLE pal_recepciones_maestro (
        id INT IDENTITY(1,1) PRIMARY KEY,
        numero_recepcion NVARCHAR(20) UNIQUE NOT NULL, -- REC-xxxxxx
        transferencia_id INT NOT NULL,
        fecha_recepcion DATETIME DEFAULT GETDATE(),
        usuario_recibe INT,
        observaciones TEXT NULL,
        estado NVARCHAR(20) DEFAULT 'completada', -- completada, anulada
        CONSTRAINT FK_Recepcion_Transferencia FOREIGN KEY (transferencia_id) REFERENCES pal_transferencias_maestro(id)
    );
END;

-- 2. Tabla Detalle de Recepciones
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_recepciones_detalle' AND type = 'U')
BEGIN
    CREATE TABLE pal_recepciones_detalle (
        id INT IDENTITY(1,1) PRIMARY KEY,
        recepcion_id INT NOT NULL,
        sugerencia_id INT NOT NULL, -- Vincula al item original de la transferencia
        cantidad_recibida DECIMAL(18,2) NOT NULL,
        CONSTRAINT FK_Detalle_Recepcion FOREIGN KEY (recepcion_id) REFERENCES pal_recepciones_maestro(id),
        CONSTRAINT FK_Detalle_Sugerencia FOREIGN KEY (sugerencia_id) REFERENCES pal_sugerencias_transferencia(id)
    );
END;

-- 3. Modificaciones a pal_sugerencias_transferencia
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_sugerencias_transferencia' AND type = 'U')
BEGIN
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_sugerencias_transferencia]') AND name = 'cantidad_recibida_total')
    BEGIN
        ALTER TABLE [dbo].[pal_sugerencias_transferencia] ADD [cantidad_recibida_total] DECIMAL(18,2) DEFAULT 0;
    END

    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[pal_sugerencias_transferencia]') AND name = 'estado_recepcion')
    BEGIN
        ALTER TABLE [dbo].[pal_sugerencias_transferencia] ADD [estado_recepcion] NVARCHAR(20) DEFAULT 'pendiente'; -- pendiente, parcial, completada
    END
END;

-- 4. Actualizar datos existentes (Opcional: Migrar transferencias 'recibida' a estado consistente)
-- Si una transferencia ya estaba 'recibida', asumimos que se recibió todo lo autorizado/sugerido.
UPDATE pal_sugerencias_transferencia
SET cantidad_recibida_total = cantidad_sugerida,
    estado_recepcion = 'completada'
FROM pal_sugerencias_transferencia st
JOIN pal_transferencias_maestro tm ON st.maestro_id = tm.id
WHERE tm.estado = 'recibida' AND st.cantidad_recibida_total IS NULL;

-- Asegurar que los campos nuevos no sean NULL después de la actualización
UPDATE pal_sugerencias_transferencia
SET cantidad_recibida_total = 0
WHERE cantidad_recibida_total IS NULL;
