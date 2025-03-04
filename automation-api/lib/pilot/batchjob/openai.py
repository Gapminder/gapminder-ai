"""OpenAI batch processing implementation."""

import json
import os
import time
from typing import Any, Dict, Optional

from openai import OpenAI

from lib.app_singleton import AppSingleton
from lib.config import read_config

from ..utils import generate_batch_id, get_output_path
from .base import BaseBatchJob

logger = AppSingleton().get_logger()
config = read_config()

# Statuses that indicate the batch is still processing
_PROCESSING_STATUSES = {"validating", "in_progress", "finalizing"}


# Provider-specific configurations
_PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = {
    "alibaba": {
        "api_key": config.get("DASHSCOPE_API_KEY", ""),
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
}


def _get_client(provider) -> OpenAI:
    """Get authorized OpenAI client with provider compatibility."""
    if provider in _PROVIDER_CONFIGS:
        return OpenAI(**_PROVIDER_CONFIGS[provider])
    return OpenAI(api_key=config["OPENAI_API_KEY"])


class OpenAIBatchJob(BaseBatchJob):
    """Class for managing OpenAI batch jobs."""

    def __init__(self, jsonl_path: str, provider: str = "openai"):
        """
        Initialize a batch job.

        Args:
            jsonl_path: Path to JSONL file containing prompts
            provider: API provider ("openai" or "alibaba")
        """
        self.jsonl_path = jsonl_path
        self._batch_id = None
        self._provider = provider
        self._output_path = get_output_path(jsonl_path)
        self._processing_file = f"{self._output_path}.processing"

        # Check if job is already being processed
        if os.path.exists(self._processing_file):
            with open(self._processing_file, "r") as f:
                self._batch_id = f.read().strip()

        # initialize client
        self._client = _get_client(provider)

    def send(self) -> str:
        """
        Submit batch job to API provider.

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

            # Send batch to OpenAI
            client = self._client
            self._batch_id = _send_batch_file(
                client, self.jsonl_path, endpoint="/v1/chat/completions"
            )

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
            status: Job status string ("completed", "failed", "processing")
        """
        return _check_batch_job_status(self._client, self.batch_id)

    def download_results(self) -> Optional[str]:
        """
        Download results of a completed batch job.

        Returns:
            str: Path to the downloaded results, or None if download failed
        """
        return _download_batch_job_output(
            self._client, self.batch_id, self._output_path
        )

    def wait_for_completion(self, poll_interval: int = 30) -> Optional[str]:
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

                if status == "completed":
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
                elif status not in _PROCESSING_STATUSES:
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


# below are helper functions
def _send_batch_file(
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

    batch_id = generate_batch_id(jsonl_path)

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


def _check_batch_job_status(client: OpenAI, batch_id: str) -> str:
    """
    Get the current status of a batch job.

    Args:
        batch_id: The batch ID to check

    Returns:
        Current status of the batch job
    """
    batch = client.batches.retrieve(batch_id)
    return batch.status


def _simplify_openai_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
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


def _download_batch_job_output(
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
                        simplified = _simplify_openai_response(response_data)
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
                        simplified = _simplify_openai_response(response_data)
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
