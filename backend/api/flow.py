import json, sqlite3
import plotly.graph_objects as go
from fastapi import APIRouter, Depends, HTTPException
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
import services.config_service as config_service
import services.data_service as data_service
from viewer.backlog import Backlog

router = APIRouter(prefix="/api/flow", tags=["flow"])

def get_db():
    conn = database.get_db()
    try: yield conn
    finally: conn.close()

@router.get("/{dataset_id}")
def get_flow(dataset_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT status FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if not row: raise HTTPException(404, "Dataset not found")
    if row["status"] != "ready": raise HTTPException(409, "Dataset not ready")
    df = data_service.load_dataframe(db, dataset_id)
    config = config_service.build_reader_config(db)
    backlog = Backlog(df, config)
    methods = {
        "flow_efficiency": backlog.draw_flow_efficiency,
        "wip_trend": backlog.draw_wip_trend,
        "throughput": backlog.draw_throughput,
        "distribution": backlog.draw_distribution,
        "timeline_size": backlog.draw_timeline_size,
    }
    raw = {}
    for name, method in methods.items():
        try:
            raw[name] = method()
        except Exception as exc:
            import logging
            logging.error(f"Error in {name}: {exc}", exc_info=True)
            raw[name] = go.Figure(layout={"title": f"{name} unavailable: {exc}"}).to_json()
    return {k: json.loads(v) for k, v in raw.items()}
