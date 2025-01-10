import argparse
import logging
import os
import re
import time
from datetime import datetime
from typing import Optional, Tuple

from openai import OpenAI

from lib.app_singleton import AppSingleton
from lib.config import read_config

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)

read_config()
client = OpenAI()

# Statuses that indicate the batch is still processing
PROCESSING_STATUSES = {"validating", "in_progress", "finalizing"}


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
    # FIXME: this is different every time I call it. Find a better way?
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_id = f"{model_conf_id}-{timestamp}"

    return batch_id, output_path


def get_batch_status(batch_id: str) -> str:
    """Get the current status of a batch"""
    batch = client.batches.retrieve(batch_id)
    return batch.status


def download_batch_results(batch_id: str, output_path: str) -> str:
    """
    Download results for a completed batch

    Args:
        batch_id: The batch ID to download results for
        output_path: Path to save results file

    Returns:
        Path to the downloaded results file
    """
    # Get batch info
    batch = client.batches.retrieve(batch_id)

    # Download results file
    with open(output_path, "w") as f:
        client.files.content(batch.output_file_id).write_to_file(f)

    logger.info(f"Saved batch results to {output_path}")
    return output_path


def send_batch_to_openai(jsonl_path: str) -> str:
    """
    Send a JSONL file to OpenAI's batch API using the OpenAI client.
    Uses a .processing file to cache the batch ID and avoid re-uploads.

    Args:
        jsonl_path: Path to the JSONL file containing prompts

    Returns:
        The batch ID for tracking the request
    """
    # Get batch ID and output path from input filename
    batch_id, output_path = get_batch_id_and_output_path(jsonl_path)

    # Check for existing processing file
    processing_file = f"{output_path}.processing"
    if os.path.exists(processing_file):
        logger.info("Batch already being processed.")
        # Read and return the batch ID from the file
        with open(processing_file, "r") as f:
            return f.read().strip()

    # Upload the JSONL file
    batch_input_file = client.files.create(file=open(jsonl_path, "rb"), purpose="batch")
    batch_input_file_id = batch_input_file.id

    # Create the batch
    batch = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "batch_id": batch_id,
            "source_file": os.path.basename(jsonl_path),
        },
    )

    # Create processing file with batch info
    with open(processing_file, "w") as f:
        f.write(batch.id)
        logger.info("Batch created successfully.")

    return batch.id


def wait_for_batch_completion(batch_id: str, output_path: str) -> Optional[str]:
    """
    Wait for a batch to complete and download results when ready.

    Args:
        batch_id: The batch ID to monitor
        output_path: Path to save results file

    Returns:
        Path to results file if successful, None if batch failed/cancelled
    """
    logger.info(f"Waiting for batch {batch_id} to complete...")
    while True:
        status = get_batch_status(batch_id)
        logger.info(f"Batch status: {status}")

        if status == "completed":
            # Download results
            return download_batch_results(batch_id, output_path)
        elif status in PROCESSING_STATUSES:
            # Still processing, wait before checking again
            time.sleep(60)
        else:
            # Failed or cancelled
            logger.error(f"Batch {batch_id} ended with status: {status}")
            return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send JSONL prompts to OpenAI batch API"
    )
    parser.add_argument(
        "jsonl_file", type=str, help="Path to the JSONL file containing prompts"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for batch completion and download results",
    )

    args = parser.parse_args()

    try:
        batch_id = send_batch_to_openai(args.jsonl_file)
        if args.wait:
            output_path = get_batch_id_and_output_path(args.jsonl_file)[1]
            result_path = wait_for_batch_completion(batch_id, output_path)
            if result_path:
                print(f"Results saved to: {result_path}")
        else:
            print(f"Batch ID: {batch_id}")
    except Exception as e:
        logger.error(f"Error sending batch: {str(e)}")
        raise
