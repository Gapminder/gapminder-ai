"""
Send command for the gm-eval CLI tool.
"""

import argparse
import os

from lib.pilot.gm_eval.utils import (
    extract_model_config_id_from_filename,
    get_model_id_from_config_id,
    logger,
)
from lib.pilot.send_batch_prompt import PROVIDER_CLASSES, process_batch


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command-specific arguments to the parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "jsonl_file",
        type=str,
        help="Path to the JSONL file containing prompts",
    )
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


def handle(args: argparse.Namespace) -> int:
    """
    Handle the send command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Check if the JSONL file exists
        if not os.path.isfile(args.jsonl_file):
            logger.error(f"JSONL file not found: {args.jsonl_file}")
            return 1

        # If model_id is not provided and method is mistral or vertex, try to get it from the CSV file
        model_id = args.model_id
        if model_id is None and args.method.lower() in ["mistral", "vertex"]:
            # Extract model_config_id from the filename
            model_config_id = extract_model_config_id_from_filename(args.jsonl_file)
            if model_config_id:
                # Look up the model_id in the CSV file
                model_id = get_model_id_from_config_id(args.jsonl_file, model_config_id)
                if model_id:
                    logger.info(f"Using model_id '{model_id}' from config for {model_config_id}")
                else:
                    logger.warning(f"Could not find model_id for {model_config_id} in config file")
            else:
                logger.warning(f"Could not extract model_config_id from filename: {args.jsonl_file}")

        # Process the batch
        process_batch(
            args.jsonl_file,
            args.method,
            args.wait,
            args.processes,
            args.provider,
            model_id,
            args.timeout_hours,
        )

        return 0
    except Exception as e:
        logger.error(f"Error sending batch: {str(e)}")
        return 1
