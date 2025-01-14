import json
import logging
from typing import Any, Dict, Optional

import anthropic

from lib.app_singleton import AppSingleton
from lib.config import read_config

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)

# Initialize Anthropic client
read_config()  # FIXME: don't do read config in lib code
client = anthropic.Anthropic()


def send_batch_file(jsonl_path: str) -> str:
    """
    Send a batch of prompts to Anthropic API.

    Args:
        jsonl_path: Path to JSONL file containing prompts

    Returns:
        Batch ID for tracking the job
    """
    try:
        # Read and parse the JSONL file
        with open(jsonl_path, "r", encoding="utf-8") as f:
            requests = [json.loads(line) for line in f]

        # Convert to Anthropic format
        anthropic_requests = []
        for req in requests:
            messages = req["body"]["messages"]
            content = messages[0]["content"]  # Assuming single user message
            model = req["body"]["model"]
            max_tokens = req["body"].get("max_tokens", 2048)
            temperature = req["body"].get("temperature", 0.01)

            anthropic_requests.append(
                client.messages.batches.Request(
                    custom_id=req["custom_id"],
                    params=anthropic.types.MessageCreateParamsNonStreaming(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=[{"role": "user", "content": content}],
                    ),
                )
            )

        # Send batch
        batch = client.messages.batches.create(requests=anthropic_requests)
        logger.info(f"Created Anthropic batch with ID: {batch.id}")
        return batch.id

    except Exception as e:
        logger.error(f"Error sending batch to Anthropic: {str(e)}")
        raise


def check_batch_job_status(batch_id: str) -> str:
    """
    Check the status of a batch job.

    Args:
        batch_id: The batch ID to check

    Returns:
        Current processing status
    """
    try:
        batch = client.messages.batches.retrieve(batch_id)
        return batch.processing_status
    except Exception as e:
        logger.error(f"Error checking batch status: {str(e)}")
        raise


def simplify_anthropic_response(response_data: Any) -> Dict[str, Any]:
    """
    Simplify Anthropic response to consistent format.

    Args:
        response_data: Raw response from Anthropic API

    Returns:
        Simplified response dictionary
    """
    status = response_data.result.type
    simplified = {
        "custom_id": response_data.custom_id,
        "status": status,
        "content": None,
        "error": None,
    }

    if status == "succeeded":
        simplified["content"] = response_data.result.message.content[0].text
    elif status == "errored":
        simplified["error"] = (str(response_data.result.error),)

    return simplified


def download_batch_job_output(batch_id: str, output_path: str) -> Optional[str]:
    """
    Download and process batch results.

    Args:
        batch_id: The batch ID to download
        output_path: Path to save results
        custom_id_mapping: Optional mapping of custom IDs

    Returns:
        Path to the output file
    """
    try:
        with open(output_path, "w", encoding="utf-8") as out_file:
            for result in client.messages.batches.results(batch_id):
                # Convert to dict and simplify
                simplified = simplify_anthropic_response(result)

                out_file.write(json.dumps(simplified, ensure_ascii=False) + "\n")

        logger.info(f"Saved Anthropic batch results to {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Error downloading batch results: {str(e)}")
        raise
