import io
import pandas as pd


def _parse(df: pd.DataFrame, workflow: list[str]) -> pd.DataFrame:
    df["Created"] = pd.to_datetime(df["Created"])
    for item in workflow:
        if item in df.columns:
            df[item] = pd.to_datetime(df[item])
    return df


def read(csv_file: str, workflow: list[str]) -> pd.DataFrame:
    return _parse(pd.read_csv(csv_file), workflow)


def read_from_string(text: str, workflow: list[str]) -> pd.DataFrame:
    return _parse(pd.read_csv(io.StringIO(text)), workflow)
