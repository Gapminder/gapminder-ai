import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import vertexai
from google.cloud import storage
from vertexai.batch_prediction import BatchPredictionJob

from lib.app_singleton import AppSingleton

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)


def send_batch_file(
    jsonl_path: str,
    model_id: str,
    gcs_bucket: str,
    project_id: str,
    location: str = "us-central1",
) -> str:
    """
    Send a JSONL file to Vertex AI's batch API.

    Args:
        jsonl_path: Path to the JSONL file containing prompts
        model_id: Vertex AI model ID
        gcs_bucket: GCS bucket name
        project_id: GCP project ID
        location: GCP region

    Returns:
        The batch job resource name for tracking the request
    """
    # Initialize Vertex AI
    vertexai.init(project=project_id, location=location)

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


def check_batch_job_status(
    batch_id: str, project_id: str, location: str = "us-central1"
) -> str:
    """
    Get the current status of a batch job.

    Args:
        batch_id: The batch job resource name
        project_id: GCP project ID
        location: GCP region

    Returns:
        Current status of the batch job
    """
    # FIXME: don't init each time..
    vertexai.init(project=project_id, location=location)
    batch_job = BatchPredictionJob(batch_id)
    batch_job.refresh()
    return batch_job.state.name


def simplify_vertex_response(
    response_data: Dict[str, Any], custom_id: Optional[str] = None
) -> Dict[str, Any]:
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
        simplified["error"] = str(e)
        simplified["status_code"] = "ERROR_IN_POSTPROCESSING"

    return simplified


def _process_and_simplify_results(
    input_path: str, output_path: str, custom_id_mapping: Dict[str, str]
) -> None:
    """
    Process and simplify batch results from raw JSONL to simplified format.

    Args:
        input_path: Path to raw results JSONL file
        output_path: Path to save simplified results
        custom_id_mapping: Dictionary mapping request strings to custom IDs
    """
    with open(input_path, "r", encoding="utf-8") as raw_file, open(
        output_path, "w", encoding="utf-8"
    ) as out_file:
        for i, line in enumerate(raw_file):
            try:
                response_data = json.loads(line)
                # Get custom_id from mapping using request string
                request_str = response_data["request"]["contents"][0]["parts"][0][
                    "text"
                ]
                custom_id = custom_id_mapping.get(request_str)
                if not custom_id:
                    logger.debug("would not find id for request:")
                    logger.debug(request_str)
                simplified = simplify_vertex_response(response_data, custom_id)
                out_file.write(json.dumps(simplified, ensure_ascii=False) + "\n")
            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"Error processing line {i}: {e}")
                continue


def download_batch_job_output(
    batch_id: str,
    output_path: str,
    project_id: str,
    custom_id_mapping: Dict[str, str],
    location: str = "us-central1",
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
    vertexai.init(project=project_id, location=location)
    batch_job = BatchPredictionJob(batch_id)

    if not batch_job.has_succeeded:
        logger.error(
            f"Cannot download results - batch status is {batch_job.state.name}"
        )
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
