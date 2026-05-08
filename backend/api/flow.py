import sqlite3, logging
from fastapi import APIRouter, Depends, HTTPException
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
import services.backlog_cache as backlog_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/flow", tags=["flow"])

def get_db():
    conn = database.get_db()
    try: yield conn
    finally: conn.close()

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
    except Exception:
        logger.exception("Flow chart rendering failed for dataset %s", dataset_id)
        raise HTTPException(500, "Flow chart rendering failed - check server logs for details")
