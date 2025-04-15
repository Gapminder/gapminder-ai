"""
Download command for the gm-eval CLI tool.
"""

import argparse
import os
from datetime import datetime

from lib.pilot.generate_experiment import save_sheets_as_csv
from lib.pilot.gm_eval.utils import ensure_directory, logger


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command-specific arguments to the parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Directory to save experiment configuration files",
        default=None,
    )
    parser.add_argument(
        "--filter-questions",
        type=str,
        help="Path to file containing question IDs to filter (one per line)",
        default=None,
    )
    parser.add_argument(
        "--filter-prompts",
        type=str,
        help="Path to file containing prompt variation IDs to filter (one per line)",
        default=None,
    )


def handle(args: argparse.Namespace) -> int:
    """
    Handle the download command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Create output directory if not specified, using the same pattern as run.py
        if args.output_dir is None:
            date_str = datetime.now().strftime("%Y%m%d")
            args.output_dir = os.path.join("experiments", date_str)
            print(f"Using output directory: {args.output_dir}")

        # Read filter files if provided
        question_ids = None
        if args.filter_questions:
            with open(args.filter_questions) as f:
                question_ids = {line.strip() for line in f if line.strip()}

        prompt_variation_ids = None
        if args.filter_prompts:
            with open(args.filter_prompts) as f:
                prompt_variation_ids = {line.strip() for line in f if line.strip()}

        ensure_directory(args.output_dir)
        saved_files = save_sheets_as_csv(
            args.output_dir, question_ids=question_ids, prompt_variation_ids=prompt_variation_ids
        )

        print("\nSaved the following files:")
        for sheet_name, file_path in saved_files.items():
            print(f"{sheet_name}: {file_path}")

        return 0
    except Exception as e:
        logger.error(f"Error downloading experiment configuration: {str(e)}")
        return 1
