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
    response_model=List[StockAlert], # Using StockAlert as response_model
    summary="Get Stock Alerts"
)
async def get_stock_alerts_endpoint(db: Session = Depends(get_db)):
    """
    Retrieves a list of stock alerts.
    """
    alerts = get_stock_alerts(db) # Call the actual CRUD function
    
    if not alerts:
        return [] # Return empty list if no alerts, rather than 404
        
    return alerts

# You can add more endpoints here for specific stock items, inventory levels, etc.