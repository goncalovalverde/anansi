import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_db
from ..services import backlog_cache

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/{dataset_id}")
def get_insights(dataset_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT status FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Dataset not found")
    if row["status"] != "ready":
        raise HTTPException(409, "Dataset not ready")
    return backlog_cache.get_insights_response(db, dataset_id)
