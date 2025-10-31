#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pal.infrastructure.database import DatabaseManager

db = DatabaseManager()

query = """
SELECT 
    i.name AS NombreIndice,
    c.name AS Columna,
    ic.key_ordinal AS Posicion,
    ic.is_included_column AS EsInclude
FROM sys.indexes i
INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE OBJECT_NAME(i.object_id) IN ('TR_INVENTARIO', 'MA_PRODUCTOS')
ORDER BY NombreIndice, ic.key_ordinal, ic.is_included_column
"""

try:
    indices = db.fetch_data(query)
    if indices:
        print('✓ Indices encontrados en TR_INVENTARIO y MA_PRODUCTOS:')
        for row in indices:
            print(f'  - {row}')
    else:
        print('✗ No se encontraron índices de optimización')
except Exception as e:
    print(f'Error consultando índices: {e}')
    import traceback
    traceback.print_exc()
