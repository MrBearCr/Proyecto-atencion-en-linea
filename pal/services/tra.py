"""
Módulo de gestión TRA (Tiempo de Reposición de Artículos) para la aplicación PAL
"""
import math
from datetime import datetime
from .filters import filter_by_hierarchy
from pal.core.log import get_logger

logger = get_logger("TRA")


def filter_ventas_tra(ventas, dept_code=None, group_code=None, sub_code=None, 
                     search_text="", filter_rotacion="TODAS", favoritos=None, alertas_stock=None):
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
        alertas_stock: Lista de tuplas (codigo, desc, stock, nivel) de productos en alerta
        
    Returns:
        list: Lista filtrada de datos de ventas, ordenada por: favoritos+alerta, alerta, neto descendente
    """
    if not ventas:
        return []
        
    datos_filtrados = list(ventas)
    favoritos = favoritos or set()
    alertas_stock = alertas_stock or []
    
    # Crear set de códigos en alerta para búsqueda rápida
    codigos_alerta = {str(alerta[0]).strip() for alerta in alertas_stock}
    
    # Filtro jerárquico unificado (lee jerarquía desde el propio registro: idx 2,3,4)
    datos_filtrados = filter_by_hierarchy(
        datos_filtrados,
        dept_code=dept_code,
        group_code=group_code,
        sub_code=sub_code,
        get_dept=lambda r: r[2] if len(r) > 2 else None,
        get_group=lambda r: r[3] if len(r) > 3 else None,
        get_sub=lambda r: r[4] if len(r) > 4 else None,
        missing_strategy="exclude",
    )
    
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
    
    # Ordenar con prioridad: Favoritos > Rotación (ALTA > MEDIA > BAJA) > Alertas > Neto
    def _get_rotacion(item):
        """Extrae rotación de forma segura"""
        try:
            if len(item) > 6:
                rotacion = str(item[6]).upper()
                if rotacion == 'ALTA':
                    return 0  # Prioridad más alta
                elif rotacion == 'MEDIA':
                    return 1
                elif rotacion == 'BAJA':
                    return 2
            return 3  # Sin clasificación
        except:
            return 3
    
    datos_ordenados = sorted(
        datos_filtrados,
        key=lambda x: (
            # 1. Favoritos primero (False=0 < True=1)
            str(x[0]) not in favoritos,
            # 2. Rotación (ALTA=0, MEDIA=1, BAJA=2)
            _get_rotacion(x),
            # 3. Alerta de stock (con alerta primero: False=0 < True=1)
            str(x[0]) not in codigos_alerta,
            # 4. Neto descendente (negativo para orden inverso)
            -_get_tra_neto(x)
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
        logger.error(f"Error calculando porcentajes: {e}")
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
    Clasifica productos según su rotación basado en porcentaje acumulado de ventas
    Implementación optimizada con cache y manejo eficiente de memoria
    
    Args:
        ventas_data: Lista de datos de ventas
        total_ventas: Total opcional de ventas para cálculo de porcentajes
        
    Returns:
        list: Lista de ventas con clasificación de rotación añadida
        
    Criterios de clasificación (Curva ABC optimizada):
        - ALTA: productos en el primer 80% del neto acumulado
        - MEDIA: productos entre 80% y 95% del neto acumulado  
        - BAJA: productos desde 95% hasta 100% del neto acumulado
    """
    if not ventas_data:
        return []
        
    try:
        # Validación rápida de entrada
        if not isinstance(ventas_data, (list, tuple)):
            return list(ventas_data) if ventas_data else []
        
        # Calcular total si no se proporciona (optimizado con generator)
        if total_ventas is None:
            total_ventas = sum(_get_tra_neto(item) for item in ventas_data if item)
        
        if total_ventas <= 0:
            # Si no hay ventas, clasificar todo como SIN CLASIFICAR
            return [
                list(item) + ['SIN CLASIFICAR'] if len(item) == 6 else list(item)
                for item in ventas_data if item
            ]
        
        # Pre-calcular netos para evitar múltiples llamadas a _get_tra_neto
        items_con_neto = [(item, _get_tra_neto(item)) for item in ventas_data if item]
        
        # Ordenar por neto descendente (más eficiente)
        items_con_neto.sort(key=lambda x: x[1], reverse=True)
        
        # Calcular porcentajes acumulados y clasificar (optimizado)
        neto_acumulado = 0.0
        ventas_clasificadas = []
        total_ventas_inv = 1.0 / total_ventas  # Pre-calcular inverso para evitar divisiones
        
        for item, neto in items_con_neto:
            neto_acumulado += neto
            porcentaje_acumulado = neto_acumulado * total_ventas_inv * 100
            
            # Clasificación según porcentaje acumulado (optimizada con elif)
            if porcentaje_acumulado <= 80.0:
                rotacion = "ALTA"
            elif porcentaje_acumulado <= 95.0:
                rotacion = "MEDIA"
            else:
                rotacion = "BAJA"
            
            # Convertir a lista mutable para permitir mutaciones (pyodbc.Row no soporta append)
            try:
                item_list = list(item)
            except Exception:
                # Fallback: intentar copiar por slicing y convertir
                item_list = list(item[:]) if hasattr(item, '__getitem__') else [item]
            
            if len(item_list) == 6:
                item_list.append(rotacion)
            elif len(item_list) > 6:
                item_list[6] = rotacion
            else:
                # Completar con valores por defecto si es necesario
                while len(item_list) < 6:
                    item_list.append(None)
                item_list.append(rotacion)
                
            ventas_clasificadas.append(tuple(item_list))
        
        return ventas_clasificadas
        
    except Exception as e:
        logger.error(f"Error clasificando rotación: {e}")
        return list(ventas_data) if ventas_data else []


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


