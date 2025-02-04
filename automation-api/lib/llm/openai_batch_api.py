import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from openai import OpenAI

from lib.app_singleton import AppSingleton

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)


# Statuses that indicate the batch is still processing
PROCESSING_STATUSES = {"validating", "in_progress", "finalizing"}


def send_batch_file(
    client: OpenAI, jsonl_path: str, endpoint: str = "/v1/chat/completions"
) -> str:
    """
    Send a JSONL file to OpenAI's batch API.

    Args:
        jsonl_path: Path to the JSONL file containing prompts
        endpoint: OpenAI API endpoint to use

    Returns:
        The batch ID for tracking the request
    """
    # Upload the JSONL file
    batch_input_file = client.files.create(file=open(jsonl_path, "rb"), purpose="batch")
    batch_input_file_id = batch_input_file.id

    # Generate batch ID using timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_id = f"batch-{timestamp}"

    # Create the batch
    batch = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint=endpoint,
        completion_window="24h",
        metadata={
            "batch_id": batch_id,
            "source_file": os.path.basename(jsonl_path),
        },
    )

    logger.info(f"Created batch with ID: {batch.id}")
    return batch.id


def check_batch_job_status(client: OpenAI, batch_id: str) -> str:
    """
    Get the current status of a batch job.

    Args:
        batch_id: The batch ID to check

    Returns:
        Current status of the batch job
    """
    batch = client.batches.retrieve(batch_id)
    return batch.status


def simplify_openai_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplify OpenAI batch response format to keep only essential information.

    Args:
        response_data: Raw response data from OpenAI batch API

    Returns:
        Simplified response dictionary containing only essential fields
    """
    simplified = {
        "custom_id": response_data.get("custom_id"),
        "status_code": response_data.get("response", {}).get("status_code"),
        "content": None,
        "error": response_data.get("error"),
    }

    # Extract content from choices if available
    try:
        choices = response_data.get("response", {}).get("body", {}).get("choices", [])
        if choices and len(choices) > 0:
            simplified["content"] = choices[0]["message"]["content"]
    except (KeyError, TypeError):
        pass

    return simplified


def download_batch_job_output(
    client: OpenAI, batch_id: str, output_path: str
) -> Optional[str]:
    """
    Download and simplify results for a completed batch job, including both successful
    responses and errors.

    Args:
        batch_id: The batch ID to download results for
        output_path: Path to save results file

    Returns:
        Path to the downloaded results file if successful, None if batch not completed
    """
    # Get batch info
    batch = client.batches.retrieve(batch_id)

    if batch.status != "completed":
        logger.error(f"Cannot download results - batch status is {batch.status}")
        return None

    # Create a temporary file for raw results
    temp_output = f"{output_path}.temp"
    temp_errors = f"{output_path}.errors.temp"

    # Download raw results file
    client.files.content(batch.output_file_id).write_to_file(temp_output)

    # Download error file if it exists
    if batch.error_file_id:
        client.files.content(batch.error_file_id).write_to_file(temp_errors)
    else:
        logger.info("No error file found for this batch")

    # Process and combine both files
    with open(output_path, "w", encoding="utf-8") as out_file:
        # Process successful responses
        if os.path.exists(temp_output):
            with open(temp_output, "r", encoding="utf-8") as raw_file:
                for line in raw_file:
                    try:
                        response_data = json.loads(line)
                        simplified = simplify_openai_response(response_data)
                        out_file.write(
                            json.dumps(simplified, ensure_ascii=False) + "\n"
                        )
                    except json.JSONDecodeError as e:
                        logger.error(f"Error processing line: {e}")
                        continue

        # Process error responses
        if batch.error_file_id and os.path.exists(temp_errors):
            with open(temp_errors, "r", encoding="utf-8") as error_file:
                for line in error_file:
                    try:
                        response_data = json.loads(line)
                        simplified = simplify_openai_response(response_data)
                        out_file.write(
                            json.dumps(simplified, ensure_ascii=False) + "\n"
                        )
                    except json.JSONDecodeError as e:
                        logger.error(f"Error processing error line: {e}")
                        continue

    # Clean up temporary files
    if os.path.exists(temp_output):
        os.remove(temp_output)
    if os.path.exists(temp_errors):
        os.remove(temp_errors)

    logger.info(f"Saved combined batch results (including errors) to {output_path}")
    return output_path
