"""
Merge command for the gm-eval CLI tool. Combines multiple response files, with later files overriding earlier ones.
"""

import argparse
import json
import os
from typing import Dict

from lib.pilot.gm_eval.utils import logger


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command-specific arguments to the parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "files", type=str, nargs="+", help="List of JSONL files to merge (later files override earlier ones)"
    )
    parser.add_argument("--output", type=str, required=True, help="Path to output JSONL file for merged responses")


def load_all_responses(file_paths: list[str]) -> Dict[str, str]:
    """Load all responses into a dictionary indexed by custom_id."""
    merged_data = {}
    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    custom_id = data.get("custom_id")
                    if custom_id:
                        merged_data[custom_id] = line.strip()
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse line in {file_path}: {line.strip()}")
                    continue
    return merged_data


def handle(args: argparse.Namespace) -> int:
    """
    Handle the merge command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Check input files exist
        for file_path in args.files:
            if not os.path.isfile(file_path):
                logger.error(f"Input file not found: {file_path}")
                return 1

        # Load all responses (later files override earlier ones)
        merged_data = load_all_responses(args.files)
        if not merged_data:
            logger.warning("No valid responses found in any input files")

        # Write merged output
        with open(args.output, "w", encoding="utf-8") as out_file:
            for line in merged_data.values():
                out_file.write(line + "\n")

        logger.info(f"Merged {len(merged_data)} responses from {len(args.files)} files into {args.output}")
        return 0

    except Exception as e:
        logger.error(f"Error merging responses: {str(e)}")
        return 1
