"""
Summarize command for the gm-eval CLI tool.
"""

import argparse
from pathlib import Path

from lib.pilot.gm_eval.utils import ensure_directory, logger
from lib.pilot.summarize_results import main as summarize_results_main


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command-specific arguments to the parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing response/eval JSONL files",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: same as input)",
    )


def handle(args: argparse.Namespace) -> int:
    """
    Handle the summarize command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        input_dir = Path(args.input_dir)
        output_dir = Path(args.output_dir) if args.output_dir else None

        # Check if the input directory exists
        if not input_dir.is_dir():
            logger.error(f"Input directory not found: {input_dir}")
            return 1

        # Ensure the output directory exists if specified
        if output_dir:
            ensure_directory(str(output_dir))

        # Run the summarize results main function
        summarize_results_main(input_dir, output_dir)

        return 0
    except Exception as e:
        logger.error(f"Error summarizing results: {str(e)}")
        return 1
