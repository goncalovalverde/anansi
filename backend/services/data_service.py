import hashlib
import json
import sqlite3
import uuid
import logging
from pandas import DataFrame

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import services.config_service as config_service
import reader

logger = logging.getLogger(__name__)


def compute_config_hash(db: sqlite3.Connection) -> str:
    raw = config_service.get_raw_config(db)
    workflow = config_service.get_workflow(db)
    combined = sorted(raw.items()) + [("__workflow__", "|".join(workflow))]
    hash_input = json.dumps(combined, sort_keys=True).encode("utf-8")
    return hashlib.md5(hash_input).hexdigest()


def find_valid_dataset(db: sqlite3.Connection, config_hash: str) -> str | None:
    row = db.execute(
        "SELECT id FROM datasets WHERE config_hash=? AND status='ready' "
        "ORDER BY created_at DESC LIMIT 1",
        (config_hash,),
    ).fetchone()
    return row["id"] if row else None


def create_dataset(db: sqlite3.Connection, config_hash: str, source: str) -> str:
    dataset_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO datasets (id, config_hash, source, status) VALUES (?, ?, ?, 'pending')",
        (dataset_id, config_hash, source),
    )
    db.commit()
    return dataset_id


def update_dataset_status(
    db: sqlite3.Connection,
    dataset_id: str,
    status: str,
    error: str | None = None,
) -> None:
    db.execute(
        "UPDATE datasets SET status=?, error=? WHERE id=?",
        (status, error, dataset_id),
    )
    db.commit()


def update_dataset_progress(
    db: sqlite3.Connection,
    dataset_id: str,
    loaded: int,
    total: int,
) -> None:
    db.execute(
        "UPDATE datasets SET progress_loaded=?, progress_total=? WHERE id=?",
        (loaded, total, dataset_id),
    )
    db.commit()


def save_dataframe(db: sqlite3.Connection, dataset_id: str, df: DataFrame) -> None:
    rows = [
        (dataset_id, idx, json.dumps(row, default=str))
        for idx, row in enumerate(df.to_dict(orient="records"))
    ]
    db.execute("DELETE FROM dataset_rows WHERE dataset_id=?", (dataset_id,))
    db.executemany(
        "INSERT INTO dataset_rows (dataset_id, row_index, row_data) VALUES (?, ?, ?)",
        rows,
    )
    db.commit()


def load_dataframe(db: sqlite3.Connection, dataset_id: str) -> DataFrame:
    rows = db.execute(
        "SELECT row_data FROM dataset_rows WHERE dataset_id=? ORDER BY row_index",
        (dataset_id,),
    ).fetchall()
    records = [json.loads(row["row_data"]) for row in rows]
    df = DataFrame(records)

    import pandas as pd
    datetime_cols = ["Created", "Done", "In Progress", "Backlog"]
    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in df.columns:
        if df[col].dtype == object:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    converted = pd.to_datetime(df[col], errors="coerce", format="mixed")
                if converted.notna().sum() > len(df) * 0.5:
                    df[col] = converted
            except Exception:
                pass

    return df


def load_data_task(dataset_id: str, db_path: str) -> None:
    conn = database.get_db(db_path)
    try:
        update_dataset_status(conn, dataset_id, "loading")

        def progress_callback(loaded: int, total: int) -> None:
            update_dataset_progress(conn, dataset_id, loaded, total)

        reader_config = config_service.build_reader_config(conn)
        df = reader.read_data(reader_config, db_path, progress_callback=progress_callback)
        store_dataframe(conn, dataset_id, df)
        update_dataset_status(conn, dataset_id, "ready")
        logger.info("Dataset %s loaded successfully (%d rows)", dataset_id, len(df))
    except Exception as exc:
        logger.exception("Failed to load dataset %s", dataset_id)
        update_dataset_status(conn, dataset_id, "failed", error=str(exc))
    finally:
        conn.close()
