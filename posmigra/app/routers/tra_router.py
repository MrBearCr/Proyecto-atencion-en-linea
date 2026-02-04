from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.database import get_db
from app.models import ProductoVentasResponse
from app.crud.tra_crud import get_tra_sales_data
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tra",
    tags=["TRA"]
)


@router.get(
    "/sales",
    response_model=List[ProductoVentasResponse],
    summary="Get TRA Sales Data"
)
async def get_tra_sales_data_endpoint(
    db: Session = Depends(get_db),
    dept_code: Optional[str] = Query(None, alias="department"),
    group_code: Optional[str] = Query(None, alias="group"),
    sub_code: Optional[str] = Query(None, alias="subgroup"),
    search_text: Optional[str] = Query(None, alias="search"),
    filter_rotacion: str = Query("TODAS", alias="rotation"),
    sede_codigo: str = Query("00", alias="sede"), # Default to Global
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1)
):
    """
    Retrieves TRA sales data based on filters.
    """
    # Calculate date range (default to last 30 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    return get_tra_sales_data(
        db=db,
        start_date=start_date,
        end_date=end_date,
        dept_code=dept_code,
        group_code=group_code,
        sub_code=sub_code,
        search_text=search_text,
        filter_rotacion=filter_rotacion,
        sede_codigo=sede_codigo,
        page=page,
        page_size=page_size
    )
    #         dept_code=dept_code, group_code=group_code, sub_code=sub_code,
    #         search_text=search_text, filter_rotacion=filter_rotacion,
    #         page=page, page_size=page_size
    #     )
    #     return sales_data
    # except Exception as e:
    #     logger.error(f"Error fetching TRA sales data from DB: {e}")
    #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener datos de ventas TRA.")
    
    return mock_get_tra_sales_data(
        db=db,
        dept_code=dept_code, group_code=group_code, sub_code=sub_code,
        search_text=search_text, filter_rotacion=filter_rotacion,
        page=page, page_size=page_size
    )

# Add endpoints for other TRA-related data if necessary