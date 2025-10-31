"""
Módulo de servicios MBRP (Movimiento de Baja Rotación de Producto)
Enfocado en productos con baja rotación e índices de movilidad cercanos a 0%
"""
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from pal.core.log import get_logger

logger = get_logger("MBRP")


def calcular_indice_movilidad(ventas_data: List, total_ventas_periodo: float = None) -> Dict[str, float]:
    """
    Calcula el Índice de Movilidad (IM) para cada producto.
    
    Args:
        ventas_data: Lista de datos de ventas con formato (codigo, desc, dept, group, sub, neto, ...)
        total_ventas_periodo: Total de ventas del período (opcional, se calcula si no se proporciona)
        
    Returns:
        dict: Mapeo código -> índice de movilidad (0-100%)
        
    El IM se calcula como:
    - 100% = Producto con máximas ventas
    - 0% = Producto sin ventas o con ventas netas <= 0
    """
    if not ventas_data:
        logger.debug(f"[CALC IM] ventas_data vacía")
        return {}
    
    try:
        logger.debug(f"[CALC IM] Iniciando cálculo IM para {len(ventas_data)} productos")
        
        # Extraer ventas por código
        ventas_por_codigo = {}
        items_invalidos = 0
        
        for item in ventas_data:
            if len(item) >= 6:
                codigo = str(item[0])
                # El neto siempre está en item[5], independiente de clasificación
                try:
                    neto = float(item[5]) if item[5] is not None else 0.0
                    ventas_por_codigo[codigo] = neto
                except (ValueError, TypeError) as e:
                    logger.warning(f"[CALC IM] Neto inválido para {codigo}: {item[5]} - {e}")
                    ventas_por_codigo[codigo] = 0.0
            else:
                items_invalidos += 1
        
        logger.debug(f"[CALC IM] Extraídos {len(ventas_por_codigo)} productos válidos, {items_invalidos} items inválidos")
        
        if not ventas_por_codigo:
            logger.warning(f"[CALC IM] No se extrajeron ventas válidas")
            return {}
        
        # Filtrar solo productos con ventas positivas para el cálculo del IM
        ventas_positivas = {k: v for k, v in ventas_por_codigo.items() if v > 0}
        
        logger.debug(f"[CALC IM] Productos con ventas positivas: {len(ventas_positivas)}/{len(ventas_por_codigo)}")
        
        # Si no hay ventas positivas, todos tienen IM = 0
        if not ventas_positivas:
            logger.info(f"[CALC IM] Ningún producto con ventas positivas - asignando IM=0 a todos")
            return {codigo: 0.0 for codigo in ventas_por_codigo.keys()}
        
        # Encontrar máximo y mínimo para normalización (solo de ventas positivas)
        max_ventas = max(ventas_positivas.values())
        min_ventas_positivas = min(ventas_positivas.values())
        
        logger.debug(f"[CALC IM] Rango de ventas: min={min_ventas_positivas}, max={max_ventas}")
        
        # Evitar división por cero
        rango_ventas = max_ventas - min_ventas_positivas
        if rango_ventas == 0:
            # Todos los productos con ventas tienen las mismas ventas
            logger.info(f"[CALC IM] Todas las ventas iguales - asignando IM=50% a productos con ventas")
            indices = {codigo: 50.0 for codigo in ventas_positivas.keys()}
            # Productos sin ventas tienen IM = 0
            for codigo in ventas_por_codigo:
                if codigo not in indices:
                    indices[codigo] = 0.0
            return indices
        
        # Calcular IM para cada producto
        indices_movilidad = {}
        for codigo, ventas in ventas_por_codigo.items():
            if ventas <= 0:
                # Productos sin ventas o con neto negativo tienen IM = 0
                indices_movilidad[codigo] = 0.0
            else:
                # IM = (ventas - min_positivas) / (max_ventas - min_positivas) * 100
                im = ((ventas - min_ventas_positivas) / rango_ventas) * 100
                # Asegurar que el IM mínimo para productos con ventas sea > 0.1%
                indices_movilidad[codigo] = max(0.1, round(im, 1))
        
        logger.debug(f"[CALC IM] Cálculo completado: {len(indices_movilidad)} índices generados")
        return indices_movilidad
        
    except Exception as e:
        logger.error(f"[CALC IM] Error calculando índices de movilidad: {e}", exc_info=True)
        return {}


