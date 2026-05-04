import io
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import services.config_service as config_service
import services.data_service as data_service
import reader.jira as jira_reader
import reader.csv as csv_reader

router = APIRouter(prefix="/api/data", tags=["data"])


def get_db():
    conn = database.get_db()
    try:
        yield conn
    finally:
        conn.close()


@router.post("/load")
def load_data(
    background_tasks: BackgroundTasks,
    db: sqlite3.Connection = Depends(get_db),
):
    reader_config = config_service.build_reader_config(db)
    source = reader_config["input"]["mode"]

    if source == "jira":
        try:
            jira_reader.validate_auth_config(reader_config["jira"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    config_hash = data_service.compute_config_hash(db)
    existing_id = data_service.find_valid_dataset(db, config_hash)

    if existing_id:
        return {"dataset_id": existing_id, "cached": True}

    dataset_id = data_service.create_dataset(db, config_hash, source)

    background_tasks.add_task(
        data_service.load_data_task, dataset_id, database.DB_PATH
    )
    return {"dataset_id": dataset_id, "cached": False}


@router.get("/{dataset_id}/status")
def get_dataset_status(dataset_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT status, error, progress_loaded, progress_total FROM datasets WHERE id=?",
        (dataset_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {
        "status": row["status"],
        "error": row["error"],
        "progress_loaded": row["progress_loaded"] or 0,
        "progress_total": row["progress_total"] or 0,
    }


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: sqlite3.Connection = Depends(get_db),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    contents = await file.read()
    try:
        text = contents.decode("utf-8-sig")  # handle BOM-prefixed CSVs too
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    workflow = config_service.get_workflow(db)
    try:
        df = csv_reader.read_from_string(text, workflow)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {exc}")

    import hashlib, json
    content_hash = hashlib.md5(contents).hexdigest()
    config_hash = f"csv:{content_hash}"

    existing_id = data_service.find_valid_dataset(db, config_hash)
    if existing_id:
        return {"dataset_id": existing_id, "cached": True}

    dataset_id = data_service.create_dataset(db, config_hash, "csv")
    data_service.store_dataframe(db, dataset_id, df)
    data_service.update_dataset_status(db, dataset_id, "ready")

    return {"dataset_id": dataset_id, "cached": False}


@router.delete("/cache")
def clear_cache(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute("SELECT COUNT(*) FROM datasets")
    count = cursor.fetchone()[0]
    db.execute("DELETE FROM datasets")
    db.commit()
    return {"deleted": count}
