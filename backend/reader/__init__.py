import logging

from . import csv, jira

logger = logging.getLogger(__name__)


def read_data(config: dict, db_path: str, progress_callback=None):
    mode = config["input"]["mode"]

    if mode == "csv":
        logger.info("Reading data from CSV: %s", config["input"]["csv_file"])
        return csv.read(config["input"]["csv_file"], config["Workflow"])

    elif mode == "jira":
        logger.info("Reading data from Jira")
        jr = jira.Jira(config["jira"], config["Workflow"], db_path)
        return jr.get_jira_data(progress_callback=progress_callback)

    else:
        raise ValueError(f"Unknown input mode: {mode!r}")
