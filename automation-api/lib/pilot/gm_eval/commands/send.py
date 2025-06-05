"""
Send command for the gm-eval CLI tool.
"""

import argparse
import os

from lib.pilot.gm_eval.utils import (
    detect_provider_from_model_id,
    get_default_output_path,
    get_model_id_from_config_id,
    get_provider_method_from_model_id,
    is_openai_compatible_provider,
    logger,
    transform_model_id,
)
from lib.pilot.send_batch_prompt import process_batch


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command-specific arguments to the parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "--mode",
        type=str,
        choices=["batch", "litellm"],
        default="batch",
        help="Processing mode to use (default: batch)",
    )
    parser.add_argument(
        "--model-config-id",
        type=str,
        required=True,
        help="Model configuration ID to process",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Directory containing configuration files and where to save outputs",
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
        "--timeout-hours",
        type=int,
        help="Number of hours after which the job should expire (default: 24, max: 168)",
    )


def handle(args: argparse.Namespace) -> int:
    """
    Handle the send command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Get the model ID from configuration
        jsonl_file = get_default_output_path(args.model_config_id, args.output_dir)
        full_model_id = get_model_id_from_config_id(jsonl_file, args.model_config_id, keep_provider_prefix=True)

        if not full_model_id:
            logger.error(f"Could not find model configuration for {args.model_config_id}")
            return 1

        # Check if the JSONL file exists - if not, we need to generate it first
        if not os.path.isfile(jsonl_file):
            logger.error(f"JSONL file not found: {jsonl_file}")
            logger.error("Please run 'gm-eval generate' first to create the prompts file")
            return 1

        # Detect provider and method from model ID
        provider, model_name = detect_provider_from_model_id(full_model_id)

        # Override method based on mode
        if args.mode == "litellm":
            method = "litellm"
        else:
            method = get_provider_method_from_model_id(full_model_id)

        logger.info(f"Detected provider: {provider}, method: {method}")
        logger.info(f"Full model ID: {full_model_id}")

        # Get the appropriate model name for the selected mode
        model_id_for_batch = transform_model_id(full_model_id, mode=args.mode)
        logger.info(f"Using model name for {args.mode} mode: {model_id_for_batch}")

        # Determine provider name for OpenAI-compatible providers
        provider_name = None
        if is_openai_compatible_provider(provider):
            provider_name = provider

        # Process the batch
        process_batch(
            jsonl_file,
            method,
            args.wait,
            args.processes,
            provider_name,
            model_id_for_batch if method in ["mistral", "vertex"] else None,
            args.timeout_hours,
        )

        return 0
    except Exception as e:
        logger.error(f"Error sending batch: {str(e)}")
        return 1
