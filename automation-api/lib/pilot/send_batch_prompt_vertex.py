import logging
import os
import time
from datetime import datetime
from typing import Optional, Tuple

import polars as pl
import vertexai

from lib.app_singleton import AppSingleton
from lib.config import read_config
from lib.llm.vertex_batch_api import (
    check_batch_job_status,
    download_batch_job_output,
    send_batch_file,
)

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)

PROCESSING_STATUSES = {"RUNNING", "PENDING"}


def get_model_id(model_config_id: str, base_path: str = ".") -> str:
    """Get model ID from gen_ai_config.csv."""
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
    # Get base filename without extension
    base_name = os.path.splitext(os.path.basename(jsonl_path))[0]
    output_dir = os.path.dirname(jsonl_path)
    output_path = os.path.join(output_dir, f"{base_name}-response.jsonl")

    # Add timestamp to batch_id (YYYYMMDDHHMMSS format)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_id = f"{base_name}-{timestamp}"

    return batch_id, output_path


def process_batch_prompts(
    model_config_id: str,
    input_jsonl_path: str,
    base_path: str = ".",
) -> str:
    """Process batch prompts using Vertex AI.

    Returns:
        The batch job resource name
    """
    # Read configuration
    config = read_config()
    project_id = config.get("VERTEXAI_PROJECT")
    if not project_id:
        raise ValueError("VERTEXAI_PROJECT not found in configuration")

    # Get GCS bucket from environment
    gcs_bucket = os.getenv("GCS_BUCKET")
    if not gcs_bucket:
        raise ValueError("GCS_BUCKET environment variable is required")

    # Get model ID
    model_id = get_model_id(model_config_id, base_path)

    # Submit batch prediction job
    batch_id = send_batch_file(
        jsonl_path=input_jsonl_path,
        model_id=model_id,
        gcs_bucket=gcs_bucket,
        project_id=project_id,
    )

    logger.info(f"Job resource name: {batch_id}")
    return batch_id


def wait_for_batch_completion(batch_id: str, output_path: str) -> Optional[str]:
    """
    Wait for a batch to complete and download results when ready.

    Args:
        batch_id: The batch job resource name
        output_path: Path to save results file

    Returns:
        Path to results file if successful, None if batch failed/cancelled
    """
    logger.info(f"Waiting for batch {batch_id} to complete...")
    config = read_config()
    project_id = config.get("VERTEXAI_PROJECT")
    if not project_id:
        raise ValueError("VERTEXAI_PROJECT not found in configuration")

    # Create custom ID mapping from prompt mapping CSV
    custom_id_mapping = {}
    mapping_path = output_path.replace("-response.jsonl", "-prompt-mapping.csv")
    if not os.path.exists(mapping_path):
        raise ValueError(f"Prompt mapping CSV file not found: {mapping_path}")

    # Read CSV using polars
    df = pl.read_csv(mapping_path)

    # Create mapping from prompt text to ID
    for row in df.iter_rows(named=True):
        prompt_text = row["prompt_text"]
        custom_id = row["prompt_id"]
        custom_id_mapping[prompt_text] = custom_id

    while True:
        status = check_batch_job_status(batch_id, project_id)
        logger.info(f"Batch status: {status}")

        if status == "JOB_STATE_SUCCEEDED":
            logger.info("Batch succeeded!")
            return download_batch_job_output(
                batch_id=batch_id,
                output_path=output_path,
                project_id=project_id,
                custom_id_mapping=custom_id_mapping,
            )
        elif status in {"JOB_STATE_FAILED", "JOB_STATE_CANCELLED"}:
            logger.error(f"Batch failed with status: {status}")
            return None

        time.sleep(60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Process batch prompts using Vertex AI"
    )
    parser.add_argument("input_jsonl", type=str, help="Path to input JSONL file")
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",
        help="Base directory containing ai_eval_sheets folder",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for batch completion and download results",
    )
    parser.add_argument(
        "--model-config-id",
        type=str,
        help="Override model config ID extracted from filename",
    )

    args = parser.parse_args()

    try:
        # Use provided model_config_id or extract from filename
        if args.model_config_id:
            model_config_id = args.model_config_id
        else:
            base_name = os.path.splitext(os.path.basename(args.input_jsonl))[0]
            model_config_id = base_name.split("-")[
                0
            ]  # Get the part before first hyphen

        # Get batch ID and output path
        batch_id, output_path = get_batch_id_and_output_path(args.input_jsonl)

        # Check for existing processing file
        processing_file = f"{output_path}.processing"
        if os.path.exists(processing_file):
            logger.info("Batch already being processed.")
            # Read and return the batch ID from the file
            with open(processing_file, "r") as f:
                batch_id = f.read().strip()
            # Initialize Vertex AI
            config = read_config()
            project_id = config.get("VERTEXAI_PROJECT")
            if not project_id:
                raise ValueError("VERTEXAI_PROJECT not found in configuration")
            vertexai.init(project=project_id, location="us-central1")

            batch_id = batch_id
        else:
            # Submit new batch job
            batch_id = process_batch_prompts(
                model_config_id=model_config_id,
                input_jsonl_path=args.input_jsonl,
                base_path=args.base_path,
            )
            # Save batch ID to processing file
            with open(processing_file, "w") as f:
                f.write(batch_id)

        if args.wait:
            result_path = wait_for_batch_completion(batch_id, output_path)
            if result_path:
                print(f"Results saved to: {result_path}")
                # Clean up processing file
                if os.path.exists(processing_file):
                    os.remove(processing_file)
        else:
            print(f"Batch ID: {batch_id}")
    except Exception as e:
        logger.error(f"Error processing batch prompts: {str(e)}")
        raise
