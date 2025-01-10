import argparse
import logging
import os
import re
from datetime import datetime
from typing import Tuple

from openai import OpenAI

from lib.app_singleton import AppSingleton
from lib.config import read_config

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)


read_config()
client = OpenAI()


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


def send_batch_to_openai(jsonl_path: str) -> str:
    """
    Send a JSONL file to OpenAI's batch API using the OpenAI client.
    Uses a .processing file to cache the batch ID and avoid re-uploads.

    Args:
        jsonl_path: Path to the JSONL file containing prompts

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
        # write the batch id to file
        f.write(batch.id)
        logger.info("Batch created successfully.")

    return batch.id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send JSONL prompts to OpenAI batch API"
    )
    parser.add_argument(
        "jsonl_file", type=str, help="Path to the JSONL file containing prompts"
    )

    args = parser.parse_args()

    try:
        response = send_batch_to_openai(args.jsonl_file)
        print(f"ID: {response}")
    except Exception as e:
        logger.error(f"Error sending batch: {str(e)}")
        raise
