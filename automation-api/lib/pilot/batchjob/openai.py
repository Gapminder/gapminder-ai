"""OpenAI batch processing implementation."""
import os
import time
from typing import Optional

from openai import OpenAI

from lib.app_singleton import AppSingleton
from lib.config import read_config
from lib.llm.openai_batch_api import (
    check_batch_job_status,
    download_batch_job_output,
    send_batch_file,
)

logger = AppSingleton().get_logger()


def _authorize_client(provider: str = "openai") -> OpenAI:
    """Get authorized OpenAI client with Alibaba compatibility."""
    config = read_config()

    if provider == "alibaba":
        return OpenAI(
            api_key=config["DASHSCOPE_API_KEY"],
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    return OpenAI(api_key=config["OPENAI_API_KEY"])


def send_batch(
    jsonl_path: str, endpoint: str = "/v1/chat/completions", provider: str = "openai"
) -> str:
    """Submit batch job to OpenAI.

    Args:
        jsonl_path: Path to JSONL file containing prompts
        endpoint: OpenAI API endpoint

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

        # Send batch to OpenAI
        client = _authorize_client(provider)
        batch_id = send_batch_file(client, jsonl_path, endpoint)

        # Create processing file with batch info
        with open(processing_file, "w") as f:
            f.write(batch_id)
            logger.info("Batch created successfully.")

        return batch_id
    except Exception as e:
        logger.error(f"Error sending batch: {str(e)}")
        raise


def check_status(batch_id: str, provider: str = "openai") -> str:
    """Check status of a batch job.

    Args:
        batch_id: Batch job identifier
        provider: API provider ("openai" or "alibaba")

    Returns:
        status: Job status string ("completed", "failed", "processing")
    """
    client = _authorize_client(provider)
    return check_batch_job_status(client, batch_id)


def download_results(
    batch_id: str, output_path: str, provider: str = "openai"
) -> Optional[str]:
    """Download results of a completed batch job.

    Args:
        batch_id: Batch job identifier
        output_path: Path where to save the results
        provider: API provider ("openai" or "alibaba")

    Returns:
        str: Path to the downloaded results, or None if download failed
    """
    client = _authorize_client(provider)
    return download_batch_job_output(client, batch_id, output_path)


def wait_for_completion(
    batch_id: str, output_path: str, poll_interval: int = 30, provider: str = "openai"
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
        status = check_status(batch_id, provider)
        if status == "completed":
            return download_results(batch_id, output_path, provider)
        elif status == "failed":
            return None
        time.sleep(poll_interval)


def get_batch_metadata(jsonl_path: str) -> tuple[str, str]:
    """Get batch ID and output path based on input file.

    Args:
        jsonl_path: Path to input JSONL file

    Returns:
        tuple: (batch_id, output_path)
    """
    # Implement the same logic as in current get_batch_id_and_output_path
    batch_id = jsonl_path.replace(".jsonl", "")
    output_path = f"{batch_id}_output.jsonl"
    return batch_id, output_path
