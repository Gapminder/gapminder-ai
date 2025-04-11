"""
Run command for the gm-eval CLI tool.

This command runs the entire workflow in sequence:
1. Download configurations from AI Eval spreadsheet
2. Generate prompts for a specific model config
3. Send the batch to a provider
4. Generate and send evaluation prompts
5. Summarize results
"""

import argparse
import os
from datetime import datetime

from lib.pilot.gm_eval.commands import download, evaluate, generate, send, summarize
from lib.pilot.gm_eval.utils import (
    ensure_directory,
    get_default_output_path,
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
        "--method",
        type=str,
        required=True,
        choices=["openai", "anthropic", "vertex", "litellm", "mistral"],
        help="LLM provider to use for processing",
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
        help="Wait for batch completion and download results at each step. Required for summarize step to run.",
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
        "--jsonl-format",
        type=str,
        choices=["openai", "vertex", "mistral"],
        default="openai",
        help="Format of JSONL output",
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
    parser.add_argument(
        "--skip-summarize",
        action="store_true",
        help="Skip summarizing results",
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
            date_str = datetime.now().strftime("%Y%m%d")
            args.output_dir = os.path.join("experiments", date_str)

        ensure_directory(args.output_dir)
        print(f"Using output directory: {args.output_dir}")

        # Step 1: Download configurations
        if not args.skip_download:
            print("\n=== Step 1: Downloading configurations ===")
            download_args = argparse.Namespace(output_dir=args.output_dir)
            result = download.handle(download_args)
            if result != 0:
                return result
        else:
            print("\n=== Step 1: Skipping download ===")

        # Step 2: Generate prompts
        if not args.skip_generate:
            print("\n=== Step 2: Generating prompts ===")
            generate_args = argparse.Namespace(
                base_path=args.output_dir,
                model_config_id=args.model_config_id,
                jsonl_format=args.jsonl_format,
            )
            result = generate.handle(generate_args)
            if result != 0:
                return result
        else:
            print("\n=== Step 2: Skipping generate ===")

        # Get prompt and response paths
        prompt_path = get_default_output_path(args.model_config_id, args.output_dir)
        response_path = get_response_path(prompt_path)

        # Step 3: Send prompts
        if not args.skip_send:
            print("\n=== Step 3: Sending prompts ===")

            # If model_id is not provided and method is mistral or vertex, try to get it from the CSV file
            model_id = args.model_id
            if model_id is None and args.method.lower() in ["mistral", "vertex"]:
                # Look up the model_id in the CSV file
                model_id = get_model_id_from_config_id(prompt_path, args.model_config_id)
                if model_id:
                    print(f"Using model_id '{model_id}' from config for {args.model_config_id}")
                else:
                    print(f"Could not find model_id for {args.model_config_id} in config file")

            # Always wait for results in the send step, regardless of the --wait flag
            # This ensures we have the response file for the evaluate step
            send_args = argparse.Namespace(
                jsonl_file=prompt_path,
                method=args.method,
                wait=True,  # Always wait for send step
                processes=args.processes,
                provider=args.provider,
                model_id=model_id,
                timeout_hours=args.timeout_hours,
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
                send=True,  # Always send when running the full workflow
                wait=args.wait,
            )
            result = evaluate.handle(evaluate_args)
            if result != 0:
                return result
        else:
            print("\n=== Step 4: Skipping evaluate ===")

        # Step 5: Summarize results
        if not args.skip_summarize and args.wait:
            print("\n=== Step 5: Summarizing results ===")
            summarize_args = argparse.Namespace(
                input_dir=args.output_dir,
                output_dir=args.output_dir,
            )
            result = summarize.handle(summarize_args)
            if result != 0:
                return result
        else:
            if args.skip_summarize:
                print("\n=== Step 5: Skipping summarize (--skip-summarize) ===")
            elif not args.wait:
                print("\n=== Step 5: Skipping summarize (--wait not specified) ===")

        print("\n=== Workflow completed successfully ===")
        return 0
    except Exception as e:
        logger.error(f"Error running workflow: {str(e)}")
        return 1
