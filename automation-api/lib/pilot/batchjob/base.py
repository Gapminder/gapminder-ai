"""Base class for batch job implementations."""
import abc
import os
import time
from typing import Optional

from lib.app_singleton import AppSingleton

logger = AppSingleton().get_logger()


class BaseBatchJob(abc.ABC):
    """Abstract base class for batch job implementations."""

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
        self._is_completed = False

        # Check if job is already being processed
        if os.path.exists(self._processing_file):
            with open(self._processing_file, "r") as f:
                self._batch_id = f.read().strip()

        # Check if job is already completed
        if os.path.exists(self._output_path):
            self._is_completed = True

    @abc.abstractmethod
    def send(self) -> str:
        """
        Submit batch job to the API provider.

        Returns:
            batch_id: Unique identifier for the batch job
        """
        pass

    @abc.abstractmethod
    def check_status(self) -> str:
        """
        Check status of the batch job.

        Returns:
            status: Job status string
        """
        pass

    @abc.abstractmethod
    def download_results(self) -> Optional[str]:
        """
        Download results of a completed batch job.

        Returns:
            str: Path to the downloaded results, or None if download failed
        """
        pass

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
                elif status not in self._get_processing_statuses():
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

    def _get_output_path(self) -> str:
        """Calculate output path from input path."""
        base_name = os.path.splitext(os.path.basename(self.jsonl_path))[0]
        output_dir = os.path.dirname(self.jsonl_path)
        return os.path.join(output_dir, f"{base_name}-response.jsonl")

    @staticmethod
    def _get_processing_statuses() -> set[str]:
        """Get set of statuses that indicate the batch is still processing."""
        return {"processing", "in_progress", "validating", "finalizing"}