def obtener_fecha_ultima_venta(db_manager, codigo_producto: str, sede_codigo: str = None) -> Optional[datetime]:
    """
    Obtiene la fecha de la última venta de un producto específico.
    
    Args:
        db_manager: Instancia del DatabaseManager
        codigo_producto: Código del producto
        sede_codigo: Código de sede (opcional)
        
    Returns:
        datetime: Fecha de última venta o None si no hay ventas
    """
    try:
        query = """
        SELECT TOP 1 f_fecha 
        FROM TR_INVENTARIO 
        WHERE c_Codarticulo = ? 
        AND c_Concepto = 'VEN'
        AND n_Cantidad > 0
        """
        params = [codigo_producto]
        
        if sede_codigo:
            query += " AND c_Deposito LIKE ?"
            params.append(sede_codigo)
            
        query += " ORDER BY f_fecha DESC"
        
        result = db_manager.fetch_data(query, params)
        
        if result and len(result) > 0:
            return result[0][0]  # Primera columna del primer resultado
        
        return None
        
    except Exception as e:
        logger.error(f"Error obteniendo última venta para {codigo_producto}: {e}")
        return None


def obtener_ultimas_ventas_bulk(db_manager, codigos_productos: List[str], sede_codigo: str = None) -> Dict[str, datetime]:
    """
    Obtiene las fechas de última venta para múltiples productos de forma eficiente.
    Procesa los productos en lotes para evitar el límite de 2100 parámetros de SQL Server.
    
    Args:
        db_manager: Instancia del DatabaseManager
        codigos_productos: Lista de códigos de productos
        sede_codigo: Código de sede (opcional)
        
    Returns:
        dict: Mapeo código -> fecha de última venta
        
    Nota: Busca única y exclusivamente registros de VENTAS (c_Concepto = 'VEN').
    No considera devoluciones. Si un producto tiene neto > 0 pero no se encuentra
    en esta consulta, es porque todas sus transacciones fueron devoluciones.
    """
    if not codigos_productos:
        return {}
    
    # Límite de parámetros SQL Server (2100) - usamos 2000 para dejar margen
    BATCH_SIZE = 2000
    ultimas_ventas = {}
    
    try:
        # Procesar en lotes para evitar el límite de parámetros
        for i in range(0, len(codigos_productos), BATCH_SIZE):
            batch_codigos = codigos_productos[i:i + BATCH_SIZE]
            
            # Crear placeholders para la consulta IN del lote actual
            placeholders = ','.join(['?' for _ in batch_codigos])
            
            # Buscar única y exclusivamente transacciones de VENTA
            query = f"""
            SELECT c_Codarticulo, MAX(f_fecha) as ultima_venta
            FROM TR_INVENTARIO WITH (NOLOCK)
            WHERE c_Codarticulo IN ({placeholders})
            AND c_Concepto = 'VEN'
            AND n_Cantidad > 0
            """
            params = list(batch_codigos)
            
            if sede_codigo:
                query += " AND c_Deposito LIKE ?"
                params.append(sede_codigo)
                
            query += " GROUP BY c_Codarticulo"
            
            logger.debug(f"Procesando lote {i//BATCH_SIZE + 1} con {len(batch_codigos)} productos")
            
            result = db_manager.fetch_data(query, params)
            
            if result:
                for row in result:
                    codigo = str(row[0])
                    fecha = row[1]
                    ultimas_ventas[codigo] = fecha
        
        logger.info(f"Procesados {len(codigos_productos)} productos - {len(ultimas_ventas)} con últimas ventas encontradas")
        return ultimas_ventas
        
    except Exception as e:
        logger.error(f"Error obteniendo últimas ventas bulk: {e}")
        return {}


def calcular_dias_sin_venta(fecha_ultima_venta: Optional[datetime]) -> int:
    """
    Calcula los días transcurridos desde la última venta.
    
    Args:
        fecha_ultima_venta: Fecha de la última venta
        
    Returns:
        int: Días sin venta (0 si fue hoy, -1 si nunca se vendió)
    """
    if fecha_ultima_venta is None:
        return -1  # Nunca se vendió
    
    try:
        hoy = datetime.now().date()
        ultima_venta_date = fecha_ultima_venta.date() if hasattr(fecha_ultima_venta, 'date') else fecha_ultima_venta
        
        diferencia = hoy - ultima_venta_date
        return diferencia.days
        
    except Exception as e:
        logger.error(f"Error calculando días sin venta: {e}")
        return -1


