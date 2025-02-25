"""Vertex AI batch processing implementation."""
import os
import time
from datetime import datetime
from typing import Dict, Optional

import polars as pl
import vertexai

from lib.app_singleton import AppSingleton
from lib.config import read_config
from lib.llm.vertex_batch_api import (
    check_batch_job_status,
    download_batch_job_output,
    send_batch_file,
)

logger = AppSingleton().get_logger()

# Define processing statuses for Vertex AI
PROCESSING_STATUSES = {"JOB_STATE_RUNNING", "JOB_STATE_PENDING", "JOB_STATE_QUEUED"}


class VertexBatchJob:
    """Class for managing Vertex AI batch jobs."""

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
        self._model_config_id = self._extract_model_config_id()
        self._model_id = None

        # Check if job is already being processed
        if os.path.exists(self._processing_file):
            with open(self._processing_file, "r") as f:
                self._batch_id = f.read().strip()

    def _extract_model_config_id(self) -> str:
        """Extract model_config_id from filename."""
        base_name = os.path.splitext(os.path.basename(self.jsonl_path))[0]
        return base_name.split("-")[0]

    def _get_model_id(self) -> str:
        """Get model ID from gen_ai_config.csv."""
        if self._model_id:
            return self._model_id

        config_path = os.path.join("ai_eval_sheets", "gen_ai_model_configs.csv")
        model_configs = pl.read_csv(config_path)

        config = model_configs.filter(pl.col("model_config_id") == self._model_config_id)
        if config.height == 0:
            raise ValueError(f"Model config ID {self._model_config_id} not found")

        self._model_id = config["model_id"][0]
        return self._model_id

    def _get_output_path(self) -> str:
        """Calculate output path from input path."""
        base_name = os.path.splitext(os.path.basename(self.jsonl_path))[0]
        output_dir = os.path.dirname(self.jsonl_path)
        return os.path.join(output_dir, f"{base_name}-response.jsonl")

    def _get_custom_id_mapping(self) -> Dict[str, str]:
        """Generate custom ID mapping from prompt mapping CSV."""
        mapping_path = self._output_path.replace("-response.jsonl", "-prompt-mapping.csv")
        if not os.path.exists(mapping_path):
            raise ValueError(f"Prompt mapping CSV not found: {mapping_path}")

        df = pl.read_csv(mapping_path)
        return {
            row["prompt_text"]: row["prompt_id"] for row in df.iter_rows(named=True)
        }

    def send(self) -> str:
        """
        Submit batch job to Vertex AI.

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

            # Get configuration
            config = read_config()
            project_id = config.get("VERTEXAI_PROJECT")
            gcs_bucket = os.getenv("GCS_BUCKET")

            if not project_id or not gcs_bucket:
                raise ValueError("Missing Vertex AI configuration (project or bucket)")

            # Get model ID
            model_id = self._get_model_id()

            # Initialize Vertex AI
            vertexai.init(project=project_id, location="us-central1")

            # Submit batch job
            self._batch_id = send_batch_file(
                jsonl_path=self.jsonl_path,
                model_id=model_id,
                gcs_bucket=gcs_bucket,
                project_id=project_id,
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
            status: Job status string (e.g., "JOB_STATE_SUCCEEDED")
        """
        config = read_config()
        project_id = config.get("VERTEXAI_PROJECT")
        if not project_id:
            raise ValueError("VERTEXAI_PROJECT not found in configuration")

        return check_batch_job_status(self.batch_id, project_id)

    def download_results(self) -> Optional[str]:
        """
        Download results of a completed batch job.

        Returns:
            str: Path to the downloaded results, or None if download failed
        """
        config = read_config()
        project_id = config.get("VERTEXAI_PROJECT")
        if not project_id:
            raise ValueError("VERTEXAI_PROJECT not found in configuration")

        # Get custom ID mapping
        custom_id_mapping = self._get_custom_id_mapping()

        return download_batch_job_output(
            batch_id=self.batch_id,
            output_path=self._output_path,
            project_id=project_id,
            custom_id_mapping=custom_id_mapping,
        )

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

                if status == "JOB_STATE_SUCCEEDED":
                    logger.info(f"Batch {self.batch_id} completed successfully")
                    result = self.download_results()
                    # Clean up processing file
                    if os.path.exists(self._processing_file):
                        os.remove(self._processing_file)
                    return result
                elif status in {"JOB_STATE_FAILED", "JOB_STATE_CANCELLED"}:
                    logger.error(f"Batch {self.batch_id} failed with status {status}")
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
