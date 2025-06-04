"""
Evaluate command for the gm-eval CLI tool.
"""

import argparse
import os

from lib.pilot.generate_eval_prompts import main as generate_eval_prompts_main
from lib.pilot.gm_eval.utils import logger


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command-specific arguments to the parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "response_file",
        type=str,
        help="Path to response JSONL file",
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",
        help="Base directory containing ai_eval_sheets folder",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["batch", "litellm"],
        default="batch",
        help="Processing mode to use (default: batch)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send generated prompts immediately after creation",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for eval results",
    )


def handle(args: argparse.Namespace) -> int:
    """
    Handle the evaluate command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Check if the response file exists
        if not os.path.isfile(args.response_file):
            logger.error(f"Response file not found: {args.response_file}")
            return 1

        # Check if ai_eval_sheets directory exists
        sheets_dir = os.path.join(args.base_path, "ai_eval_sheets")
        if not os.path.isdir(sheets_dir):
            logger.error(f"AI Eval sheets directory not found at {sheets_dir}")
            logger.error("Please run the 'download' command first")
            return 1

        # Run the generate eval prompts main function
        # Note: The mode parameter is available but not currently used by generate_eval_prompts_main
        # This maintains compatibility while allowing future mode-specific evaluation logic
        generate_eval_prompts_main(args.base_path, args.response_file, args.send, args.wait)

        return 0
    except Exception as e:
        logger.error(f"Error generating evaluation prompts: {str(e)}")
        return 1
