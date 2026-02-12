"""
Script de diagnóstico para identificar productos con stock 0 y rotación ALTA
que NO están mostrando avisos de pérdida de venta.

Este script ayuda a identificar por qué algunos productos no están en fechas_criticas.
"""

import pyodbc
from datetime import datetime

# Configuración de conexión (ajustar según tu db_config.ini)
SERVER = "192.168.5.2"
DATABASE = "vad10"
USER = "sa"
PASSWORD = ""  # Ajustar si es necesario

def connect_db():
    """Conecta a la base de datos"""
    conn_str = (
        f"DRIVER={{SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USER};"
        f"PWD={PASSWORD};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def analizar_productos_sin_aviso():
    """
    Analiza productos que tienen:
    - Stock = 0
    - Rotación ALTA (top 20% de ventas)
    - Pero NO muestran aviso de pérdida de venta
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("ANÁLISIS: Productos con Stock 0 y Rotación ALTA sin aviso de pérdida de venta")
    print("=" * 80)
    
    # Query para identificar productos problemáticos
    query = """
    WITH Ventas AS (
        SELECT 
            i.c_Codarticulo AS codigo,
            SUM(CASE 
                WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
                WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
                ELSE 0 
            END) AS neto
        FROM TR_INVENTARIO i WITH (NOLOCK)
        WHERE i.f_fecha >= DATEADD(DAY, -180, GETDATE())
            AND i.c_Concepto IN ('VEN', 'DEV')
            AND i.c_Deposito = '0301'  -- Ajustar según tu depósito
        GROUP BY i.c_Codarticulo
        HAVING SUM(CASE 
            WHEN i.c_Concepto = 'VEN' THEN i.n_Cantidad
            WHEN i.c_Concepto = 'DEV' THEN -i.n_Cantidad 
            ELSE 0 
        END) > 0
    ),
    Stock AS (
        SELECT 
            c_codarticulo AS codigo,
            SUM(n_cantidad) AS stock_total
        FROM MA_DEPOPROD WITH (NOLOCK)
        WHERE c_coddeposito = '0301'  -- Ajustar según tu depósito
        GROUP BY c_codarticulo
    ),
    Rotacion AS (
        SELECT 
            codigo,
            neto,
            NTILE(5) OVER (ORDER BY neto DESC) AS quintil
        FROM Ventas
    )
    SELECT 
        p.C_CODIGO,
        COALESCE(p.cu_descripcion_corta, p.C_DESCRI) AS descripcion,
        COALESCE(s.stock_total, 0) AS stock,
        COALESCE(v.neto, 0) AS ventas_180d,
        p.Update_date,
        (SELECT MAX(f_fecha) 
         FROM TR_INVENTARIO i WITH (NOLOCK)
         WHERE i.c_Codarticulo = p.C_CODIGO 
           AND i.c_Concepto = 'VEN'
           AND i.c_Deposito = '0301') AS ultima_venta,
        CASE 
            WHEN p.Update_date IS NULL THEN 'Sin Update_date'
            WHEN p.Update_date > (SELECT MAX(f_fecha) FROM TR_INVENTARIO i WHERE i.c_Codarticulo = p.C_CODIGO AND i.c_Concepto = 'VEN') 
                THEN 'Update_date posterior a última venta'
            WHEN NOT EXISTS (
                SELECT 1 FROM TR_INVENTARIO i 
                WHERE i.c_Codarticulo = p.C_CODIGO 
                  AND i.c_Concepto = 'VEN'
                  AND i.f_fecha >= p.Update_date
            ) THEN 'Sin ventas desde Update_date'
            ELSE 'OK - Debería estar en fechas_criticas'
        END AS razon_exclusion
    FROM MA_PRODUCTOS p WITH (NOLOCK)
    LEFT JOIN Stock s ON p.C_CODIGO = s.codigo
    LEFT JOIN Ventas v ON p.C_CODIGO = v.codigo
    INNER JOIN Rotacion r ON p.C_CODIGO = r.codigo
    WHERE r.quintil = 1  -- Top 20% (ALTA rotación)
        AND COALESCE(s.stock_total, 0) = 0  -- Stock en 0
    ORDER BY v.neto DESC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print("\n✅ No se encontraron productos con este problema.")
        cursor.close()
        conn.close()
        return
    
    print(f"\n⚠️ Se encontraron {len(rows)} productos con stock 0 y rotación ALTA:\n")
    
    # Agrupar por razón de exclusión
    razones = {}
    for row in rows:
        razon = row[6]
        if razon not in razones:
            razones[razon] = []
        razones[razon].append(row)
    
    # Mostrar resumen
    print("RESUMEN POR RAZÓN DE EXCLUSIÓN:")
    print("-" * 80)
    for razon, productos in razones.items():
        print(f"\n{razon}: {len(productos)} productos")
        print("  Ejemplos:")
        for prod in productos[:3]:  # Mostrar solo 3 ejemplos
            codigo, desc, stock, ventas, update_date, ultima_venta, _ = prod
            print(f"    - {codigo}: {desc[:40]}")
            print(f"      Ventas (180d): {ventas:.0f} | Update_date: {update_date} | Última venta: {ultima_venta}")
    
    print("\n" + "=" * 80)
    print("DETALLES COMPLETOS:")
    print("=" * 80)
    
    for row in rows:
        codigo, desc, stock, ventas, update_date, ultima_venta, razon = row
        print(f"\nCódigo: {codigo}")
        print(f"Descripción: {desc}")
        print(f"Stock: {stock}")
        print(f"Ventas (180 días): {ventas:.0f}")
        print(f"Update_date: {update_date}")
        print(f"Última venta: {ultima_venta}")
        print(f"Razón de exclusión: {razon}")
        print("-" * 80)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        analizar_productos_sin_aviso()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
