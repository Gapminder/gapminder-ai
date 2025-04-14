"""
Main CLI entry point for the gm-eval tool.
"""

import argparse
import logging
import sys
from typing import List, Optional

from lib.app_singleton import AppSingleton
from lib.pilot.gm_eval import __version__
from lib.pilot.gm_eval.commands import download, evaluate, generate, run, send, summarize


def setup_logging(debug: bool = False) -> None:
    """
    Set up logging for the CLI.

    Args:
        debug: If True, set log level to DEBUG instead of INFO
    """
    logger = AppSingleton().get_logger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Add a console handler if not already present
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="gm-eval",
        description="Gapminder AI Evaluation CLI tool",
        epilog="For more information, see the README.md file.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Create subparsers for each command
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download configurations from AI Eval spreadsheet")
    download.add_arguments(download_parser)

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate prompts for a specific model config")
    generate.add_arguments(generate_parser)

    # Send command
    send_parser = subparsers.add_parser("send", help="Send the batch to a provider")
    send.add_arguments(send_parser)

    # Evaluate command
    evaluate_parser = subparsers.add_parser("evaluate", help="Generate and optionally send evaluation prompts")
    evaluate.add_arguments(evaluate_parser)

    # Summarize command
    summarize_parser = subparsers.add_parser("summarize", help="Create summarized output")
    summarize.add_arguments(summarize_parser)

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the entire workflow in sequence")
    run.add_arguments(run_parser)

    return parser


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        args: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse arguments
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # Set up logging with debug flag
    setup_logging(debug=parsed_args.debug if hasattr(parsed_args, "debug") else False)

    # If no command is specified, show help and exit
    if not parsed_args.command:
        parser.print_help()
        return 0

    # Dispatch to the appropriate command handler
    if parsed_args.command == "download":
        return download.handle(parsed_args)
    elif parsed_args.command == "generate":
        return generate.handle(parsed_args)
    elif parsed_args.command == "send":
        return send.handle(parsed_args)
    elif parsed_args.command == "evaluate":
        return evaluate.handle(parsed_args)
    elif parsed_args.command == "summarize":
        return summarize.handle(parsed_args)
    elif parsed_args.command == "run":
        return run.handle(parsed_args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
