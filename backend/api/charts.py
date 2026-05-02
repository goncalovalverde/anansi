import json
import sqlite3
from fastapi import APIRouter, Depends, HTTPException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import services.config_service as config_service
import services.data_service as data_service
from viewer.backlog import Backlog

router = APIRouter(prefix="/api/charts", tags=["charts"])


def get_db():
    conn = database.get_db()
    try:
        yield conn
    finally:
        conn.close()


@router.get("/{dataset_id}")
def get_charts(dataset_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT status FROM datasets WHERE id=?", (dataset_id,)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")

    status = row["status"]
    if status == "pending" or status == "loading":
        raise HTTPException(
            status_code=409, detail=f"Dataset is not ready yet (status: {status})"
        )
    if status == "failed":
        raise HTTPException(status_code=422, detail="Dataset loading failed")

    df = data_service.load_dataframe(db, dataset_id)
    reader_config = config_service.build_reader_config(db)

    try:
        backlog = Backlog(df, reader_config)
        raw_charts = backlog.get_all_charts()
        charts = {key: json.loads(value) for key, value in raw_charts.items()}
        charts["kpis"] = backlog.get_kpis()
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Chart rendering failed: {exc}"
        )

    return charts
