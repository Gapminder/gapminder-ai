"""Main entry point for batch prompt processing with LLM providers."""
import argparse
import logging

from lib.app_singleton import AppSingleton
from lib.pilot.batchjob import anthropic as anthropic_batch
from lib.pilot.batchjob import openai as openai_batch
from lib.pilot.batchjob import vertex as vertex_batch

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)

PROVIDER_HANDLERS = {
    "openai": openai_batch,
    "anthropic": anthropic_batch,
    "vertex": vertex_batch,
    "alibaba": openai_batch,  # Share OpenAI implementation
}


def get_provider_handler(provider: str):
    """Get the appropriate batch processing module for the provider."""
    provider = provider.lower()
    if provider not in PROVIDER_HANDLERS:
        raise ValueError(
            f"Unsupported provider: {provider}. Supported providers: {list(PROVIDER_HANDLERS.keys())}"
        )
    return PROVIDER_HANDLERS[provider]


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
        handler = get_provider_handler(args.provider)
        output_path = handler.get_batch_metadata(args.jsonl_file)[1]

        # Run batch processing using provider's interface
        if args.provider in ["openai", "alibaba"]:
            batch_id = handler.send_batch(args.jsonl_file, provider=args.provider)
            if args.wait:
                result_path = handler.wait_for_completion(
                    batch_id, output_path, provider=args.provider
                )
                if result_path:
                    print(f"Results saved to: {result_path}")
            else:
                print(f"Batch ID: {batch_id}")
        else:
            # Original logic for other providers
            batch_id = handler.send_batch(args.jsonl_file)
            if args.wait:
                result_path = handler.wait_for_completion(batch_id, output_path)
                if result_path:
                    print(f"Results saved to: {result_path}")
            else:
                print(f"Batch ID: {batch_id}")

    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        raise


if __name__ == "__main__":
    main()
