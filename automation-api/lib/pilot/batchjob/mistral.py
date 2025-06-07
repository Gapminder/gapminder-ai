"""Mistral batch processing implementation."""

import json
import os
import time
from typing import Any, Dict, Optional

from mistralai import Mistral

from lib.app_singleton import AppSingleton
from lib.config import read_config

from ..utils import generate_batch_id
from .base import BaseBatchJob

logger = AppSingleton().get_logger()
config = read_config()

# Statuses for batch processing
_PROCESSING_STATUSES = {"QUEUED", "RUNNING", "CANCELLATION_REQUESTED"}
_TERMINAL_STATUSES = {"SUCCESS", "FAILED", "TIMEOUT_EXCEEDED", "CANCELLED"}


def _get_client() -> Mistral:
    """Get authorized Mistral client."""
    return Mistral(api_key=config["MISTRAL_API_KEY"])


def _simplify_mistral_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplify Mistral batch response format to keep only essential information.

    Args:
        response_data: Raw response data from Mistral batch API

    Returns:
        Simplified response dictionary containing only essential fields
    """
    try:
        status_code = response_data.get("response", {}).get("status_code", 500)
    except AttributeError:
        logger.error("no status code for response. default to 500.")
        logger.error("respose data:")
        logger.error(str(response_data))
        status_code = 500

    simplified = {
        "custom_id": response_data.get("custom_id"),
        "status_code": status_code,
        "content": None,
        "error": None,
    }

    # Extract content from choices if available
    if status_code == 200:
        choices = response_data.get("response", {}).get("body", {}).get("choices", [])
        if choices and len(choices) > 0:
            simplified["content"] = choices[0]["message"]["content"]
    else:
        error = response_data.get("error")
        if error:
            simplified["error"] = error
        # sometimes there is no error message, we create one
        else:
            simplified["error"] = f"Error: status code {status_code}"

    return simplified


class MistralBatchJob(BaseBatchJob):
    """Class for managing Mistral batch jobs."""

    def __init__(
        self,
        jsonl_path: str,
        model_id: Optional[str] = None,
        timeout_hours: Optional[int] = None,
    ):
        """
        Initialize a batch job.

        Args:
            jsonl_path: Path to JSONL file containing prompts
            model_id: Mistral model ID to use (e.g., mistral-small-latest, codestral-latest)
            timeout_hours: Number of hours after which the job should expire (default: 24, max: 168)
        """
        super().__init__(jsonl_path)
        self.model_id = model_id or "mistral-small-latest"
        self.timeout_hours = timeout_hours
        self._client = _get_client()

    def send(self) -> str:
        """
        Submit batch job to Mistral API.

        Returns:
            batch_id: Unique identifier for the batch job
        """
        try:
            # Check if response file already exists
            if self.should_skip_processing():
                return self._output_path

            # Check for existing processing file
            if os.path.exists(self._processing_file):
                logger.info("Batch already being processed.")
                with open(self._processing_file, "r") as f:
                    self._batch_id = f.read().strip()
                    return self._batch_id

            # Upload the file
            batch_file = self._client.files.upload(
                file={
                    "file_name": os.path.basename(self.jsonl_path),
                    "content": open(self.jsonl_path, "rb"),
                },
                purpose="batch",
            )

            batch_id = generate_batch_id(self.jsonl_path)

            # Create the batch job with additional parameters
            create_params: Dict[str, Any] = {
                "input_files": [batch_file.id],
                "model": self.model_id,
                "endpoint": "/v1/chat/completions",
                "metadata": {"batch_id": batch_id},
            }

            # Add timeout_hours if specified
            if self.timeout_hours is not None:
                timeout_value = self.timeout_hours
                if timeout_value > 168:
                    timeout_value = 168  # Cap at 7 days
                create_params["timeout_hours"] = timeout_value

            batch_job = self._client.batch.jobs.create(**create_params)

            self._batch_id = str(batch_job.id)

            # Create processing file with batch info
            with open(self._processing_file, "w") as f:
                f.write(self._batch_id)
                logger.info(f"Batch created successfully with model {self.model_id}")

            return self._batch_id
        except Exception as e:
            logger.error(f"Error sending batch: {str(e)}")
            raise

    def check_status(self) -> str:
        """
        Check status of the batch job.

        Returns:
            status: Job status string
        """
        try:
            batch_job = self._client.batch.jobs.get(job_id=self.batch_id)
            status = batch_job.status

            # Log additional statistics if available
            if hasattr(batch_job, "total_requests") and hasattr(batch_job, "succeeded_requests"):
                total = batch_job.total_requests or 0
                succeeded = batch_job.succeeded_requests or 0
                failed = batch_job.failed_requests or 0

                if total > 0:
                    percent_done = round(((succeeded + failed) / total) * 100, 2)
                    logger.info(f"Progress: {percent_done}% ({succeeded} succeeded, {failed} failed, {total} total)")

            return status
        except Exception as e:
            logger.error(f"Error checking batch status: {str(e)}")
            raise

    def download_results(self) -> Optional[str]:
        """
        Download results of a completed batch job.

        Returns:
            str: Path to the downloaded results, or None if download failed
        """
        try:
            # Get batch job details
            batch_job = self._client.batch.jobs.get(job_id=self.batch_id)

            if batch_job.status != "SUCCESS":
                logger.error(f"Cannot download results - batch status is {batch_job.status}")
                return None

            # Create output file path
            output_file_path = self._output_path
            temp_output = f"{self._output_path}.temp"
            error_temp_path = f"{self._output_path}.errors.temp"

            # Download output file
            if batch_job.output_file:
                output_content = self._client.files.download(file_id=batch_job.output_file)

                with open(temp_output, "wb") as f:
                    for chunk in output_content.iter_bytes():
                        f.write(chunk)

                # Download error file if it exists
                if batch_job.error_file:
                    error_content = self._client.files.download(file_id=batch_job.error_file)

                    with open(error_temp_path, "wb") as f:
                        for chunk in error_content.iter_bytes():
                            f.write(chunk)

                # Process and simplify both files
                with open(output_file_path, "w", encoding="utf-8") as out_file:
                    # Process successful responses
                    if os.path.exists(temp_output):
                        with open(temp_output, "r", encoding="utf-8") as raw_file:
                            for line in raw_file:
                                try:
                                    response_data = json.loads(line)
                                    simplified = _simplify_mistral_response(response_data)
                                    out_file.write(json.dumps(simplified, ensure_ascii=False) + "\n")
                                except json.JSONDecodeError as e:
                                    logger.error(f"Error processing line: {e}")
                                    continue

                    # Process error responses
                    if batch_job.error_file and os.path.exists(error_temp_path):
                        with open(error_temp_path, "r", encoding="utf-8") as error_file:
                            for line in error_file:
                                try:
                                    response_data = json.loads(line)
                                    simplified = _simplify_mistral_response(response_data)
                                    out_file.write(json.dumps(simplified, ensure_ascii=False) + "\n")
                                except json.JSONDecodeError as e:
                                    logger.error(f"Error processing error line: {e}")
                                    continue

                # Clean up temporary files
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                if os.path.exists(error_temp_path):
                    os.remove(error_temp_path)

                logger.info(f"Saved simplified batch results to {output_file_path}")
                return output_file_path
            else:
                logger.error("No output file available for this batch")
                return None

        except Exception as e:
            logger.error(f"Error downloading batch results: {str(e)}")
            return None

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

                if status == "SUCCESS":
                    logger.info(f"Batch {self.batch_id} completed successfully")
                    result = self.download_results()
                    # Clean up processing file
                    if os.path.exists(self._processing_file):
                        os.remove(self._processing_file)
                    return result
                elif status in _TERMINAL_STATUSES:
                    logger.error(f"Batch {self.batch_id} ended with status: {status}")
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

    def cancel(self) -> bool:
        """
        Request cancellation of the batch job.

        Returns:
            bool: True if cancellation request was successful
        """
        try:
            self._client.batch.jobs.cancel(job_id=self.batch_id)
            logger.info(f"Requested cancellation for batch {self.batch_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling batch: {str(e)}")
            return False

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
