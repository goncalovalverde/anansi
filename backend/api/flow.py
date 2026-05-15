import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_db
from ..services import backlog_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/flow", tags=["flow"])

@router.get("/{dataset_id}")
def get_flow(dataset_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT status FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Dataset not found")

    status = row["status"]
    if status in ("pending", "loading"):
        raise HTTPException(409, f"Dataset is not ready yet (status: {status})")
    if status == "failed":
        raise HTTPException(422, "Dataset loading failed")

    try:
        return backlog_cache.get_flow_response(db, dataset_id)
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        logger.exception("Flow chart rendering failed for dataset %s: %s", dataset_id, e)
        raise HTTPException(500, "Flow chart rendering failed - check server logs for details")
    except Exception as e:
        logger.exception("Unexpected error during flow chart rendering for dataset %s: %s", dataset_id, e)
        raise
