"""Anthropic batch processing implementation."""
import os
import time
from typing import Optional

from lib.app_singleton import AppSingleton
from lib.llm.anthropic_batch_api import (
    check_batch_job_status,
    download_batch_job_output,
    send_batch_file,
)

logger = AppSingleton().get_logger()


def send_batch(jsonl_path: str) -> str:
    """Submit batch job to Anthropic.

    Args:
        jsonl_path: Path to JSONL file containing prompts

    Returns:
        batch_id: Unique identifier for the batch job
    """
    try:
        output_path = get_batch_metadata(jsonl_path)[1]

        # Check for existing processing file
        processing_file = f"{output_path}.processing"
        if os.path.exists(processing_file):
            logger.info("Batch already being processed.")
            with open(processing_file, "r") as f:
                return f.read().strip()

        # Send batch to Anthropic
        batch_id = send_batch_file(jsonl_path)

        # Create processing file with batch info
        with open(processing_file, "w") as f:
            f.write(batch_id)
            logger.info("Batch created successfully.")

        return batch_id
    except Exception as e:
        logger.error(f"Error sending batch: {str(e)}")
        raise


def check_status(batch_id: str) -> str:
    """Check status of a batch job.

    Args:
        batch_id: Batch job identifier

    Returns:
        status: Job status string ("ended", "processing")
    """
    return check_batch_job_status(batch_id)


def download_results(batch_id: str, output_path: str) -> Optional[str]:
    """Download results of a completed batch job.

    Args:
        batch_id: Batch job identifier
        output_path: Path where to save the results

    Returns:
        str: Path to the downloaded results, or None if download failed
    """
    return download_batch_job_output(batch_id, output_path)


def wait_for_completion(
    batch_id: str, output_path: str, poll_interval: int = 60
) -> Optional[str]:
    """Wait for batch job completion and download results.

    Args:
        batch_id: Batch job identifier
        output_path: Path where to save the results
        poll_interval: Seconds between status checks

    Returns:
        str: Path to the downloaded results, or None if job failed
    """
    while True:
        status = check_status(batch_id)
        if status == "ended":
            return download_results(batch_id, output_path)
        time.sleep(poll_interval)


def get_batch_metadata(jsonl_path: str) -> tuple[str, str]:
    """Get batch ID and output path based on input file.

    Args:
        jsonl_path: Path to input JSONL file

    Returns:
        tuple: (batch_id, output_path)
    """
    base_name = os.path.splitext(os.path.basename(jsonl_path))[0]
    output_dir = os.path.dirname(jsonl_path)
    output_path = os.path.join(output_dir, f"{base_name}-response.jsonl")
    return base_name, output_path
