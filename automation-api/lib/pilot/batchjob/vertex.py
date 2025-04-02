"""Vertex AI batch processing implementation."""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import polars as pl
import vertexai
from google.cloud import storage
from vertexai.batch_prediction import BatchPredictionJob

from lib.app_singleton import AppSingleton
from lib.config import read_config

from ..utils import get_batch_id_and_output_path
from .base import BaseBatchJob

logger = AppSingleton().get_logger()

# Define processing statuses for Vertex AI
_PROCESSING_STATUSES = {"JOB_STATE_RUNNING", "JOB_STATE_PENDING", "JOB_STATE_QUEUED"}


class VertexBatchJob(BaseBatchJob):
    """Class for managing Vertex AI batch jobs."""

    def __init__(self, jsonl_path: str, model_id: str):
        """
        Initialize a batch job.

        Note:
            Vertex AI doesn't support setting model in the
            jsonl prompts. So we need to set it when initialization.
            and note that model id (eg gemini-pro-1.0) is not
            model config id (eg mc041).

        Args:
            jsonl_path: Path to JSONL file containing prompts
            model_id: The model to send to
        """
        self.jsonl_path = jsonl_path
        _, output_path = get_batch_id_and_output_path(jsonl_path)
        self._batch_id = None
        self._output_path = output_path
        self._processing_file = f"{self._output_path}.processing"
        self._model_id = model_id

        # find custom id mapping file
        # because vertex AI doesn't support custom id in the
        # request file, so we create a local file for custom id.
        mapping_path = self._output_path.replace("-response.jsonl", "-prompt-mapping.csv")
        if not os.path.exists(mapping_path):
            raise ValueError(f"Prompt mapping CSV file not found: {mapping_path}")
        self._custom_id_mapping = {}
        # Read CSV using polars
        df = pl.read_csv(mapping_path)

        # Create mapping from prompt text to ID
        for row in df.iter_rows(named=True):
            prompt_text = row["prompt_text"]
            custom_id = row["prompt_id"]
            self._custom_id_mapping[prompt_text] = custom_id

            # Check if job is already being processed
            if os.path.exists(self._processing_file):
                with open(self._processing_file, "r") as f:
                    self._batch_id = f.read().strip()

        # initial vertexai
        config = read_config()

        project_id = config.get("VERTEXAI_PROJECT")
        if not project_id:
            raise ValueError("VERTEXAI_PROJECT not found in configuration")
        self._project_id = project_id

        gcs_bucket = os.getenv("GCS_BUCKET")
        if not gcs_bucket:
            raise ValueError("GCS_BUCKET environment variable is required")
        self._gcs_bucket = gcs_bucket

        vertexai.init(project=project_id, location="us-central1")

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

            # Submit batch job
            self._batch_id = _send_batch_file(
                jsonl_path=self.jsonl_path,
                model_id=self._model_id,
                gcs_bucket=self._gcs_bucket,
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
        return _check_batch_job_status(self.batch_id)

    def download_results(self) -> Optional[str]:
        """
        Download results of a completed batch job.

        Returns:
            str: Path to the downloaded results, or None if download failed
        """
        return _download_batch_job_output(
            self.batch_id,
            self._output_path,
            self._custom_id_mapping,
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


# Below are helper functions
def _send_batch_file(
    jsonl_path: str,
    model_id: str,
    gcs_bucket: str,
) -> str:
    """
    Send a JSONL file to Vertex AI's batch API.

    Args:
        jsonl_path: Path to the JSONL file containing prompts
        model_id: Vertex AI model ID
        gcs_bucket: GCS bucket name

    Returns:
        The batch job resource name for tracking the request
    """
    # Upload to GCS with timestamp folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(jsonl_path)
    blob_path = f"batch_prompts/{timestamp}/{filename}"

    # Upload file
    client = storage.Client()
    bucket = client.bucket(gcs_bucket)
    blob = bucket.blob(blob_path)
    input_uri = f"gs://{gcs_bucket}/{blob_path}"

    logger.info(f"Uploading {jsonl_path} to {input_uri}")
    blob.upload_from_filename(jsonl_path, timeout=20 * 60)
    logger.info("Upload complete")

    # Generate output URI
    output_uri = f"gs://{gcs_bucket}/batch_results"

    # Submit batch prediction job
    # Strip vertex_ai/ prefix if present
    model_id = model_id.replace("vertex_ai/", "")
    logger.info(f"Submitting batch prediction job for model {model_id}")
    batch_job = BatchPredictionJob.submit(
        source_model=model_id,
        input_dataset=input_uri,
        output_uri_prefix=output_uri,
    )

    logger.info(f"Job resource name: {batch_job.resource_name}")
    return batch_job.resource_name


def _check_batch_job_status(batch_id: str) -> str:
    """
    Get the current status of a batch job.

    Args:
        batch_id: The batch job resource name

    Returns:
        Current status of the batch job
    """
    batch_job = BatchPredictionJob(batch_id)
    batch_job.refresh()
    return batch_job.state.name


def _simplify_vertex_response(response_data: Dict[str, Any], custom_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Simplify Vertex AI batch response format to keep only essential information.

    Args:
        response_data: Raw response data from Vertex AI batch API
        custom_id: Custom ID to include in the response

    Returns:
        Simplified response dictionary containing only essential fields
    """
    simplified = {
        "custom_id": custom_id,
        "status_code": response_data.get("status"),
        "content": None,
        "error": None,
    }

    try:
        candidates = response_data.get("response", {}).get("candidates", [])
        if candidates and len(candidates) > 0:
            content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text")
            simplified["content"] = content
    except (KeyError, TypeError, IndexError) as e:
        # FIXME: should read error from the response_data.
        simplified["error"] = str(e)

    return simplified


def _process_and_simplify_results(input_path: str, output_path: str, custom_id_mapping: Dict[str, str]) -> None:
    """
    Process and simplify batch results from raw JSONL to simplified format.

    Args:
        input_path: Path to raw results JSONL file
        output_path: Path to save simplified results
        custom_id_mapping: Dictionary mapping request strings to custom IDs
    """
    with (
        open(input_path, "r", encoding="utf-8") as raw_file,
        open(output_path, "w", encoding="utf-8") as out_file,
    ):
        for i, line in enumerate(raw_file):
            try:
                response_data = json.loads(line)
                # Get custom_id from mapping using request string
                request_str = response_data["request"]["contents"][0]["parts"][0]["text"]
                custom_id = custom_id_mapping.get(request_str)
                if not custom_id:
                    logger.debug("would not find id for request:")
                    logger.debug(request_str)
                simplified = _simplify_vertex_response(response_data, custom_id)
                out_file.write(json.dumps(simplified, ensure_ascii=False) + "\n")
            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"Error processing line {i}: {e}")
                continue


def _download_batch_job_output(
    batch_id: str,
    output_path: str,
    custom_id_mapping: Dict[str, str],
) -> Optional[str]:
    """
    Download and simplify results for a completed batch job.

    Args:
        batch_id: The batch job resource name
        output_path: Path to save results file
        project_id: GCP project ID
        custom_id_mapping: Dictionary mapping request strings to custom IDs
        location: GCP region

    Returns:
        Path to the downloaded results file if successful, None if batch not completed
    """
    batch_job = BatchPredictionJob(batch_id)

    if not batch_job.has_succeeded:
        logger.error(f"Cannot download results - batch status is {batch_job.state.name}")
        return None

    if not batch_job.output_location:
        logger.error("No output location available for this batch job")
        return None

    # Download from GCS
    client = storage.Client()
    uri = batch_job.output_location.replace("gs://", "")
    bucket_name, prefix = uri.split("/", 1)
    bucket = client.bucket(bucket_name)

    # Look for predictions.jsonl
    predictions_blob = None
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith("predictions.jsonl"):
            predictions_blob = blob
            break

    if not predictions_blob:
        logger.error(f"No predictions.jsonl found at {batch_job.output_location}")
        return None

    # Create a temporary file for raw results
    temp_output = f"{output_path}.temp"
    predictions_blob.download_to_filename(temp_output)

    # Process and simplify the results
    _process_and_simplify_results(temp_output, output_path, custom_id_mapping)

    # Clean up temporary file
    os.remove(temp_output)

    logger.info(f"Saved simplified batch results to {output_path}")
    return output_path
