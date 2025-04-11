"""
Generate command for the gm-eval CLI tool.
"""

import argparse
import os

from lib.pilot.generate_prompts import JsonlFormat
from lib.pilot.generate_prompts import main as generate_prompts_main
from lib.pilot.gm_eval.utils import ensure_directory, logger


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command-specific arguments to the parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",
        help="Base directory containing ai_eval_sheets folder",
    )
    parser.add_argument(
        "--model-config-id",
        type=str,
        required=True,
        help="ID of the model configuration to use",
    )
    parser.add_argument(
        "--jsonl-format",
        type=str,
        choices=[f.value for f in JsonlFormat],
        default=JsonlFormat.OPENAI.value,
        help="Format of JSONL output (openai, vertex, or mistral)",
    )


def handle(args: argparse.Namespace) -> int:
    """
    Handle the generate command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        base_path = args.base_path
        model_config_id = args.model_config_id
        jsonl_format = args.jsonl_format

        # Ensure the base path exists
        ensure_directory(base_path)

        # Check if ai_eval_sheets directory exists
        sheets_dir = os.path.join(base_path, "ai_eval_sheets")
        if not os.path.isdir(sheets_dir):
            logger.error(f"AI Eval sheets directory not found at {sheets_dir}")
            logger.error("Please run the 'download' command first")
            return 1

        # Run the generate prompts main function
        generate_prompts_main(base_path, model_config_id, jsonl_format)

        return 0
    except Exception as e:
        logger.error(f"Error generating prompts: {str(e)}")
        return 1
