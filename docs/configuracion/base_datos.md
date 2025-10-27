# Configuración de Base de Datos (SQL Server)

## Esquema utilizado por la app
Tablas internas creadas automáticamente por `DatabaseManager`:

```sql
CREATE TABLE clientes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    numero_cliente NVARCHAR(50) NOT NULL,
    C_CODIGO NVARCHAR(15) NOT NULL
);
CREATE INDEX idx_clientes_numero ON clientes (numero_cliente);
CREATE INDEX idx_clientes_codigo ON clientes (C_CODIGO);

CREATE TABLE favoritos_productos (
    codigo NVARCHAR(15) PRIMARY KEY,
    favorito BIT DEFAULT 0,
    fecha_creacion DATETIME DEFAULT GETDATE()
);

CREATE TABLE envios_programados (
    id INT IDENTITY(1,1) PRIMARY KEY,
    numero_cliente NVARCHAR(50) NOT NULL,
    fecha_programada DATETIME NOT NULL,
    fecha_creacion DATETIME DEFAULT GETDATE(),
    estado NVARCHAR(20) DEFAULT 'PENDIENTE'
);
CREATE INDEX idx_envios_fecha_estado ON envios_programados (fecha_programada, estado);
CREATE INDEX idx_envios_numero ON envios_programados (numero_cliente);

CREATE TABLE TEMP_ENVIO (
    numero_cliente NVARCHAR(50),
    codigo_producto NVARCHAR(15),
    descripcion NVARCHAR(255),
    timestamp DATETIME DEFAULT GETDATE()
);
```

Tablas externas (solo lectura) esperadas en el ERP:
- `MA_PRODUCTOS (C_CODIGO, C_DESCRI)`
- `MA_DEPOPROD (c_codarticulo, c_coddeposito, n_cantidad)`
- `TR_INVENTARIO (c_Codarticulo, f_fecha, c_Concepto, n_Cantidad, c_Deposito)`

## Conexión
- Conector: pyodbc + ODBC Driver de SQL Server (instalar el driver oficial de Microsoft).
- Autenticación: SQL o Windows. Credenciales cifradas con keyring + Fernet.
- Consultas: siempre parametrizadas; commit/rollback automáticos.

## Recomendaciones
- Índices arriba incluidos; añadir índices adicionales según volumen real.
- Usar WITH (NOLOCK) solo en lecturas no críticas si aplica a tu entorno.
- Separar base operativa ERP de la base local de la app si es posible.

