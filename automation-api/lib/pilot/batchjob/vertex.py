"""Vertex AI batch processing implementation."""
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


def _get_model_id(model_config_id: str) -> str:
    """Get model ID from gen_ai_config.csv."""
    config_path = os.path.join("ai_eval_sheets", "gen_ai_model_configs.csv")
    model_configs = pl.read_csv(config_path)

    config = model_configs.filter(pl.col("model_config_id") == model_config_id)
    if config.height == 0:
        raise ValueError(f"Model config ID {model_config_id} not found")

    return config["model_id"][0]


def send_batch(jsonl_path: str) -> str:
    """Submit batch job to Vertex AI."""
    try:
        output_path = get_batch_metadata(jsonl_path)[1]

        # Check for existing processing file
        processing_file = f"{output_path}.processing"
        if os.path.exists(processing_file):
            logger.info("Batch already being processed.")
            with open(processing_file, "r") as f:
                return f.read().strip()

        # Get configuration
        config = read_config()
        project_id = config.get("VERTEXAI_PROJECT")
        gcs_bucket = os.getenv("GCS_BUCKET")

        if not project_id or not gcs_bucket:
            raise ValueError("Missing Vertex AI configuration (project or bucket)")

        # Extract model_config_id from filename
        base_name = os.path.splitext(os.path.basename(jsonl_path))[0]
        model_config_id = base_name.split("-")[0]
        model_id = _get_model_id(model_config_id)

        # Initialize Vertex AI
        vertexai.init(project=project_id, location="us-central1")

        # Submit batch job
        batch_id = send_batch_file(
            jsonl_path=jsonl_path,
            model_id=model_id,
            gcs_bucket=gcs_bucket,
            project_id=project_id,
        )

        # Create processing file
        with open(processing_file, "w") as f:
            f.write(batch_id)

        return batch_id

    except Exception as e:
        logger.error(f"Error sending batch: {str(e)}")
        raise


def check_status(batch_id: str) -> str:
    """Check status of a Vertex AI batch job."""
    config = read_config()
    project_id = config.get("VERTEXAI_PROJECT")
    if not project_id:
        raise ValueError("VERTEXAI_PROJECT not found in configuration")

    return check_batch_job_status(batch_id, project_id)


def download_results(batch_id: str, output_path: str) -> Optional[str]:
    """Download Vertex AI batch results."""
    config = read_config()
    project_id = config.get("VERTEXAI_PROJECT")
    if not project_id:
        raise ValueError("VERTEXAI_PROJECT not found in configuration")

    # Generate custom ID mapping from prompt mapping CSV
    mapping_path = output_path.replace("-response.jsonl", "-prompt-mapping.csv")
    if not os.path.exists(mapping_path):
        raise ValueError(f"Prompt mapping CSV not found: {mapping_path}")

    df = pl.read_csv(mapping_path)
    custom_id_mapping = {
        row["prompt_text"]: row["prompt_id"] for row in df.iter_rows(named=True)
    }

    return download_batch_job_output(
        batch_id=batch_id,
        output_path=output_path,
        project_id=project_id,
        custom_id_mapping=custom_id_mapping,
    )


def wait_for_completion(
    batch_id: str, output_path: str, poll_interval: int = 60
) -> Optional[str]:
    """Wait for Vertex AI batch completion."""
    while True:
        status = check_status(batch_id)
        if status == "JOB_STATE_SUCCEEDED":
            return download_results(batch_id, output_path)
        elif status in {"JOB_STATE_FAILED", "JOB_STATE_CANCELLED"}:
            return None
        time.sleep(poll_interval)


def get_batch_metadata(jsonl_path: str) -> Tuple[str, str]:
    """Generate Vertex-specific batch metadata."""
    base_name = os.path.splitext(os.path.basename(jsonl_path))[0]
    output_dir = os.path.dirname(jsonl_path)
    output_path = os.path.join(output_dir, f"{base_name}-response.jsonl")

    # Include timestamp in batch ID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_id = f"{base_name}-{timestamp}"

    return batch_id, output_path
