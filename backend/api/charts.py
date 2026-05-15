import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_db
from ..services import backlog_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/charts", tags=["charts"])


@router.get("/{dataset_id}")
def get_charts(dataset_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT status FROM datasets WHERE id=?", (dataset_id,)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")

    status = row["status"]
    if status in ("pending", "loading"):
        raise HTTPException(
            status_code=409, detail=f"Dataset is not ready yet (status: {status})"
        )
    if status == "failed":
        raise HTTPException(status_code=422, detail="Dataset loading failed")

    try:
        response = backlog_cache.get_dashboard_response(db, dataset_id)
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        logger.exception("Chart rendering failed for dataset %s: %s", dataset_id, e)
        raise HTTPException(
            status_code=500, detail="Chart rendering failed - check server logs for details"
        )
    except Exception as e:
        logger.exception("Unexpected error during chart rendering for dataset %s: %s", dataset_id, e)
        raise

    return response