def detectar_alertas_rotacion_alta(ventas_clasificadas, alertas_stock, rotaciones_objetivo=["ALTA", "MEDIA"]):
    """
    Detecta productos de alta/media rotación que tienen alerta de stock
    Para alertar al departamento de compras sobre productos críticos sin stock
    
    Args:
        ventas_clasificadas: Lista de ventas con clasificación de rotación
        alertas_stock: Diccionario {codigo: (descripcion, stock, nivel_alerta)}
        rotaciones_objetivo: Lista de rotaciones a monitorear (default: ALTA, MEDIA)
        
    Returns:
        list: Lista de productos críticos [(codigo, descripcion, stock, nivel, rotacion), ...]
    """
    try:
        productos_criticos = []
        
        # Crear mapa de alertas para búsqueda rápida
        alertas_map = {str(r[0]).strip(): r for r in alertas_stock} if alertas_stock else {}
        
        for venta in ventas_clasificadas:
            if not venta or len(venta) < 7:
                continue
                
            codigo = str(venta[0]).strip()
            descripcion = str(venta[1]) if len(venta) > 1 else ""
            rotacion = str(venta[6]) if len(venta) > 6 else "BAJA"
            
            # Si el producto tiene rotación objetivo y está en alertas
            if rotacion in rotaciones_objetivo and codigo in alertas_map:
                alerta = alertas_map[codigo]
                # alerta = (codigo, descripcion, stock, nivel_alerta)
                if len(alerta) >= 4:
                    stock = alerta[2]
                    nivel_alerta = alerta[3]
                    productos_criticos.append({
                        'codigo': codigo,
                        'descripcion': descripcion,
                        'stock': stock,
                        'nivel': nivel_alerta,
                        'rotacion': rotacion
                    })
        
        return productos_criticos
        
    except Exception as e:
        logger.error(f"Error detectando alertas de rotación: {e}")
        return []


def generar_reporte_critico_rotacion(productos_criticos):
    """
    Genera un reporte resumido para el departamento de compras
    
    Args:
        productos_criticos: Lista de productos críticos
        
    Returns:
        dict: Reporte con estadísticas y listado
    """
    try:
        if not productos_criticos:
            return {
                'total': 0,
                'por_rotacion': {},
                'por_nivel': {},
                'productos': []
            }
        
        reporte = {
            'total': len(productos_criticos),
            'por_rotacion': {},
            'por_nivel': {},
            'productos': productos_criticos
        }
        
        # Contar por rotación
        for p in productos_criticos:
            rotacion = p.get('rotacion', 'DESCONOCIDO')
            reporte['por_rotacion'][rotacion] = reporte['por_rotacion'].get(rotacion, 0) + 1
            
            nivel = p.get('nivel', 'DESCONOCIDO')
            reporte['por_nivel'][nivel] = reporte['por_nivel'].get(nivel, 0) + 1
        
        return reporte
        
    except Exception as e:
        logger.error(f"Error generando reporte crítico: {e}")
        return {'total': 0, 'por_rotacion': {}, 'por_nivel': {}, 'productos': []}


# Alias para compatibilidad con código existente
clasificar_rotacion = clasificar_rotacion_tra
