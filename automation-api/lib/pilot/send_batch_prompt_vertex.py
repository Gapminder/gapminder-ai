import json
import os
import re
import time
from datetime import datetime
from typing import Optional, Tuple

import polars as pl
import vertexai
from google.cloud import storage

from lib.app_singleton import AppSingleton
from lib.config import read_config

logger = AppSingleton().get_logger()


def upload_to_gcs(local_path: str, gcs_uri: str) -> None:
    """Upload a file to Google Cloud Storage."""
    client = storage.Client()
    bucket_name, blob_path = gcs_uri.replace("gs://", "").split("/", 1)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    logger.info(f"Uploading {local_path} to {gcs_uri}")
    blob.upload_from_filename(local_path)
    logger.info("Upload complete")


def get_model_parameters(model_config_id: str, base_path: str = ".") -> dict:
    """Get model parameters from gen_ai_config.csv."""
    config_path = os.path.join(base_path, "ai_eval_sheets", "gen_ai_model_configs.csv")
    model_configs = pl.read_csv(config_path)

    config = model_configs.filter(pl.col("model_config_id") == model_config_id)
    if config.height == 0:
        raise ValueError(f"Model config ID {model_config_id} not found")

    parameters = {}
    if config["model_parameters"][0]:
        try:
            parameters = json.loads(config["model_parameters"][0])
        except json.JSONDecodeError:
            logger.warning(
                f"Could not parse model_parameters: {config['model_parameters'][0]}"
            )

    return {
        "model_id": config["model_id"][0],
        "temperature": parameters.get("temperature", 0.01),
        "max_output_tokens": parameters.get("max_output_tokens", 2048),
        "top_p": parameters.get("top_p", 0.95),
        "top_k": parameters.get("top_k", 40),
    }


def get_batch_id_and_output_path(jsonl_path: str) -> Tuple[str, str]:
    """
    Extract batch ID and generate output path from input JSONL filename.

    Args:
        jsonl_path: Path to input JSONL file

    Returns:
        Tuple of (batch_id, output_path)
    """
    # Extract base filename without extension
    base_name = os.path.basename(jsonl_path)
    match = re.match(r"^(.*?)-question_prompts\.jsonl$", base_name)
    if not match:
        raise ValueError(f"Input filename {base_name} doesn't match expected pattern")

    model_conf_id = match.group(1)
    output_dir = os.path.dirname(jsonl_path)
    output_path = os.path.join(output_dir, f"{model_conf_id}-question_response.jsonl")
    # Add timestamp to batch_id (YYYYMMDDHHMMSS format)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_id = f"{model_conf_id}-{timestamp}"

    return batch_id, output_path


def get_batch_status(batch_job) -> str:
    """Get the current status of a batch"""
    batch_job.refresh()
    return batch_job.state.name


def download_batch_results(batch_job, output_path: str) -> str:
    """
    Download results for a completed batch

    Args:
        batch_job: The batch job object
        output_path: Path to save results file

    Returns:
        Path to the downloaded results file
    """
    if not batch_job.output_location:
        raise ValueError("No output location available for this batch job")

    # Download from GCS
    client = storage.Client()
    uri = batch_job.output_location.replace("gs://", "")
    bucket_name, prefix = uri.split("/", 1)

    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))

    if not blobs:
        raise ValueError(f"No results found at {batch_job.output_location}")

    # Download first result file
    blob = blobs[0]
    blob.download_to_filename(output_path)

    logger.info(f"Saved batch results to {output_path}")
    return output_path


