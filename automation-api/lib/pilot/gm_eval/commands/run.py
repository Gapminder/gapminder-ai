"""
Run command for the gm-eval CLI tool.

This command runs the experiment workflow in sequence:
1. Download configurations from AI Eval spreadsheet
2. Generate prompts for a specific model config
3. Send the batch to a provider
4. Generate and send evaluation prompts

Use 'gm-eval summarize' command separately when all experiments are complete.
"""

import argparse
import os
from datetime import datetime

from lib.pilot.gm_eval.commands import download, evaluate, generate, send
from lib.pilot.gm_eval.utils import (
    detect_provider_from_model_id,
    ensure_directory,
    get_default_output_path,
    get_jsonl_format_from_provider,
    get_model_id_from_config_id,
    get_response_path,
    logger,
)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command-specific arguments to the parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "--model-config-id",
        type=str,
        required=True,
        help="ID of the model configuration to use",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["batch", "litellm"],
        default="batch",
        help="Processing mode to use (default: batch)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save experiment files (default: None)",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for batch completion and download results at each step (applies to batch mode only).",
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
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading configurations (use existing ones)",
    )
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Skip generating prompts (use existing ones)",
    )
    parser.add_argument(
        "--skip-send",
        action="store_true",
        help="Skip sending prompts (use existing responses)",
    )
    parser.add_argument(
        "--skip-evaluate",
        action="store_true",
        help="Skip generating and sending evaluation prompts",
    )


def handle(args: argparse.Namespace) -> int:
    """
    Handle the run command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Create output directory if not specified
        if args.output_dir is None:
            date_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            args.output_dir = os.path.join("./", date_str)

        ensure_directory(args.output_dir)
        print(f"Using output directory: {args.output_dir}")

        # Step 1: Download configurations
        if not args.skip_download:
            print("\n=== Step 1: Downloading configurations ===")
            download_args = argparse.Namespace(output_dir=args.output_dir, filter_questions=None, filter_prompts=None)
            result = download.handle(download_args)
            if result != 0:
                return result
        else:
            print("\n=== Step 1: Skipping download ===")

        # Get model configuration and detect provider/format
        prompt_path = get_default_output_path(args.model_config_id, args.output_dir)
        full_model_id = get_model_id_from_config_id(prompt_path, args.model_config_id, keep_provider_prefix=True)

        if not full_model_id:
            logger.error(f"Could not find model configuration for {args.model_config_id}")
            return 1

        provider, model_name = detect_provider_from_model_id(full_model_id)

        # Override JSONL format for litellm mode
        if args.mode == "litellm":
            jsonl_format = "openai"
        else:
            jsonl_format = get_jsonl_format_from_provider(provider)

        print(f"Detected provider: {provider}, format: {jsonl_format}")

        # Step 2: Generate prompts
        if not args.skip_generate:
            print("\n=== Step 2: Generating prompts ===")
            generate_args = argparse.Namespace(
                base_path=args.output_dir,
                model_config_id=args.model_config_id,
                jsonl_format=jsonl_format,
            )
            result = generate.handle(generate_args)
            if result != 0:
                return result
        else:
            print("\n=== Step 2: Skipping generate ===")

        # Get response path
        response_path = get_response_path(prompt_path)

        # Step 3: Send prompts
        if not args.skip_send:
            print("\n=== Step 3: Sending prompts ===")

            # Use the new mode-based send command
            send_args = argparse.Namespace(
                mode=args.mode,
                model_config_id=args.model_config_id,
                output_dir=args.output_dir,
                wait=True,  # Always wait for send step
                processes=args.processes,
                timeout_hours=args.timeout_hours,
                force_regenerate=False,  # Default to not force regenerate
            )
            result = send.handle(send_args)
            if result != 0:
                return result
        else:
            print("\n=== Step 3: Skipping send ===")

        # Step 4: Generate and send evaluation prompts
        if not args.skip_evaluate:
            print("\n=== Step 4: Generating and sending evaluation prompts ===")
            evaluate_args = argparse.Namespace(
                response_file=response_path,
                base_path=args.output_dir,
                mode=args.mode,
                send=True,  # Always send when running the full workflow
                wait=args.wait,
            )
            result = evaluate.handle(evaluate_args)
            if result != 0:
                return result
        else:
            print("\n=== Step 4: Skipping evaluate ===")

        print("\n=== Experiment completed successfully ===")
        print("\nTo summarize results after all experiments are complete, run:")
        print(f"gm-eval summarize --input-dir {args.output_dir}")
        return 0
    except Exception as e:
        logger.error(f"Error running workflow: {str(e)}")
        return 1