def filtrar_productos_baja_rotacion(ventas_data: List, umbral_im: float = 20.0) -> List:
    """
    Filtra productos con Índice de Movilidad bajo para el módulo MBRP.
    
    Args:
        ventas_data: Lista de datos de ventas (puede incluir clasificación en posición 6)
        umbral_im: Umbral de IM por debajo del cual se considera baja rotación
        
    Returns:
        list: Productos filtrados con baja rotación, ordenados por IM ascendente
    """
    if not ventas_data:
        logger.warning(f"[MBRP FILTER] ventas_data vacía")
        return []
    
    try:
        logger.info(f"[MBRP FILTER] Iniciando filtrado: {len(ventas_data)} productos, umbral_im={umbral_im}%")
        
        # Verificar estructura de datos
        primera_fila = ventas_data[0] if ventas_data else None
        if primera_fila:
            logger.debug(f"[MBRP FILTER] Primera fila: {primera_fila}, len={len(primera_fila)}")
        
        # Calcular IM para todos los productos (usa item[5] que siempre es neto)
        indices_movilidad = calcular_indice_movilidad(ventas_data)
        logger.info(f"[MBRP FILTER] Índices de movilidad calculados: {len(indices_movilidad)} productos")
        
        if not indices_movilidad:
            logger.warning(f"[MBRP FILTER] No se pudieron calcular índices de movilidad (datos recibidos: {len(ventas_data)} productos)")
            # Debug: verificar qué hay en ventas_data
            if ventas_data:
                logger.debug(f"[MBRP FILTER] Primeros 3 items: {ventas_data[:3]}")
            return []
        
        # Filtrar productos con IM bajo o igual al umbral
        productos_baja_rotacion = []
        im_stats = {'filtrados': 0, 'excluidos': 0, 'sin_im': 0}
        
        for item in ventas_data:
            if len(item) >= 6:
                codigo = str(item[0])
                im = indices_movilidad.get(codigo, 0.0)
                
                # Incluir solo productos con IM por debajo o igual al umbral
                if im <= umbral_im:
                    productos_baja_rotacion.append(item)
                    im_stats['filtrados'] += 1
                else:
                    im_stats['excluidos'] += 1
            else:
                im_stats['sin_im'] += 1
                logger.warning(f"[MBRP FILTER] Item incompleto: {item}")
        
        # Ordenar por IM ascendente (los de menor movilidad primero)
        productos_baja_rotacion.sort(key=lambda x: indices_movilidad.get(str(x[0]), 0.0))
        
        logger.info(f"[MBRP FILTER] Resultados: {im_stats['filtrados']} filtrados, {im_stats['excluidos']} excluidos, {im_stats['sin_im']} incompletos (total entrada: {len(ventas_data)})")
        
        return productos_baja_rotacion
        
    except Exception as e:
        logger.error(f"[MBRP FILTER] Error filtrando productos de baja rotación: {e}", exc_info=True)
        # En caso de error, devolver lista vacía en lugar de todos los datos
        return []


