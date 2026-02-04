from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models import MBRPReportSummary
from app.crud.mbrp_crud import get_mbrp_report
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mbrp",
    tags=["MBRP"]
)

@router.get(
    "/report",
    response_model=MBRPReportSummary,
    summary="Get MBRP Report Summary"
)
async def get_mbrp_report_endpoint(
    db: Session = Depends(get_db),
    sede_codigo: str = Query("00", alias="sede"),
    days: int = Query(30, ge=1, le=365)
):
    """
    Retrieves a summary report for products with Low Movement (MBRP).
    """
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        return get_mbrp_report(
            db=db,
            start_date=start_date,
            end_date=end_date,
            sede_codigo=sede_codigo
        )
    except Exception as e:
        logger.error(f"Error in MBRP report endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
