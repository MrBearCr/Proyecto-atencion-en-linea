"""
Lógica de stock legada (niveles Crítica/Media/Leve)
"""

def fetch_stock_alerts_optimized(db_manager, depositos=None, limit=None, offset=0, use_indices=True):
    """
    Obtiene alertas de stock usando consulta optimizada con índices y paginación
    (DEPUREDO: Basado en niveles 15-50)
    """
    try:
        if not depositos:
            return []
            
        placeholders = ','.join(['?' for _ in depositos])
        
        base_query = f"""
        SELECT 
            p.C_CODIGO as codigo,
            COALESCE(p.cu_descripcion_corta, 'SIN DESCRIPCIÓN') as descripcion,
            SUM(ISNULL(d.n_cantidad, 0)) as stock,
            CASE 
                WHEN SUM(ISNULL(d.n_cantidad, 0)) <= 0 THEN 'CRÍTICA'
                WHEN SUM(ISNULL(d.n_cantidad, 0)) <= 15 THEN 'MEDIA'
                ELSE 'LEVE'
            END as nivel
        FROM MA_PRODUCTOS p {{index_hint}}
        LEFT JOIN MA_DEPOPROD d ON p.C_CODIGO = d.c_codarticulo AND d.c_coddeposito IN ({placeholders})
        WHERE p.C_ESTADO = 'A'
            AND p.C_CODIGO IS NOT NULL
            AND (p.cu_descripcion_corta IS NOT NULL AND LTRIM(RTRIM(p.cu_descripcion_corta)) <> '')
        GROUP BY p.C_CODIGO, p.cu_descripcion_corta
        HAVING SUM(ISNULL(d.n_cantidad, 0)) <= 50
        """
        
        index_hint = "WITH (NOLOCK)" if use_indices else ""
        query = base_query.format(index_hint=index_hint)
        query += "\nORDER BY SUM(ISNULL(d.n_cantidad, 0)) ASC, p.C_CODIGO"
        
        if limit is not None:
            if offset > 0:
                query += f"\nOFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
            else:
                query = f"SELECT TOP ({limit}) * FROM ({query}) AS subquery"
        
        result = db_manager.fetch_data(query, depositos)
        return result if result else []
    except Exception:
        return []

def filter_alertas_legacy(alertas, producto_jerarquia, dept_code=None, group_code=None, 
                   sub_code=None, search_text="", filter_level="TODAS", favoritos=None):
    """
    Filtra las alertas de stock según niveles Crítico/Medio/Leve (LEGACY)
    """
    if not alertas:
        return []
    # ... (Resto de la lógica de filtrado de niveles)
    return alertas
