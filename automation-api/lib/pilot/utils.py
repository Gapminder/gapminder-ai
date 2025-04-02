import os
from datetime import datetime
from typing import Tuple

import polars as pl
from pandera.errors import SchemaError

from lib.ai_eval_spreadsheet.wrapper import (
    AiEvalData,
    get_ai_eval_spreadsheet,
    read_ai_eval_data,
)
from lib.app_singleton import AppSingleton
from lib.authorized_clients import get_service_account_authorized_clients
from lib.config import read_config

logger = AppSingleton().get_logger()


def read_ai_eval_spreadsheet() -> AiEvalData:
    config = read_config()
    authorized_clients = get_service_account_authorized_clients()

    ai_eval_spreadsheet_id = config["AI_EVAL_DEV_SPREADSHEET_ID"]
    ai_eval_spreadsheet = get_ai_eval_spreadsheet(authorized_clients, ai_eval_spreadsheet_id)
    try:
        return read_ai_eval_data(ai_eval_spreadsheet)
    except SchemaError as err:
        logger.error("DataFrame validation failed. Errors:", err.check)
        logger.error("Schema:")
        logger.error(err.schema)
        logger.error("Failure cases:")
        logger.error(err.failure_cases)  # dataframe of schema errors
        logger.error("Original data:")
        logger.error(err.data)  # invalid dataframe
        raise Exception("Data validation. Please fix and retry")


def get_model_id(model_config_id: str, base_path: str = ".") -> str:
    """Get model ID from gen_ai_config.csv"""
    config_path = os.path.join(base_path, "ai_eval_sheets", "gen_ai_model_configs.csv")
    model_configs = pl.read_csv(config_path)

    config = model_configs.filter(pl.col("model_config_id") == model_config_id)
    if config.height == 0:
        raise ValueError(f"Model config ID {model_config_id} not found")

    return config["model_id"][0]


def get_batch_id_and_output_path(jsonl_path: str) -> Tuple[str, str]:
    """
    Generate batch ID and output path from input JSONL filename.

    Args:
        jsonl_path: Path to input JSONL file

    Returns:
        Tuple of (batch_id, output_path)
    """
    batch_id = generate_batch_id(jsonl_path)
    output_path = get_output_path(jsonl_path)
    return batch_id, output_path


def get_output_path(jsonl_path: str) -> str:
    # Get base filename without extension
    base_name = os.path.splitext(os.path.basename(jsonl_path))[0]
    output_dir = os.path.dirname(jsonl_path)
    output_path = os.path.join(output_dir, f"{base_name}-response.jsonl")

    return output_path


def generate_batch_id(jsonl_path: str) -> str:
    # Get base filename without extension
    base_name = os.path.splitext(os.path.basename(jsonl_path))[0]
    # Add timestamp to batch_id (YYYYMMDDHHMMSS format)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_id = f"{base_name}-{timestamp}"

    return batch_id
