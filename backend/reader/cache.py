import sqlite3
import json
import logging
from pandas import DataFrame

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self, db_path: str, config_hash: str):
        self.db_path = db_path
        self.config_hash = config_hash

    def _connect(self) -> sqlite3.Connection:
        import database
        return database.get_db(self.db_path)

    def is_valid(self) -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id FROM datasets WHERE config_hash=? AND status='ready' LIMIT 1",
                (self.config_hash,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def read(self) -> DataFrame:
        import pandas as pd
        conn = self._connect()
        try:
            dataset_row = conn.execute(
                "SELECT id FROM datasets WHERE config_hash=? AND status='ready' "
                "ORDER BY created_at DESC LIMIT 1",
                (self.config_hash,),
            ).fetchone()
            if not dataset_row:
                raise ValueError(f"No valid dataset found for hash {self.config_hash}")
            dataset_id = dataset_row["id"]
            rows = conn.execute(
                "SELECT row_data FROM dataset_rows WHERE dataset_id=? ORDER BY row_index",
                (dataset_id,),
            ).fetchall()
            records = [json.loads(r["row_data"]) for r in rows]
            return DataFrame(records)
        finally:
            conn.close()

    def write(self, df: DataFrame) -> None:
        conn = self._connect()
        try:
            dataset_row = conn.execute(
                "SELECT id FROM datasets WHERE config_hash=? AND status='ready' "
                "ORDER BY created_at DESC LIMIT 1",
                (self.config_hash,),
            ).fetchone()
            if not dataset_row:
                raise ValueError(
                    f"No dataset found to write cache for hash {self.config_hash}"
                )
            dataset_id = dataset_row["id"]
            rows = [
                (dataset_id, idx, json.dumps(row, default=str))
                for idx, row in enumerate(df.to_dict(orient="records"))
            ]
            conn.execute("DELETE FROM dataset_rows WHERE dataset_id=?", (dataset_id,))
            conn.executemany(
                "INSERT INTO dataset_rows (dataset_id, row_index, row_data) VALUES (?, ?, ?)",
                rows,
            )
            conn.commit()
            logger.debug("Cache written for hash %s (%d rows)", self.config_hash, len(df))
        finally:
            conn.close()

    def clean(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM datasets WHERE config_hash=?", (self.config_hash,)
            )
            conn.commit()
            logger.debug("Cache cleaned for hash %s", self.config_hash)
        finally:
            conn.close()
