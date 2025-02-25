"""Anthropic batch processing implementation."""
import os
import time
from typing import Optional

import anthropic

from lib.app_singleton import AppSingleton
from lib.config import read_config
from lib.llm.anthropic_batch_api import (
    check_batch_job_status,
    download_batch_job_output,
    send_batch_file,
)

logger = AppSingleton().get_logger()

# Define processing statuses for Anthropic
PROCESSING_STATUSES = {"processing"}


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
