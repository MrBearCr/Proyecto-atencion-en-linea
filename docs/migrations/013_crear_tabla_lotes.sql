-- Migración: Tabla de Lotes y Vencimientos para Recepciones
-- Fecha: 2026-03-21

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pal_recepciones_lotes' AND type = 'U')
BEGIN
    CREATE TABLE pal_recepciones_lotes (
        id INT IDENTITY(1,1) PRIMARY KEY,
        recepcion_detalle_id INT NOT NULL,
        lote_interno NVARCHAR(50) NOT NULL, -- UNIQUE será validado por lógica o índice si se requiere
        lote_fabrica NVARCHAR(50) NULL,
        fecha_vencimiento DATE NULL,
        cantidad DECIMAL(18,2) NOT NULL,
        fecha_registro DATETIME DEFAULT GETDATE(),
        
        CONSTRAINT FK_Lotes_RecepcionDetalle FOREIGN KEY (recepcion_detalle_id) REFERENCES pal_recepciones_detalle(id)
    );

    -- Índice para búsquedas rápidas por lote interno
    CREATE INDEX IX_pal_recepciones_lotes_interno ON pal_recepciones_lotes(lote_interno);
END;
