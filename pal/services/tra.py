"""
Módulo de gestión TRA (Tiempo de Reposición de Artículos) para la aplicación PAL
"""
import math
from datetime import datetime


def filter_ventas_tra(ventas, dept_code=None, group_code=None, sub_code=None, 
                     search_text="", filter_rotacion="TODAS", favoritos=None):
    """
    Filtra los datos de ventas TRA según múltiples criterios
    
    Args:
        ventas: Lista de datos de ventas desde cache
        dept_code: Código de departamento a filtrar
        group_code: Código de grupo a filtrar
        sub_code: Código de subgrupo a filtrar
        search_text: Texto para buscar en código/descripción
        filter_rotacion: Tipo de rotación ('TODAS', 'ALTA', 'MEDIA', 'BAJA', etc.)
        favoritos: Set de códigos favoritos
        
    Returns:
        list: Lista filtrada de datos de ventas
    """
    if not ventas:
        return []
        
    datos_filtrados = list(ventas)
    favoritos = favoritos or set()
    
    # Filtro jerárquico por departamento, grupo y subgrupo
    if dept_code:
        datos_filtrados = [
            r for r in datos_filtrados 
            if len(r) > 2 and str(r[2]) == str(dept_code)
        ]
    
    if group_code:
        datos_filtrados = [
            r for r in datos_filtrados 
            if len(r) > 3 and str(r[3]) == str(group_code)
        ]
        
    if sub_code:
        datos_filtrados = [
            r for r in datos_filtrados 
            if len(r) > 4 and str(r[4]) == str(sub_code)
        ]
    
    # Filtro de texto en descripción y código
    texto_busqueda = search_text.strip().lower()
    if texto_busqueda:
        datos_filtrados = [
            r for r in datos_filtrados 
            if len(r) > 1 and (
                texto_busqueda in str(r[0]).lower() or 
                texto_busqueda in str(r[1]).lower()
            )
        ]
    
    # Filtro de rotación (si se implementa en el futuro)
    if filter_rotacion != "TODAS":
        datos_filtrados = [
            r for r in datos_filtrados 
            if len(r) > 6 and str(r[6]).upper() == filter_rotacion.upper()
        ]
    
    # Ordenar por favoritos (favoritos primero), luego por neto descendente
    datos_ordenados = sorted(
        datos_filtrados,
        key=lambda x: (
            str(x[0]) not in favoritos,  # Favoritos primero
            -_get_tra_neto(x)  # Neto descendente
        )
    )
    
    return datos_ordenados


def paginate_tra(datos, current_page, page_size):
    """
    Realiza paginación específica para datos TRA
    
    Args:
        datos: Lista de datos TRA a paginar
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


def calcular_porcentajes_representacion(ventas_data):
    """
    Calcula porcentajes de representación para cada producto
    
    Args:
        ventas_data: Lista completa de datos de ventas
        
    Returns:
        dict: Mapeo código -> porcentaje de representación
    """
    if not ventas_data:
        return {}
        
    try:
        # Calcular total de ventas
        total_ventas = sum(_get_tra_neto(item) for item in ventas_data)
        
        if total_ventas <= 0:
            return {}
        
        # Calcular porcentaje para cada producto
        porcentajes = {}
        for item in ventas_data:
            codigo = str(item[0])
            neto = _get_tra_neto(item)
            porcentaje = (neto / total_ventas) * 100 if total_ventas > 0 else 0.0
            porcentajes[codigo] = round(porcentaje, 2)
            
        return porcentajes
        
    except Exception as e:
        print(f"Error calculando porcentajes: {e}")
        return {}


def _get_tra_neto(item):
    """
    Extrae el valor neto de un item TRA de forma segura
    
    Args:
        item: Tupla/lista con datos TRA
        
    Returns:
        float: Valor neto del item
    """
    try:
        if not item or len(item) < 6:
            return 0.0
        
        neto = item[5]  # El neto está en el índice 5 según el patrón de recup.py
        return float(neto) if neto is not None else 0.0
        
    except (ValueError, TypeError, IndexError):
        return 0.0


def clasificar_rotacion_tra(ventas_data, total_ventas=None):
    """
    Clasifica productos según su rotación basado en ventas
    
    Args:
        ventas_data: Lista de datos de ventas
        total_ventas: Total opcional de ventas para cálculo de porcentajes
        
    Returns:
        list: Lista de ventas con clasificación de rotación añadida
    """
    if not ventas_data:
        return []
        
    try:
        # Calcular total si no se proporciona
        if total_ventas is None:
            total_ventas = sum(_get_tra_neto(item) for item in ventas_data)
        
        if total_ventas <= 0:
            # Si no hay ventas, clasificar todo como SIN CLASIFICAR
            return [
                list(item) + ['SIN CLASIFICAR'] if len(item) == 6 else list(item)
                for item in ventas_data
            ]
        
        # Clasificar según porcentaje de participación
        ventas_clasificadas = []
        for item in ventas_data:
            item_list = list(item)
            neto = _get_tra_neto(item)
            porcentaje = (neto / total_ventas) * 100
            
            # Clasificación según rangos de porcentaje
            if porcentaje >= 5.0:
                rotacion = "ALTA"
            elif porcentaje >= 1.0:
                rotacion = "MEDIA" 
            elif porcentaje > 0:
                rotacion = "BAJA"
            else:
                rotacion = "SIN MOVIMIENTO"
            
            # Añadir rotación si no existe
            if len(item_list) == 6:
                item_list.append(rotacion)
            elif len(item_list) > 6:
                item_list[6] = rotacion
                
            ventas_clasificadas.append(tuple(item_list))
        
        return ventas_clasificadas
        
    except Exception as e:
        print(f"Error clasificando rotación: {e}")
        return list(ventas_data)


def obtener_stock_ideal_tra(neto_ventas, dias_periodo=365, dias_buffer=30):
    """
    Calcula stock ideal basado en ventas netas
    
    Args:
        neto_ventas: Ventas netas del producto
        dias_periodo: Días del periodo analizado (default 365)
        dias_buffer: Días de buffer adicional (default 30)
        
    Returns:
        int: Stock ideal calculado
    """
    try:
        if neto_ventas <= 0:
            return 0
            
        # Calcular promedio diario
        promedio_diario = neto_ventas / dias_periodo
        
        # Stock ideal = promedio diario * días de buffer
        stock_ideal = promedio_diario * dias_buffer
        
        return max(1, int(round(stock_ideal)))
        
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


# Alias para compatibilidad con código existente
clasificar_rotacion = clasificar_rotacion_tra
