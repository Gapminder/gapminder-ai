"""
Split command for the gm-eval CLI tool. Extracts failed requests from original file based on error responses.
"""

import argparse
import json
import os
from typing import Set

from lib.pilot.gm_eval.utils import logger


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command-specific arguments to the parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument("--requests", type=str, required=True, help="Path to original JSONL requests file")
    parser.add_argument(
        "--responses",
        type=str,
        help="Path to JSONL responses file containing errors (default: requests filename with '-response' suffix)",
    )
    parser.add_argument("--output", type=str, required=True, help="Path to output JSONL file for failed requests")


def _get_error_ids(responses_path: str) -> Set[str]:
    """Extract custom_ids from error responses."""
    error_ids = set()

    with open(responses_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                response = json.loads(line)
                if response.get("error") or response.get("status_code", 200) != 200:
                    custom_id = response.get("custom_id")
                    if custom_id:
                        error_ids.add(custom_id)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse response line: {line.strip()}")
                continue

    return error_ids


def handle(args: argparse.Namespace) -> int:
    """
    Handle the split command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Check input files exist
        if not os.path.isfile(args.requests):
            logger.error(f"Requests file not found: {args.requests}")
            return 1

        # Set default responses path if not provided
        if not args.responses:
            base_path = os.path.splitext(args.requests)[0]
            args.responses = f"{base_path}-response.jsonl"
            logger.info(f"Using default responses path: {args.responses}")

        if not os.path.isfile(args.responses):
            logger.error(f"Responses file not found: {args.responses}")
            return 1

        # Get custom_ids of failed responses
        error_ids = _get_error_ids(args.responses)
        if not error_ids:
            logger.info("No error responses found - nothing to split")
            return 0

        # Write matching requests to output file
        count = 0
        with open(args.output, "w", encoding="utf-8") as out_file, open(
            args.requests, "r", encoding="utf-8"
        ) as in_file:
            for line in in_file:
                try:
                    request = json.loads(line)
                    custom_id = request.get("custom_id")
                    if custom_id and custom_id in error_ids:
                        out_file.write(line)
                        count += 1
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse request line: {line.strip()}")
                    continue

        logger.info(f"Extracted {count} failed requests to {args.output}")
        return 0

    except Exception as e:
        logger.error(f"Error splitting requests: {str(e)}")
        return 1
