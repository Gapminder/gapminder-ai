"""Main entry point for batch prompt processing with LLM providers."""

import argparse
from typing import Dict, Optional, Type

from lib.app_singleton import AppSingleton
from lib.pilot.batchjob.anthropic import AnthropicBatchJob
from lib.pilot.batchjob.base import BaseBatchJob
from lib.pilot.batchjob.litellm import LiteLLMBatchJob
from lib.pilot.batchjob.openai import OpenAIBatchJob
from lib.pilot.batchjob.vertex import VertexBatchJob

logger = AppSingleton().get_logger()

# Map provider names to their batch job classes
PROVIDER_CLASSES: Dict[str, Type] = {
    "openai": OpenAIBatchJob,
    "anthropic": AnthropicBatchJob,
    "vertex": VertexBatchJob,
    "litellm": LiteLLMBatchJob,
}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Send JSONL prompts to LLM batch APIs")
    parser.add_argument(
        "jsonl_file", type=str, help="Path to the JSONL file containing prompts"
    )
    parser.add_argument(
        "--method",
        type=str,
        default="openai",
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
        help="the model id for vertex AI",
    )
    return parser.parse_args()


def process_batch(
    jsonl_file: str,
    method: str,
    wait: bool = False,
    processes: int = 1,
    provider: Optional[str] = None,
    model_id: Optional[str] = None,
):
    """Process a batch of prompts."""
    try:
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
        else:
            if provider:
                provider = provider.lower()
                batch_job = LiteLLMBatchJob(
                    jsonl_file, provider=provider, num_processes=processes
                )
            else:
                batch_job = LiteLLMBatchJob(jsonl_file, num_processes=processes)

        # Send the batch
        batch_id = batch_job.send()
        if method != "litellm":
            print(f"Batch ID: {batch_id}")

        # Wait for completion if requested
        if wait and method != "litellm":
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
    )


if __name__ == "__main__":
    main()
