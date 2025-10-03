"""
Módulo de gestión de stock para la aplicación PAL
"""
import json
import os
import math
from datetime import datetime, timedelta

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

def filter_alertas(alertas, producto_jerarquia, dept_code=None, group_code=None, 
                   sub_code=None, search_text="", filter_level="TODAS", favoritos=None):
    """
    Filtra las alertas de stock según múltiples criterios
    
    Args:
        alertas: Lista de alertas desde cache
        producto_jerarquia: Dict con jerarquía de productos 
        dept_code: Código de departamento a filtrar
        group_code: Código de grupo a filtrar
        sub_code: Código de subgrupo a filtrar
        search_text: Texto para buscar en código/descripción
        filter_level: Nivel de alerta ('TODAS', 'CRÍTICA', 'MEDIA', 'LEVE')
        favoritos: Set de códigos favoritos
        
    Returns:
        list: Lista filtrada de alertas
    """
    if not alertas:
        return []
        
    datos_filtrados = list(alertas)
    favoritos = favoritos or set()
    
    # Filtro jerárquico
    if any([dept_code, group_code, sub_code]):
        datos_filtrados = [
            r for r in datos_filtrados 
            if _coincide_jerarquia(r[0], producto_jerarquia, dept_code, group_code, sub_code)
        ]
    
    # Filtro de texto en descripción y código
    texto_busqueda = search_text.strip().lower()
    if texto_busqueda:
        datos_filtrados = [
            r for r in datos_filtrados 
            if texto_busqueda in (str(r[1]).lower() + str(r[0]).lower())
        ]
    
    # Filtro de nivel de alerta
    filtro_nivel = filter_level.upper()
    if filtro_nivel != 'TODAS':
        datos_filtrados = [r for r in datos_filtrados if str(r[3]).upper() == filtro_nivel]
    
    # Ordenar por favoritos (favoritos primero)
    datos_ordenados = sorted(
        datos_filtrados,
        key=lambda x: str(x[0]) not in favoritos  # Favoritos primero
    )
    
    return datos_ordenados

def _coincide_jerarquia(codigo, producto_jerarquia, dept_code, group_code, sub_code):
    """Helper function para filtro jerárquico optimizado"""
    jerarquia = producto_jerarquia.get(codigo)
    if not jerarquia:
        return False
    
    dep, grp, sub = jerarquia
    return (not dept_code or dep == dept_code) and \
           (not group_code or grp == group_code) and \
           (not sub_code or sub == sub_code)

def paginate(datos, current_page, page_size):
    """
    Realiza paginación de los datos
    
    Args:
        datos: Lista de datos a paginar
        current_page: Página actual (1-indexed)
        page_size: Tamaño de página
        
    Returns:
        tuple: (datos_pagina, total_paginas, pagina_actual)
    """
    if not datos:
        return [], 1, 1
        
    total_items = len(datos)
    total_paginas = max(1, math.ceil(total_items / page_size))
    
    # Asegurar que la página actual sea válida
    current_page = max(1, min(current_page, total_paginas))
    
    # Obtener slice de datos para la página actual
    inicio = (current_page - 1) * page_size
    fin = inicio + page_size
    datos_pagina = datos[inicio:fin]
    
    return datos_pagina, total_paginas, current_page

def load_all_jerarquia(db_manager, cache_file, cache_ttl_seconds):
    """
    Carga el mapeo completo de productos a jerarquía con caché local
    
    Args:
        db_manager: Instancia de DatabaseManager
        cache_file: Ruta del archivo de caché
        cache_ttl_seconds: TTL del caché en segundos
        
    Returns:
        dict: Mapeo de código producto -> (departamento, grupo, subgrupo)
    """
    try:
        # Verificar si existe caché válido
        if os.path.exists(cache_file):
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - mtime < timedelta(seconds=cache_ttl_seconds):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        # Cargar desde BD
        filas = db_manager.fetch_data(
            "SELECT C_CODIGO, C_DEPARTAMENTO, C_GRUPO, C_SUBGRUPO FROM MA_PRODUCTOS"
        )
        jerarquia = {fila[0]: (fila[1], fila[2], fila[3]) for fila in filas if all(fila)}
        
        # Guardar en caché
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(jerarquia, f, ensure_ascii=False)
            
        return jerarquia
        
    except Exception as e:
        print(f"Error cargando jerarquía: {e}")
        return {}

def build_producto_jerarquia(all_jerarquia, codigos_en_alerta):
    """
    Filtra la jerarquía usando solo los códigos actualmente en alerta
    
    Args:
        all_jerarquia: Dict completo de jerarquía
        codigos_en_alerta: Set de códigos que están en alerta
        
    Returns:
        dict: Jerarquía filtrada solo con códigos en alerta
    """
    if not all_jerarquia or not codigos_en_alerta:
        return {}
        
    return {cod: all_jerarquia[cod] for cod in codigos_en_alerta if cod in all_jerarquia}
