from fastapi import APIRouter, Depends, HTTPException
import sqlite3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
import services.config_service as config_service
import services.data_service as data_service
from viewer.backlog import Backlog

router = APIRouter(prefix="/api/insights", tags=["insights"])

def get_db():
    conn = database.get_db()
    try: yield conn
    finally: conn.close()

@router.get("/{dataset_id}")
def get_insights(dataset_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT status FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if not row: raise HTTPException(404, "Dataset not found")
    if row["status"] != "ready": raise HTTPException(409, "Dataset not ready")
    df = data_service.load_dataframe(db, dataset_id)
    config = config_service.build_reader_config(db)
    backlog = Backlog(df, config)
    return backlog.get_insights()
