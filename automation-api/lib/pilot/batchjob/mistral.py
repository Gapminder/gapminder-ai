"""Mistral batch processing implementation."""

import json
import os
import time
from typing import Any, Dict, Optional

from mistralai import Mistral

from lib.app_singleton import AppSingleton
from lib.config import read_config

from ..utils import generate_batch_id, get_output_path
from .base import BaseBatchJob

logger = AppSingleton().get_logger()
config = read_config()

# Statuses for batch processing
_PROCESSING_STATUSES = {"QUEUED", "RUNNING"}
_TERMINAL_STATUSES = {"SUCCESS", "FAILED", "TIMEOUT_EXCEEDED", "CANCELLED"}


def _get_client() -> Mistral:
    """Get authorized Mistral client."""
    return Mistral(api_key=config["MISTRAL_API_KEY"])


class MistralBatchJob(BaseBatchJob):
    """Class for managing Mistral batch jobs."""

    def __init__(self, jsonl_path: str):
        """
        Initialize a batch job.

        Args:
            jsonl_path: Path to JSONL file containing prompts
        """
        self.jsonl_path = jsonl_path
        self._batch_id = None
        self._output_path = get_output_path(jsonl_path)
        self._processing_file = f"{self._output_path}.processing"

        # Check if job is already being processed
        if os.path.exists(self._processing_file):
            with open(self._processing_file, "r") as f:
                self._batch_id = f.read().strip()

        # initialize client
        self._client = _get_client()

    def send(self) -> str:
        """
        Submit batch job to Mistral API.

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

            # Upload the file
            batch_file = self._client.files.upload(
                file={
                    "file_name": os.path.basename(self.jsonl_path),
                    "content": open(self.jsonl_path, "rb"),
                },
                purpose="batch"
            )
            
            batch_id = generate_batch_id(self.jsonl_path)
            
            # Create the batch job
            batch_job = self._client.batch.jobs.create(
                input_files=[batch_file.id],
                model="mistral-small-latest",  # Default model, can be parameterized
                endpoint="/v1/chat/completions",
                metadata={"batch_id": batch_id}
            )
            
            self._batch_id = batch_job.id

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
            status: Job status string
        """
        try:
            batch_job = self._client.batch.jobs.get(job_id=self.batch_id)
            return batch_job.status
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
            
            # Download output file
            if batch_job.output_file:
                output_content = self._client.files.download(file_id=batch_job.output_file)
                
                with open(output_file_path, "w", encoding="utf-8") as f:
                    if hasattr(output_content, 'stream'):
                        for chunk in output_content.stream:
                            f.write(chunk.decode("utf-8"))
                    else:
                        f.write(output_content)
                
                logger.info(f"Saved batch results to {output_file_path}")
                
                # Download and append error file if it exists
                if batch_job.error_file:
                    error_temp_path = f"{self._output_path}.errors.temp"
                    error_content = self._client.files.download(file_id=batch_job.error_file)
                    
                    with open(error_temp_path, "w", encoding="utf-8") as f:
                        if hasattr(error_content, 'stream'):
                            for chunk in error_content.stream:
                                f.write(chunk.decode("utf-8"))
                        else:
                            f.write(error_content)
                    
                    # Append error content to main output file
                    with open(error_temp_path, "r", encoding="utf-8") as error_file:
                        with open(output_file_path, "a", encoding="utf-8") as main_file:
                            for line in error_file:
                                main_file.write(line)
                    
                    # Clean up temp file
                    if os.path.exists(error_temp_path):
                        os.remove(error_temp_path)
                    
                    logger.info(f"Added error results to {output_file_path}")
                
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
                elif status in {"FAILED", "TIMEOUT_EXCEEDED", "CANCELLED"}:
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
