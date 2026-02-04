from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
# Using StockAlert as Pydantic model for response as defined in models.py
from app.models import StockAlert 
from app.crud.stock_crud import get_stock_alerts # Import the actual CRUD function
import logging # Import logging

logger = logging.getLogger(__name__) # Get logger instance

router = APIRouter(
    prefix="/stock",
    tags=["Stock"]
)

@router.get(
    "/alerts",
    response_model=List[StockAlert],
    summary="Get Stock Alerts"
)
async def get_stock_alerts_endpoint(
    db: Session = Depends(get_db),
    sede_codigo: str = Query("0301", alias="sede")
):
    """
    Retrieves a list of live stock alerts for a specific branch.
    """
    return get_stock_alerts(db, sede_codigo=sede_codigo)

# You can add more endpoints here for specific stock items, inventory levels, etc.