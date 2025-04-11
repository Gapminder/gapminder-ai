"""
Shared utilities for the gm-eval CLI tool.
"""

import os
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from lib.app_singleton import AppSingleton

logger = AppSingleton().get_logger()


def ensure_directory(directory: Optional[str] = None) -> Path:
    """
    Ensure the specified directory exists.

    Args:
        directory: Directory path to ensure exists

    Returns:
        Path object for the directory
    """
    if directory is None:
        directory = os.getcwd()

    path = Path(directory)
    path.mkdir(exist_ok=True, parents=True)
    return path


def get_default_output_path(model_config_id: str, base_path: str = ".") -> str:
    """
    Get the default output path for a model config.

    Args:
        model_config_id: Model configuration ID
        base_path: Base directory path

    Returns:
        Path to the output file
    """
    return os.path.join(base_path, f"{model_config_id}-question_prompts.jsonl")


def get_response_path(prompt_path: str) -> str:
    """
    Get the response path for a prompt file.

    Args:
        prompt_path: Path to the prompt file

    Returns:
        Path to the response file
    """
    base, ext = os.path.splitext(prompt_path)
    return f"{base}-response{ext}"


def extract_model_config_id_from_filename(filename: str) -> Optional[str]:
    """
    Extract the model config ID from a filename.

    Args:
        filename: Filename to extract from (e.g., "mc056-question_prompts.jsonl")

    Returns:
        Extracted model config ID or None if not found
    """
    match = re.match(r"^([^-]+)-", os.path.basename(filename))
    if match:
        return match.group(1)
    return None


def get_model_id_from_config_id(jsonl_file: str, model_config_id: str) -> Optional[str]:
    """
    Get the model ID for a given model config ID from the CSV file in the same directory.

    Args:
        jsonl_file: Path to the JSONL file, used to determine the directory
        model_config_id: Model configuration ID to look up

    Returns:
        Model ID or None if not found
    """
    # Get the directory containing the JSONL file
    directory = os.path.dirname(jsonl_file)

    # Look for the CSV file in the ai_eval_sheets subdirectory
    csv_path = os.path.join(directory, "ai_eval_sheets", "gen_ai_model_configs.csv")

    if not os.path.exists(csv_path):
        logger.warning(f"Could not find gen_ai_model_configs.csv file in {os.path.join(directory, 'ai_eval_sheets')}")
        return None

    try:
        df = pd.read_csv(csv_path)
        if "model_config_id" not in df.columns or "model_id" not in df.columns:
            logger.warning(f"CSV file {csv_path} does not have required columns")
            return None

        # Find the row with the matching model_config_id
        matching_rows = df[df["model_config_id"] == model_config_id]
        if matching_rows.empty:
            logger.warning(f"Model config ID {model_config_id} not found in {csv_path}")
            return None

        # Get the model_id from the first matching row
        model_id = matching_rows.iloc[0]["model_id"]

        # If the model_id contains a slash, return only the part after the slash
        if "/" in model_id:
            return model_id.split("/", 1)[1]

        return model_id
    except Exception as e:
        logger.error(f"Error reading CSV file {csv_path}: {str(e)}")
        return None
