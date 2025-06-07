"""Main entry point for batch prompt processing with LLM providers."""

import argparse
from typing import Dict, Optional, Type

from lib.app_singleton import AppSingleton
from lib.config import read_config
from lib.pilot.batchjob.anthropic import AnthropicBatchJob
from lib.pilot.batchjob.base import BaseBatchJob
from lib.pilot.batchjob.litellm import LiteLLMBatchJob
from lib.pilot.batchjob.mistral import MistralBatchJob
from lib.pilot.batchjob.openai import OpenAIBatchJob
from lib.pilot.batchjob.vertex import VertexBatchJob

logger = AppSingleton().get_logger()

# Map provider names to their batch job classes
PROVIDER_CLASSES: Dict[str, Type] = {
    "openai": OpenAIBatchJob,
    "anthropic": AnthropicBatchJob,
    "vertex": VertexBatchJob,
    "litellm": LiteLLMBatchJob,
    "mistral": MistralBatchJob,
}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Send JSONL prompts to LLM batch APIs")
    parser.add_argument("jsonl_file", type=str, help="Path to the JSONL file containing prompts")
    parser.add_argument(
        "--method",
        type=str,
        required=True,
        choices=list(PROVIDER_CLASSES.keys()),
        help="LLM provider to use for processing",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for batch completion and download results",
    )
    parser.add_argument(
        "--processes",
        type=int,
        default=1,
        help="Number of processes to use (default: 1)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        help="Custom provider name (e.g., alibaba)",
    )
    parser.add_argument(
        "--model-id",
        type=str,
        help="Model ID to use (required for vertex AI and mistral)",
    )
    parser.add_argument(
        "--timeout-hours",
        type=int,
        help="Number of hours after which the job should expire (default: 24, max: 168)",
    )
    return parser.parse_args()


def process_batch(
    jsonl_file: str,
    method: str,
    wait: bool = False,
    processes: int = 1,
    provider: Optional[str] = None,
    model_id: Optional[str] = None,
    timeout_hours: Optional[int] = None,
):
    """Process a batch of prompts."""
    try:
        # Read configuration from environment variables
        read_config()

        method = method.lower()
        # Create batch job instance
        if method == "openai":
            if provider:
                provider = provider.lower()
                batch_job: BaseBatchJob = OpenAIBatchJob(jsonl_file, provider=provider)
            else:
                batch_job = OpenAIBatchJob(jsonl_file)
        elif method == "anthropic":
            batch_job = AnthropicBatchJob(jsonl_file)
        elif method == "vertex":
            if not model_id:
                raise ValueError("Please provide model id (--model-id) for vertex AI")
            batch_job = VertexBatchJob(jsonl_file, model_id)
        elif method == "mistral":
            if not model_id:
                raise ValueError("Please provide model id (--model-id) for mistral")
            batch_job = MistralBatchJob(jsonl_file, model_id=model_id, timeout_hours=timeout_hours)
        else:
            if provider:
                provider = provider.lower()
                batch_job = LiteLLMBatchJob(jsonl_file, provider=provider, num_processes=processes)
            else:
                batch_job = LiteLLMBatchJob(jsonl_file, num_processes=processes)

        # Send the batch
        batch_id = batch_job.send()

        # Check if batch was skipped due to existing response file
        batch_was_skipped = batch_job.is_completed and batch_id == batch_job.output_path

        if method != "litellm":
            print(f"Batch ID: {batch_id}")

            # Add logging here - AFTER the batch is submitted
            if wait:
                if batch_was_skipped:
                    logger.info("Response file already exists - no need to wait.")
                else:
                    logger.info("Waiting for batch completion...")
                    logger.info("If you're using batch mode, you can stop this command with Ctrl+C")
                    logger.info("and rerun it later with the same parameters to check if results are ready.")
            else:
                logger.info("Batch job submitted successfully. Results will be available later.")
                logger.info("You can rerun this command with the same parameters and --wait to check for results.")

        # Wait for completion if requested
        if wait and method != "litellm":
            if batch_was_skipped:
                # Response file already exists, just return the path
                print(f"Results already available at: {batch_job.output_path}")
            else:
                result_path = batch_job.wait_for_completion()
                if result_path:
                    print(f"Results saved to: {result_path}")
                else:
                    print("Batch processing failed or was cancelled.")

    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        raise


def main():
    """Command line interface for batch processing."""
    args = parse_args()

    process_batch(
        args.jsonl_file,
        args.method,
        args.wait,
        args.processes,
        args.provider,
        args.model_id,
        args.timeout_hours,
    )


if __name__ == "__main__":
    main()
