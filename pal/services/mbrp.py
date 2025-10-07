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
    - 0% = Producto sin ventas o ventas mínimas
    """
    if not ventas_data:
        return {}
    
    try:
        # Extraer ventas por código
        ventas_por_codigo = {}
        for item in ventas_data:
            if len(item) >= 6:
                codigo = str(item[0])
                neto = float(item[5]) if item[5] is not None else 0.0
                ventas_por_codigo[codigo] = neto
        
        if not ventas_por_codigo:
            return {}
        
        # Encontrar máximo y mínimo para normalización
        ventas_values = list(ventas_por_codigo.values())
        max_ventas = max(ventas_values)
        min_ventas = min(ventas_values)
        
        # Evitar división por cero
        rango_ventas = max_ventas - min_ventas
        if rango_ventas == 0:
            # Todos tienen las mismas ventas
            return {codigo: 50.0 for codigo in ventas_por_codigo.keys()}
        
        # Calcular IM para cada producto (normalizado 0-100%)
        indices_movilidad = {}
        for codigo, ventas in ventas_por_codigo.items():
            # IM = (ventas - min_ventas) / (max_ventas - min_ventas) * 100
            im = ((ventas - min_ventas) / rango_ventas) * 100
            indices_movilidad[codigo] = round(im, 1)
        
        return indices_movilidad
        
    except Exception as e:
        logger.error(f"Error calculando índices de movilidad: {e}")
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
            
            query = f"""
            SELECT c_Codarticulo, MAX(f_fecha) as ultima_venta
            FROM TR_INVENTARIO 
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
        
        logger.info(f"Procesados {len(codigos_productos)} productos en {math.ceil(len(codigos_productos)/BATCH_SIZE)} lotes")
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
        ventas_data: Lista de datos de ventas
        umbral_im: Umbral de IM por debajo del cual se considera baja rotación
        
    Returns:
        list: Productos filtrados con baja rotación
    """
    if not ventas_data:
        return []
    
    try:
        # Calcular IM para todos los productos
        indices_movilidad = calcular_indice_movilidad(ventas_data)
        
        # Filtrar productos con IM bajo
        productos_baja_rotacion = []
        for item in ventas_data:
            if len(item) >= 6:
                codigo = str(item[0])
                im = indices_movilidad.get(codigo, 0.0)
                
                if im <= umbral_im:
                    productos_baja_rotacion.append(item)
        
        # Ordenar por IM ascendente (los de menor movilidad primero)
        productos_baja_rotacion.sort(key=lambda x: indices_movilidad.get(str(x[0]), 0.0))
        
        return productos_baja_rotacion
        
    except Exception as e:
        logger.error(f"Error filtrando productos de baja rotación: {e}")
        return ventas_data


def clasificar_rotacion_mbrp(ventas_data: List) -> List:
    """
    Clasifica productos según rotación específicamente para MBRP.
    Enfocado en identificar productos de BAJA rotación.
    
    Args:
        ventas_data: Lista de datos de ventas
        
    Returns:
        list: Lista con clasificación de rotación añadida
        
    Criterios MBRP (inversos a TRA):
    - SIN_MOVIMIENTO: IM = 0% (sin ventas)
    - BAJA: IM <= 10% (muy poca rotación)
    - MEDIA: IM <= 30% (rotación moderadamente baja)  
    - ALTA: IM > 30% (se excluye normalmente del análisis MBRP)
    """
    if not ventas_data:
        return []
    
    try:
        # Calcular índices de movilidad
        indices_movilidad = calcular_indice_movilidad(ventas_data)
        
        ventas_clasificadas = []
        for item in ventas_data:
            if len(item) < 6:
                continue
                
            codigo = str(item[0])
            im = indices_movilidad.get(codigo, 0.0)
            
            # Clasificación específica para MBRP (enfoque en baja rotación)
            if im == 0.0:
                rotacion = "SIN_MOVIMIENTO"
            elif im <= 10.0:
                rotacion = "BAJA"
            elif im <= 30.0:
                rotacion = "MEDIA"
            else:
                rotacion = "ALTA"  # Normalmente se filtraría en MBRP
            
            # Convertir a lista mutable y añadir clasificación
            try:
                item_list = list(item)
            except Exception:
                item_list = list(item[:]) if hasattr(item, '__getitem__') else [item]
            
            if len(item_list) == 6:
                item_list.append(rotacion)
            elif len(item_list) > 6:
                item_list[6] = rotacion
            else:
                # Completar con valores por defecto
                while len(item_list) < 6:
                    item_list.append(None)
                item_list.append(rotacion)
            
            ventas_clasificadas.append(tuple(item_list))
        
        return ventas_clasificadas
        
    except Exception as e:
        logger.error(f"Error clasificando rotación MBRP: {e}")
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
