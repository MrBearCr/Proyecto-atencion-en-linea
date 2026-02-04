from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List, Dict, Optional
from datetime import date, datetime, timedelta
from app.models import MaProductosDB, TrInventarioDB, ProductoMBRP, MBRPReportSummary
from app.crud.tra_crud import get_tra_sales_data
import logging

logger = logging.getLogger(__name__)

def calculate_im(ventas_data: List) -> Dict[str, float]:
    """
    Calculates Índice de Movilidad (IM) based on cumulative percentage of net sales.
    Replicates logic from pal/services/mbrp.py
    """
    if not ventas_data:
        return {}
    
    # Sort by net sales descending
    sorted_ventas = sorted(ventas_data, key=lambda x: x.ventas_netas, reverse=True)
    
    # Only positive sales count for accumulation
    ventas_positivas = [v for v in sorted_ventas if v.ventas_netas > 0]
    total_neto = sum(v.ventas_netas for v in ventas_positivas)
    
    if total_neto <= 0:
        return {v.codigo: 0.0 for v in sorted_ventas}
    
    indices = {}
    neto_acumulado = 0.0
    for v in ventas_positivas:
        neto_acumulado += v.ventas_netas
        pct_acumulado = (neto_acumulado / total_neto) * 100
        # IM = 100 - % acumulado
        im = max(0.1, round(100.0 - pct_acumulado, 1))
        indices[v.codigo] = im
        
    # Assign 0.0 to those with zero or negative sales
    for v in sorted_ventas:
        if v.codigo not in indices:
            indices[v.codigo] = 0.0
            
    return indices

def get_mbrp_report(
    db: Session,
    start_date: date,
    end_date: date,
    sede_codigo: str = "00",
    umbral_im: float = 20.0
) -> MBRPReportSummary:
    """
    Generates MBRP report data.
    """
    try:
        # 1. Fetch sales data (reusing TRA logic for base data)
        # We fetch a larger chunk or all for calculation
        all_ventas = get_tra_sales_data(
            db=db, 
            start_date=start_date, 
            end_date=end_date, 
            sede_codigo=sede_codigo,
            page=1,
            page_size=5000 # Fetch up to 5000 for summary
        )
        
        if not all_ventas:
            return MBRPReportSummary(
                total_productos=0,
                sin_movimiento=0,
                baja_rotacion=0,
                media_rotacion=0,
                alta_rotacion=0,
                productos_criticos=0,
                porcentaje_baja_rotacion=0.0
            )

        # 2. Calculate IM
        im_map = calculate_im(all_ventas)
        
        # 3. Classify and Filter
        sin_mov = 0
        baja = 0
        media = 0
        alta = 0
        criticos = []
        
        for v in all_ventas:
            im = im_map.get(v.codigo, 0.0)
            v.im_movilidad = im
            
            # Classification
            if im == 0:
                sin_mov += 1
                v.rotacion = "SIN_MOVIMIENTO"
            elif im <= 10:
                baja += 1
                v.rotacion = "BAJA"
            elif im <= 30:
                media += 1
                v.rotacion = "MEDIA"
            else:
                alta += 1
                v.rotacion = "ALTA"
                
            # Critical products (Placeholder for "Days without sales" logic)
            # In a real scenario, we would join with Last Sale Date
            if im <= 5.0:
                criticos.append(v)
                
        total = len(all_ventas)
        pct_baja = round((sin_mov + baja) / total * 100, 1) if total > 0 else 0.0
        
        return MBRPReportSummary(
            total_productos=total,
            sin_movimiento=sin_mov,
            baja_rotacion=baja,
            media_rotacion=media,
            alta_rotacion=alta,
            productos_criticos=len(criticos),
            porcentaje_baja_rotacion=pct_baja
        )

    except Exception as e:
        logger.error(f"Error generating MBRP report: {e}")
        raise
