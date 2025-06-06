"""
Send command for the gm-eval CLI tool.
Enhanced with batch mode validation and auto-generate prompts functionality.
"""

import argparse
import os

from lib.pilot.generate_prompts import main as generate_prompts_main
from lib.pilot.gm_eval.utils import (
    detect_provider_from_model_id,
    get_default_output_path,
    get_jsonl_format_from_provider,
    get_model_id_from_config_id,
    get_provider_method_from_model_id,
    is_openai_compatible_provider,
    logger,
    transform_model_id,
)
from lib.pilot.send_batch_prompt import process_batch

# Provider batch mode compatibility matrix
BATCH_COMPATIBLE_PROVIDERS = {
    "openai",
    "anthropic",
    "vertex",
    "vertex_ai",
    "mistral",
    "alibaba",  # OpenAI-compatible
}


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command-specific arguments to the parser.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "--mode",
        type=str,
        choices=["batch", "litellm"],
        default="batch",
        help="Processing mode to use (default: batch)",
    )
    parser.add_argument(
        "--model-config-id",
        type=str,
        required=True,
        help="Model configuration ID to process",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Directory containing configuration files and where to save outputs",
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
        "--timeout-hours",
        type=int,
        help="Number of hours after which the job should expire (default: 24, max: 168)",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Force regeneration of prompts even if file exists",
    )


def validate_mode_compatibility(provider: str, mode: str) -> bool:
    """
    Validate if the provider supports the requested mode.

    Args:
        provider: Provider name (e.g., "openai", "deepseek")
        mode: Requested mode ("batch" or "litellm")

    Returns:
        True if compatible, False otherwise
    """
    if mode == "litellm":
        # LiteLLM mode supports all providers
        return True

    if mode == "batch":
        # Check if provider supports batch mode
        return provider in BATCH_COMPATIBLE_PROVIDERS

    return False


def get_suggested_mode(provider: str) -> str:
    """
    Get the suggested mode for a provider.

    Args:
        provider: Provider name

    Returns:
        Suggested mode ("batch" or "litellm")
    """
    if provider in BATCH_COMPATIBLE_PROVIDERS:
        return "batch"
    else:
        return "litellm"


def check_and_generate_prompts(
    model_config_id: str, output_dir: str, provider: str, mode: str, force_regenerate: bool = False
) -> str:
    """
    Check if prompts file exists and generate if needed.

    Args:
        model_config_id: Model configuration ID
        output_dir: Output directory
        provider: Provider name
        mode: Processing mode
        force_regenerate: Force regeneration even if file exists

    Returns:
        Path to the prompts file

    Raises:
        Exception: If generation fails
    """
    jsonl_file = get_default_output_path(model_config_id, output_dir)

    # Determine the correct JSONL format based on provider
    jsonl_format = get_jsonl_format_from_provider(provider)

    # Check if we need to generate prompts
    should_generate = force_regenerate or not os.path.isfile(jsonl_file)

    if should_generate:
        logger.info(f"Generating prompts for {model_config_id} in {jsonl_format} format...")

        # Check if ai_eval_sheets directory exists
        sheets_dir = os.path.join(output_dir, "ai_eval_sheets")
        if not os.path.isdir(sheets_dir):
            raise Exception(
                f"AI Eval sheets directory not found at {sheets_dir}. "
                "Please run 'gm-eval download' first or ensure you're in the correct directory."
            )

        # Generate prompts using the existing generate command
        try:
            generate_prompts_main(output_dir, model_config_id, jsonl_format, mode=mode)
            logger.info(f"Successfully generated prompts: {jsonl_file}")
        except Exception as e:
            raise Exception(f"Failed to generate prompts: {str(e)}")
    else:
        logger.info(f"Using existing prompts file: {jsonl_file}")

    return jsonl_file


def handle(args: argparse.Namespace) -> int:
    """
    Handle the send command with enhanced functionality.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Get the model ID from configuration
        jsonl_file = get_default_output_path(args.model_config_id, args.output_dir)
        full_model_id = get_model_id_from_config_id(jsonl_file, args.model_config_id, keep_provider_prefix=True)

        if not full_model_id:
            logger.error(f"Could not find model configuration for {args.model_config_id}")
            return 1

        # Detect provider from model ID
        provider, model_name = detect_provider_from_model_id(full_model_id)
        logger.info(f"Detected provider: {provider}, model: {model_name}")

        # Validate mode compatibility
        if not validate_mode_compatibility(provider, args.mode):
            suggested_mode = get_suggested_mode(provider)
            logger.error(
                f"❌ Provider '{provider}' does not support {args.mode} mode.\n"
                f"💡 Suggestion: Try using --mode {suggested_mode} instead.\n"
                f"   Example: gm-eval send --mode {suggested_mode} --model-config-id {args.model_config_id}"
            )
            if provider not in BATCH_COMPATIBLE_PROVIDERS:
                logger.info(f"ℹ️  Provider '{provider}' only supports LiteLLM mode for real-time processing.")
            return 1

        logger.info(f"✅ Mode '{args.mode}' is compatible with provider '{provider}'")

        # Auto-generate prompts if needed
        try:
            jsonl_file = check_and_generate_prompts(
                args.model_config_id, args.output_dir, provider, args.mode, args.force_regenerate
            )
        except Exception as e:
            logger.error(f"Error with prompts generation: {str(e)}")
            return 1

        # Determine method based on mode
        if args.mode == "litellm":
            method = "litellm"
        else:
            method = get_provider_method_from_model_id(full_model_id)

        logger.info(f"Using method: {method}")
        logger.info(f"Full model ID: {full_model_id}")

        # Get the appropriate model name for the selected mode
        model_id_for_batch = transform_model_id(full_model_id, mode=args.mode)
        logger.info(f"Using model name for {args.mode} mode: {model_id_for_batch}")

        # Determine provider name for OpenAI-compatible providers
        provider_name = None
        if is_openai_compatible_provider(provider):
            provider_name = provider

        # Process the batch
        logger.info(f"🚀 Starting {args.mode} processing...")
        process_batch(
            jsonl_file,
            method,
            args.wait,
            args.processes,
            provider_name,
            model_id_for_batch if method in ["mistral", "vertex"] else None,
            args.timeout_hours,
        )

        logger.info("✅ Send command completed successfully")
        return 0

    except Exception as e:
        logger.error(f"❌ Error in send command: {str(e)}")
        return 1
