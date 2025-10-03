"""
Módulo de gestión de stock para la aplicación PAL
"""

def get_existencias_por_ubicacion(codigo, depositos, db_manager):
    """
    Obtiene existencias de un producto en ubicaciones específicas
    
    Args:
        codigo: Código del producto
        depositos: Lista de códigos de depósito
        db_manager: Instancia de DatabaseManager
        
    Returns:
        int: Total de existencias
    """
    placeholders = ','.join('?' for _ in depositos)
    sql = (
        f"SELECT SUM(n_cantidad) "
        f"FROM MA_DEPOPROD "
        f"WHERE c_codarticulo = ? AND c_coddeposito IN ({placeholders})"
    )
    params = [codigo] + depositos
    result = db_manager.fetch_data(sql, params)
    return int(result[0][0] or 0)