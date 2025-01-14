import json
import logging
import os
import re
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


def get_model_parameters(model_config_id: str, base_path: str = ".") -> dict:
    """Get model parameters from gen_ai_config.csv."""
    config_path = os.path.join(base_path, "ai_eval_sheets", "gen_ai_model_configs.csv")
    model_configs = pl.read_csv(config_path)

    config = model_configs.filter(pl.col("model_config_id") == model_config_id)
    if config.height == 0:
        raise ValueError(f"Model config ID {model_config_id} not found")

    parameters = {}
    if config["model_parameters"][0]:
        try:
            parameters = json.loads(config["model_parameters"][0])
        except json.JSONDecodeError:
            logger.warning(
                f"Could not parse model_parameters: {config['model_parameters'][0]}"
            )

    return {
        "model_id": config["model_id"][0],
        "temperature": parameters.get("temperature", 0.01),
        "max_output_tokens": parameters.get("max_output_tokens", 2048),
        "top_p": parameters.get("top_p", 0.95),
        "top_k": parameters.get("top_k", 40),
    }


def get_batch_id_and_output_path(jsonl_path: str) -> Tuple[str, str]:
    """
    Extract batch ID and generate output path from input JSONL filename.

    Args:
        jsonl_path: Path to input JSONL file

    Returns:
        Tuple of (batch_id, output_path)
    """
    # Extract base filename without extension
    base_name = os.path.basename(jsonl_path)
    match = re.match(r"^(.*?)-question_prompts\.jsonl$", base_name)
    if not match:
        raise ValueError(f"Input filename {base_name} doesn't match expected pattern")

    model_conf_id = match.group(1)
    output_dir = os.path.dirname(jsonl_path)
    output_path = os.path.join(output_dir, f"{model_conf_id}-question_response.jsonl")
    # Add timestamp to batch_id (YYYYMMDDHHMMSS format)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_id = f"{model_conf_id}-{timestamp}"

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

    # Get model parameters
    model_params = get_model_parameters(model_config_id, base_path)
    model_id = model_params["model_id"]

    # Submit batch prediction job
    batch_id = send_batch_file(
        jsonl_path=input_jsonl_path,
        model_id=model_id,
        gcs_bucket=gcs_bucket,
        project_id=project_id,
    )

    logger.info(f"Job resource name: {batch_id}")
    return batch_id


def wait_for_batch_completion(
    batch_id: str, output_path: str, model_config_id: str
) -> Optional[str]:
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

    # Create custom ID mapping from CSV
    custom_id_mapping = {}
    csv_path = os.path.join(os.path.dirname(output_path), "question_prompts.csv")
    if not os.path.exists(csv_path):
        raise ValueError(f"Question prompts CSV file not found: {csv_path}")

    # Read CSV using polars
    df = pl.read_csv(csv_path)

    # Create mapping from prompt text to ID with model_config_id prefix
    for row in df.iter_rows(named=True):
        prompt_text = row["question_prompt_text"]
        custom_id = f"{model_config_id}-{row['question_prompt_id']}"
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
    parser.add_argument(
        "--input-jsonl", type=str, required=True, help="Path to input JSONL file"
    )
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

    args = parser.parse_args()

    try:
        # Extract model_config_id and output path from input filename
        base_name = os.path.basename(args.input_jsonl)
        match = re.match(r"^(.*?)-question_prompts\.jsonl$", base_name)
        if not match:
            raise ValueError(
                f"Input filename {base_name} doesn't match expected pattern"
            )
        model_config_id = match.group(1)

        # Get output path
        _, output_path = get_batch_id_and_output_path(args.input_jsonl)

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
            result_path = wait_for_batch_completion(
                batch_id, output_path, model_config_id
            )
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
