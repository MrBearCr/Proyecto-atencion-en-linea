"""
Endpoints de API para gestión de stock.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al path para importar pal/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pal.services.stock import (
    fetch_stock_alerts_optimized,
    filter_alertas,
    get_existencias_por_ubicacion,
    build_producto_jerarquia,
)
from ..db import get_db_manager, ensure_db_connected
from ..dependencies import verify_token

router = APIRouter(prefix="/api/stock", tags=["stock"])


class StockAlertResponse(BaseModel):
    codigo: str
    descripcion: str
    stock: int
    nivel: str


class StockAlertsListResponse(BaseModel):
    alerts: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


@router.get("/alerts", response_model=StockAlertsListResponse)
def get_stock_alerts(
    user_info: Dict[str, Any] = Depends(verify_token),
    dept_code: Optional[str] = Query(None, description="Código de departamento"),
    group_code: Optional[str] = Query(None, description="Código de grupo"),
    sub_code: Optional[str] = Query(None, description="Código de subgrupo"),
    search_text: Optional[str] = Query("", description="Texto de búsqueda"),
    filter_level: Optional[str] = Query("TODAS", description="Nivel de alerta (TODAS, CRÍTICA, MEDIA, LEVE)"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(50, ge=1, le=500, description="Tamaño de página"),
):
    """
    Obtiene alertas de stock con filtros opcionales.
    """
    try:
        if not ensure_db_connected():
            raise HTTPException(status_code=503, detail="Base de datos no disponible")
        
        db_manager = get_db_manager()
        
        # Obtener todas las alertas (sin paginación inicial para aplicar filtros)
        all_alerts = fetch_stock_alerts_optimized(db_manager, limit=None, offset=0)
        
        # Obtener jerarquía de productos para filtros
        jerarquia_query = """
        SELECT DISTINCT C_CODIGO, C_DEPARTAMENTO, C_GRUPO, C_SUBGRUPO
        FROM MA_PRODUCTOS
        WHERE C_ESTADO = 'A' AND C_CODIGO IS NOT NULL
        """
        jerarquia_data = db_manager.fetch_data(jerarquia_query)
        producto_jerarquia = build_producto_jerarquia(
            jerarquia_data,
            [str(a[0]) for a in all_alerts]
        )
        
        # Aplicar filtros
        filtered_alerts = filter_alertas(
            all_alerts,
            producto_jerarquia,
            dept_code=dept_code,
            group_code=group_code,
            sub_code=sub_code,
            search_text=search_text,
            filter_level=filter_level,
            favoritos=None,  # TODO: obtener favoritos del usuario
        )
        
        # Paginación
        total = len(filtered_alerts)
        offset = (page - 1) * page_size
        paginated_alerts = filtered_alerts[offset:offset + page_size]
        
        # Formatear respuesta
        alerts_data = [
            {
                "codigo": str(alert[0]),
                "descripcion": str(alert[1]) if len(alert) > 1 else "",
                "stock": int(alert[2]) if len(alert) > 2 and alert[2] is not None else 0,
                "nivel": str(alert[3]) if len(alert) > 3 else "LEVE",
            }
            for alert in paginated_alerts
        ]
        
        return StockAlertsListResponse(
            alerts=alerts_data,
            total=total,
            page=page,
            page_size=page_size,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo alertas de stock: {str(e)}")


@router.get("/existencias/{codigo}")
def get_existencias(
    codigo: str,
    user_info: Dict[str, Any] = Depends(verify_token),
    depositos: Optional[str] = Query("0301", description="Códigos de depósito separados por coma"),
):
    """
    Obtiene las existencias de un producto en los depósitos especificados.
    """
    try:
        if not ensure_db_connected():
            raise HTTPException(status_code=503, detail="Base de datos no disponible")
        
        db_manager = get_db_manager()
        depositos_list = [d.strip() for d in depositos.split(",") if d.strip()]
        
        if not depositos_list:
            raise HTTPException(status_code=400, detail="Debe especificar al menos un depósito")
        
        existencias = get_existencias_por_ubicacion(db_manager, codigo, depositos_list)
        
        return {
            "codigo": codigo,
            "depositos": depositos_list,
            "existencias": existencias,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo existencias: {str(e)}")