def process_batch_prompts(
    model_config_id: str,
    input_jsonl_path: str,
    base_path: str = ".",
    gcs_bucket: Optional[str] = None,
) -> str:
    """Process batch prompts using Vertex AI.

    Returns:
        The batch job object
    """
    # Read configuration
    config = read_config()
    project_id = config.get("VERTEX_PROJECT")
    if not project_id:
        raise ValueError("VERTEX_PROJECT not found in configuration")

    # Get GCS bucket from argument or environment
    gcs_bucket = gcs_bucket or os.getenv("GCS_BUCKET")

    # Initialize Vertex AI
    vertexai.init(project=project_id, location="us-central1")

    # Get model parameters
    model_params = get_model_parameters(model_config_id, base_path)

    # Handle GCS upload if needed
    input_uri = input_jsonl_path
    if gcs_bucket:
        gcs_path = (
            f"gs://{gcs_bucket}/batch_prompts/{os.path.basename(input_jsonl_path)}"
        )
        upload_to_gcs(input_jsonl_path, gcs_path)
        input_uri = gcs_path

    # Generate output URI
    output_uri = f"gs://{gcs_bucket}/batch_results" if gcs_bucket else None

    # Submit batch prediction job
    logger.info(f"Submitting batch prediction job for model {model_params['model_id']}")
    batch_job = vertexai.batch_prediction.BatchPredictionJob.submit(
        source_model=model_params["model_id"],
        input_dataset=input_uri,
        output_uri_prefix=output_uri,
        parameters={
            "temperature": model_params["temperature"],
            "max_output_tokens": model_params["max_output_tokens"],
            "top_p": model_params["top_p"],
            "top_k": model_params["top_k"],
        },
    )

    logger.info(f"Job resource name: {batch_job.resource_name}")
    logger.info(f"Model resource name: {batch_job.model_name}")

    return batch_job


def wait_for_batch_completion(batch_job, output_path: str) -> Optional[str]:
    """
    Wait for a batch to complete and download results when ready.

    Args:
        batch_job: The batch job object
        output_path: Path to save results file

    Returns:
        Path to results file if successful, None if batch failed/cancelled
    """
    logger.info(f"Waiting for batch {batch_job.resource_name} to complete...")
    while True:
        status = get_batch_status(batch_job)
        logger.info(f"Batch status: {status}")

        if status == "SUCCEEDED":
            # Download results
            return download_batch_results(batch_job, output_path)
        elif status in ["PENDING", "RUNNING"]:
            # Still processing, wait before checking again
            time.sleep(60)
        else:
            # Failed or cancelled
            logger.error(f"Batch {batch_job.resource_name} ended with status: {status}")
            return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Process batch prompts using Vertex AI"
    )
    parser.add_argument(
        "--model-config-id",
        type=str,
        required=True,
        help="ID of the model configuration to use",
    )
    parser.add_argument(
        "--input-jsonl", type=str, required=True, help="Path to input JSONL file"
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",
        help="Base directory containing ai_eval_sheets folder",
    )
    parser.add_argument(
        "--gcs-bucket", type=str, help="GCS bucket name for input/output (optional)"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for batch completion and download results",
    )

    args = parser.parse_args()

    try:
        # Get output path from input filename
        _, output_path = get_batch_id_and_output_path(args.input_jsonl)

        # Check for existing processing file
        processing_file = f"{output_path}.processing"
        if os.path.exists(processing_file):
            logger.info("Batch already being processed.")
            # Read and return the batch ID from the file
            with open(processing_file, "r") as f:
                batch_id = f.read().strip()
            batch_job = vertexai.batch_prediction.BatchPredictionJob(batch_id)
        else:
            # Submit new batch job
            batch_job = process_batch_prompts(
                model_config_id=args.model_config_id,
                input_jsonl_path=args.input_jsonl,
                base_path=args.base_path,
                gcs_bucket=args.gcs_bucket,
            )
            # Save batch ID to processing file
            with open(processing_file, "w") as f:
                f.write(batch_job.resource_name)

        if args.wait:
            result_path = wait_for_batch_completion(batch_job, output_path)
            if result_path:
                print(f"Results saved to: {result_path}")
        else:
            print(f"Batch ID: {batch_job.resource_name}")
    except Exception as e:
        logger.error(f"Error processing batch prompts: {str(e)}")
        raise