def clasificar_rotacion_mbrp(ventas_data: List) -> List:
    """
    Clasifica productos según rotación específicamente para MBRP.
    Enfocado en identificar productos de BAJA rotación.
    
    Args:
        ventas_data: Lista de datos de ventas
        
    Returns:
        list: Lista con clasificación de rotación añadida
        
    Criterios MBRP (inversos a TRA):
    - SIN_MOVIMIENTO: IM = 0% (sin ventas o neto <= 0)
    - BAJA: IM <= 10% (muy poca rotación)
    - MEDIA: IM <= 30% (rotación moderadamente baja)  
    - ALTA: IM > 30% (se excluye normalmente del análisis MBRP)
    """
    if not ventas_data:
        logger.warning(f"[MBRP CLASSIFY] ventas_data vacía")
        return []
    
    try:
        logger.info(f"[MBRP CLASSIFY] Iniciando clasificación: {len(ventas_data)} productos")
        
        # Verificar estructura de datos
        primera_fila = ventas_data[0] if ventas_data else None
        if primera_fila:
            logger.debug(f"[MBRP CLASSIFY] Primera fila: {primera_fila}, len={len(primera_fila)}")
        
        # Calcular índices de movilidad
        indices_movilidad = calcular_indice_movilidad(ventas_data)
        logger.info(f"[MBRP CLASSIFY] Índices de movilidad calculados: {len(indices_movilidad)} productos")
        
        if not indices_movilidad:
            logger.warning(f"[MBRP CLASSIFY] No se pudieron calcular índices de movilidad para clasificación (datos: {len(ventas_data)})")
            return list(ventas_data)
        
        ventas_clasificadas = []
        clasificacion_stats = {'sin_movimiento': 0, 'baja': 0, 'media': 0, 'alta': 0, 'incompletos': 0}
        
        for item in ventas_data:
            if len(item) < 6:
                logger.warning(f"[MBRP CLASSIFY] Item con menos de 6 campos: {item}")
                clasificacion_stats['incompletos'] += 1
                continue
                
            codigo = str(item[0])
            im = indices_movilidad.get(codigo, 0.0)
            neto = float(item[5]) if item[5] is not None else 0.0
            
            # Clasificación específica para MBRP (enfoque en baja rotación)
            # SIN_MOVIMIENTO: IM = 0% O neto <= 0
            if im == 0.0 or neto <= 0:
                rotacion = "SIN_MOVIMIENTO"
                clasificacion_stats['sin_movimiento'] += 1
            elif im <= 10.0:
                rotacion = "BAJA"
                clasificacion_stats['baja'] += 1
            elif im <= 30.0:
                rotacion = "MEDIA"
                clasificacion_stats['media'] += 1
            else:
                rotacion = "ALTA"  # Normalmente se filtraría en MBRP
                clasificacion_stats['alta'] += 1
            
            # Convertir a lista mutable y añadir clasificación
            try:
                item_list = list(item)
            except Exception:
                item_list = list(item[:]) if hasattr(item, '__getitem__') else [item]
            
            # Asegurar que siempre se añade o reemplaza la clasificación en posición 6
            if len(item_list) == 6:
                item_list.append(rotacion)
            elif len(item_list) > 6:
                # Ya tiene clasificación, reemplazarla
                item_list[6] = rotacion
            else:
                # Completar con valores por defecto hasta tener 6 campos
                while len(item_list) < 6:
                    item_list.append(None)
                item_list.append(rotacion)
            
            ventas_clasificadas.append(tuple(item_list))
        
        logger.info(f"[MBRP CLASSIFY] Clasificación completada: {len(ventas_clasificadas)} productos (SIN_MOVIMIENTO: {clasificacion_stats['sin_movimiento']}, BAJA: {clasificacion_stats['baja']}, MEDIA: {clasificacion_stats['media']}, ALTA: {clasificacion_stats['alta']}, incompletos: {clasificacion_stats['incompletos']})")
        return ventas_clasificadas
        
    except Exception as e:
        logger.error(f"[MBRP CLASSIFY] Error clasificando rotación MBRP: {e}", exc_info=True)
        return list(ventas_data) if ventas_data else []


def generar_reporte_baja_rotacion(ventas_data: List, db_manager, sede_codigo: str = None) -> Dict:
    """
    Genera un reporte completo de productos de baja rotación.
    
    Args:
        ventas_data: Datos de ventas
        db_manager: DatabaseManager instance
        sede_codigo: Código de sede
        
    Returns:
        dict: Reporte con estadísticas y recomendaciones
    """
    try:
        if not ventas_data:
            return {"error": "No hay datos disponibles"}
        
        # Calcular métricas
        indices_movilidad = calcular_indice_movilidad(ventas_data)
        codigos = [str(item[0]) for item in ventas_data if len(item) >= 6]
        ultimas_ventas = obtener_ultimas_ventas_bulk(db_manager, codigos, sede_codigo)
        
        # Clasificar productos
        sin_movimiento = sum(1 for im in indices_movilidad.values() if im == 0.0)
        baja_rotacion = sum(1 for im in indices_movilidad.values() if 0.0 < im <= 10.0)
        media_rotacion = sum(1 for im in indices_movilidad.values() if 10.0 < im <= 30.0)
        alta_rotacion = sum(1 for im in indices_movilidad.values() if im > 30.0)
        
        # Productos críticos (más de 90 días sin venta y IM muy bajo)
        productos_criticos = []
        for item in ventas_data:
            if len(item) >= 6:
                codigo = str(item[0])
                im = indices_movilidad.get(codigo, 0.0)
                ultima_venta = ultimas_ventas.get(codigo)
                dias_sin_venta = calcular_dias_sin_venta(ultima_venta)
                
                if im <= 5.0 and dias_sin_venta > 90:
                    productos_criticos.append({
                        'codigo': codigo,
                        'descripcion': str(item[1]),
                        'im': im,
                        'dias_sin_venta': dias_sin_venta
                    })
        
        return {
            "total_productos": len(ventas_data),
            "sin_movimiento": sin_movimiento,
            "baja_rotacion": baja_rotacion,
            "media_rotacion": media_rotacion,
            "alta_rotacion": alta_rotacion,
            "productos_criticos": len(productos_criticos),
            "detalle_criticos": productos_criticos[:10],  # Top 10 más críticos
            "porcentaje_baja_rotacion": round((baja_rotacion + sin_movimiento) / len(ventas_data) * 100, 1)
        }
        
    except Exception as e:
        logger.error(f"Error generando reporte: {str(e)}")
        return {"error": f"Error generando reporte: {str(e)}"}
