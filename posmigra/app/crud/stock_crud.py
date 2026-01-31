from sqlalchemy.orm import Session
from typing import List
from app.models import StockAlert, StockDB # Import both Pydantic model and SQLAlchemy DB model
import logging

logger = logging.getLogger(__name__)

def get_stock_alerts(db: Session) -> List[StockAlert]:
    """
    Fetches stock alerts from the database.

    Args:
        db: The database session.

    Returns:
        A list of StockAlert Pydantic models.
    """
    try:
        # Query the StockDB model from the database
        db_results = db.query(StockDB).all()
        
        # Map SQLAlchemy objects to Pydantic models
        # Assuming StockAlert can be created directly from StockDB attributes, or use .model_dump() if StockDB inherited from Base and had ORM features
        return [
            StockAlert(
                codigo=item.codigo,
                descripcion=item.descripcion,
                stock=item.stock,
                nivel=item.nivel
            ) for item in db_results
        ]
    except Exception as e:
        logger.error(f"Database error fetching stock alerts: {e}")
        return []

# You might also want functions for creating, updating, or deleting stock alerts
# if that functionality is required.
