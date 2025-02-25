"""Anthropic batch processing implementation."""
import json
import os
import time
from typing import Any, Dict, Optional

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from lib.app_singleton import AppSingleton
from lib.config import read_config

logger = AppSingleton().get_logger()

# Define processing statuses for Anthropic
PROCESSING_STATUSES = {"processing"}


def send_batch_file(client: anthropic.Anthropic, jsonl_path: str) -> str:
    """
    Send a batch of prompts to Anthropic API.

    Args:
        client: Anthropic client
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
                Request(
                    custom_id=req["custom_id"],
                    params=MessageCreateParamsNonStreaming(
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


def check_batch_job_status(client: anthropic.Anthropic, batch_id: str) -> str:
    """
    Check the status of a batch job.

    Args:
        client: Anthropic client
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


def simplify_anthropic_response(response_ Any) -> Dict[str, Any]:
    """
    Simplify Anthropic response to consistent format.

    Args:
        response_ Raw response from Anthropic API

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


def download_batch_job_output(
    client: anthropic.Anthropic, batch_id: str, output_path: str
) -> Optional[str]:
    """
    Download and process batch results.

    Args:
        client: Anthropic client
        batch_id: The batch ID to download
        output_path: Path to save results

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


class AnthropicBatchJob:
    """Class for managing Anthropic batch jobs."""

    def __init__(self, jsonl_path: str):
        """
        Initialize a batch job.

        Args:
            jsonl_path: Path to JSONL file containing prompts
        """
        self.jsonl_path = jsonl_path
        self._batch_id = None
        self._output_path = self._get_output_path()
        self._processing_file = f"{self._output_path}.processing"

        # Check if job is already being processed
        if os.path.exists(self._processing_file):
            with open(self._processing_file, "r") as f:
                self._batch_id = f.read().strip()

    def _get_output_path(self) -> str:
        """Calculate output path from input path."""
        base_name = os.path.splitext(os.path.basename(self.jsonl_path))[0]
        output_dir = os.path.dirname(self.jsonl_path)
        return os.path.join(output_dir, f"{base_name}-response.jsonl")

    def _authorize_client(self) -> anthropic.Anthropic:
        """Get authorized Anthropic client."""
        config = read_config()
        return anthropic.Anthropic(api_key=config["ANTHROPIC_API_KEY"])

    def send(self) -> str:
        """
        Submit batch job to Anthropic.

        Returns:
            batch_id: Unique identifier for the batch job
        """
        try:
            # Check for existing processing file
            if os.path.exists(self._processing_file):
                logger.info("Batch already being processed.")
                with open(self._processing_file, "r") as f:
                    self._batch_id = f.read().strip()
                    return self._batch_id

            # Send batch to Anthropic
            client = self._authorize_client()
            self._batch_id = send_batch_file(client, self.jsonl_path)

            # Create processing file with batch info
            with open(self._processing_file, "w") as f:
                f.write(self._batch_id)
                logger.info("Batch created successfully.")

            return self._batch_id
        except Exception as e:
            logger.error(f"Error sending batch: {str(e)}")
            raise

    def check_status(self) -> str:
        """
        Check status of the batch job.

        Returns:
            status: Job status string ("ended", "processing")
        """
        client = self._authorize_client()
        return check_batch_job_status(client, self.batch_id)

    def download_results(self) -> Optional[str]:
        """
        Download results of a completed batch job.

        Returns:
            str: Path to the downloaded results, or None if download failed
        """
        client = self._authorize_client()
        return download_batch_job_output(client, self.batch_id, self._output_path)

    def wait_for_completion(self, poll_interval: int = 60) -> Optional[str]:
        """
        Wait for batch job completion and download results.

        Args:
            poll_interval: Seconds between status checks

        Returns:
            str: Path to the downloaded results, or None if job failed
        """
        logger.info(f"Waiting for batch {self.batch_id} to complete...")
        try:
            while True:
                status = self.check_status()
                logger.info(f"Current status: {status}")

                if status == "ended":
                    logger.info(f"Batch {self.batch_id} completed successfully")
                    result = self.download_results()
                    # Clean up processing file
                    if os.path.exists(self._processing_file):
                        os.remove(self._processing_file)
                    return result
                elif status == "failed":
                    logger.error(f"Batch {self.batch_id} failed")
                    # Clean up processing file
                    if os.path.exists(self._processing_file):
                        os.remove(self._processing_file)
                    return None
                elif status not in PROCESSING_STATUSES:
                    logger.warning(f"Unexpected status: {status}")

                time.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Error while waiting for batch completion: {str(e)}")
            return None

    @property
    def batch_id(self) -> str:
        """Get the batch job ID."""
        if self._batch_id:
            return self._batch_id
        else:
            raise ValueError("The batch job is not started")

    @property
    def output_path(self) -> str:
        """Get the output file path."""
        return self._output_path
