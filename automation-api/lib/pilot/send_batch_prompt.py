"""Main entry point for batch prompt processing with LLM providers."""
import argparse
import logging
from typing import Dict, Type

from lib.app_singleton import AppSingleton
from lib.pilot.batchjob.anthropic import AnthropicBatchJob
from lib.pilot.batchjob.openai import OpenAIBatchJob
from lib.pilot.batchjob.vertex import VertexBatchJob

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)

# Map provider names to their batch job classes
PROVIDER_CLASSES: Dict[str, Type] = {
    "openai": OpenAIBatchJob,
    "anthropic": AnthropicBatchJob,
    "vertex": VertexBatchJob,
    "alibaba": OpenAIBatchJob,  # Share OpenAI implementation
}


def main():
    """Command line interface for batch processing."""
    parser = argparse.ArgumentParser(description="Send JSONL prompts to LLM batch APIs")
    parser.add_argument(
        "jsonl_file", type=str, help="Path to the JSONL file containing prompts"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        choices=["openai", "anthropic", "vertex", "alibaba"],
        help="LLM provider to use for processing",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for batch completion and download results",
    )

    args = parser.parse_args()

    try:
        # Get the appropriate batch job class
        BatchJobClass = PROVIDER_CLASSES[args.provider.lower()]

        # Create batch job instance
        if args.provider.lower() in ["openai", "alibaba"]:
            # OpenAI and Alibaba need provider parameter
            batch_job = BatchJobClass(args.jsonl_file, provider=args.provider.lower())
        else:
            # Other providers don't need provider parameter
            batch_job = BatchJobClass(args.jsonl_file)

        # Send the batch
        batch_id = batch_job.send()
        print(f"Batch ID: {batch_id}")

        # Wait for completion if requested
        if args.wait:
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
