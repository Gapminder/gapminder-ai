"""Main entry point for batch prompt processing with LLM providers."""
import argparse
import logging
from typing import Dict, Type

from lib.app_singleton import AppSingleton
from lib.pilot.batchjob.anthropic import AnthropicBatchJob
from lib.pilot.batchjob.litellm import LiteLLMBatchJob
from lib.pilot.batchjob.openai import OpenAIBatchJob
from lib.pilot.batchjob.vertex import VertexBatchJob

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)

# Map provider names to their batch job classes
PROVIDER_CLASSES: Dict[str, Type] = {
    "openai": OpenAIBatchJob,
    "anthropic": AnthropicBatchJob,
    "vertex": VertexBatchJob,
    "litellm": LiteLLMBatchJob,
}


def main():
    """Command line interface for batch processing."""
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
    args = parser.parse_args()

    try:
        method = args.method.lower()
        # Create batch job instance
        if method == "openai":
            provider = args.provider.lower()
            if provider:
                batch_job = OpenAIBatchJob(args.jsonl_file, provider=provider)
            else:
                batch_job = OpenAIBatchJob(args.jsonl_file)
        elif method in ["anthropic", "vertex"]:
            batch_job = PROVIDER_CLASSES[method](args.jsonl_file)
        else:
            provider = args.provider.lower()
            if provider:
                batch_job = LiteLLMBatchJob(
                    args.jsonl_file, provider=provider, num_processes=args.processes
                )
            else:
                batch_job = LiteLLMBatchJob(
                    args.jsonl_file, num_processes=args.processes
                )

        # Send the batch
        batch_id = batch_job.send()
        if method != "litellm":
            print(f"Batch ID: {batch_id}")

        # Wait for completion if requested
        if args.wait and method != "litellm":
            result_path = batch_job.wait_for_completion()
            if result_path:
                print(f"Results saved to: {result_path}")
            else:
                print("Batch processing failed or was cancelled.")

    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        raise


if __name__ == "__main__":
    main()
