"""
Shared utilities for the gm-eval CLI tool.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple

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


def get_model_id_from_config_id(
    jsonl_file: str, model_config_id: str, keep_provider_prefix: bool = False
) -> Optional[str]:
    """
    Get the model ID for a given model config ID from the CSV file in the same directory.

    Args:
        jsonl_file: Path to the JSONL file, used to determine the directory
        model_config_id: Model configuration ID to look up
        keep_provider_prefix: If True, return full model_id with provider prefix

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

        # Return full model_id if requested, otherwise remove provider prefix
        if keep_provider_prefix:
            return model_id
        elif "/" in model_id:
            return model_id.split("/", 1)[1]

        return model_id
    except Exception as e:
        logger.error(f"Error reading CSV file {csv_path}: {str(e)}")
        return None


def detect_provider_from_model_id(model_id: str) -> Tuple[str, str]:
    """
    Detect provider and model name from a model ID with provider prefix.

    Args:
        model_id: Model ID with potential provider prefix (e.g., "openai/gpt-4", "anthropic/claude-3")

    Returns:
        Tuple of (provider, model_name)
    """
    if "/" not in model_id:
        # No provider prefix, assume openai for backward compatibility
        return "openai", model_id

    provider, model_name = model_id.split("/", 1)
    return provider.lower(), model_name


def get_batch_model_name(model_id: str, mode: str) -> str:
    """
    Get the appropriate model name for the specified mode.

    Args:
        model_id: Full model ID (may include provider prefix)
        mode: Processing mode ("batch" or "litellm")

    Returns:
        Model name appropriate for the mode
    """
    if mode == "batch":
        # For batch mode, remove provider prefix
        if "/" in model_id:
            return model_id.split("/", 1)[1]
        return model_id
    else:
        # For litellm mode, keep the full model_id with prefix
        return model_id


def get_provider_method_from_model_id(model_id: str) -> str:
    """
    Get the provider method name from a model ID.

    Args:
        model_id: Model ID with provider prefix (e.g., "openai/gpt-4")

    Returns:
        Provider method name for use with batch processing
    """
    provider, _ = detect_provider_from_model_id(model_id)

    # Map provider names to method names
    provider_method_map = {
        "openai": "openai",
        "anthropic": "anthropic",
        "vertex": "vertex",
        "vertex_ai": "vertex",  # vertex_ai maps to vertex method
        "mistral": "mistral",
        "alibaba": "openai",  # alibaba uses openai-compatible endpoint
        "deepseek": "litellm",  # deepseek uses litellm
    }

    return provider_method_map.get(provider, "litellm")


def get_jsonl_format_from_provider(provider: str) -> str:
    """
    Get the JSONL format for a given provider.

    Args:
        provider: Provider name

    Returns:
        JSONL format string
    """
    format_map = {
        "openai": "openai",
        "anthropic": "openai",
        "vertex": "vertex",
        "vertex_ai": "vertex",  # vertex_ai uses vertex format
        "mistral": "mistral",
        "alibaba": "openai",  # alibaba uses openai format
        "deepseek": "openai",  # deepseek uses openai format
    }

    return format_map.get(provider, "openai")


def is_openai_compatible_provider(provider: str) -> bool:
    """
    Check if a provider is OpenAI-compatible (uses OpenAI endpoints but different keys/URLs).

    Args:
        provider: Provider name

    Returns:
        True if provider is OpenAI-compatible
    """
    openai_compatible = {"alibaba"}
    return provider in openai_compatible
