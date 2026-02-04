from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional
from app.models import StockAlert, MaDepoProdDB, MaProductosDB
import logging

logger = logging.getLogger(__name__)

def get_stock_alerts(
    db: Session, 
    sede_codigo: str = "0301", # Default to Barquisimeto/Cabudare? Or first available
    limit: int = 500
) -> List[StockAlert]:
    """
    Fetches live stock alerts from MA_DEPOPROD joined with MA_PRODUCTOS.
    Replicates logic from pal/infrastructure/database.py
    """
    try:
        # Querying MA_DEPOPROD joined with MA_PRODUCTOS
        # Grouping by product code to get total stock in that deposit
        query = db.query(
            MaDepoProdDB.c_codarticulo.label("codigo"),
            func.max(MaProductosDB.cu_descripcion_corta).label("descripcion"),
            func.sum(MaDepoProdDB.n_cantidad).label("stock")
        ).join(
            MaProductosDB, MaDepoProdDB.c_codarticulo == MaProductosDB.C_CODIGO
        ).filter(
            MaDepoProdDB.c_coddeposito == sede_codigo
        ).group_by(
            MaDepoProdDB.c_codarticulo
        ).having(
            func.sum(MaDepoProdDB.n_cantidad) < 21
        ).order_by(
            func.sum(MaDepoProdDB.n_cantidad).asc()
        ).limit(limit)

        results = query.all()
        
        alerts = []
        for row in results:
            # Classification logic
            stock = int(row.stock)
            if 15 <= stock <= 20:
                nivel = "Leve"
            elif 8 <= stock <= 14:
                nivel = "Media"
            else:
                nivel = "Crítica"
                
            alerts.append(StockAlert(
                codigo=row.codigo,
                descripcion=row.descripcion or "SIN DESCRIPCIÓN",
                stock=stock,
                nivel=nivel
            ))
            
        return alerts

    except Exception as e:
        logger.error(f"Error fetching live stock alerts: {e}")
        return []
