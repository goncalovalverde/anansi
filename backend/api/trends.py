import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_db
from ..services import backlog_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trends", tags=["trends"])

@router.get("/{dataset_id}")
def get_trends(dataset_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT status FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if not row: raise HTTPException(404, "Dataset not found")
    if row["status"] != "ready": raise HTTPException(409, "Dataset not ready")
    try:
        return backlog_cache.get_trends_response(db, dataset_id)
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        logger.exception("Trend charts failed for dataset %s: %s", dataset_id, e)
        raise HTTPException(500, "Trend chart rendering failed")
    except Exception as e:
        logger.exception("Unexpected error during trend chart rendering for dataset %s: %s", dataset_id, e)
        raise
