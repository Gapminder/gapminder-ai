"""Module for sending batch prompts using LiteLLM."""

import argparse
import json
import logging
import multiprocessing as mp
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import litellm
from litellm import Cache  # type: ignore

from lib.app_singleton import AppSingleton
from lib.config import read_config

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)


def get_batch_id_and_output_path(jsonl_path: str) -> Tuple[str, str]:
    """Generate batch ID and output path from input path."""
    input_path = Path(jsonl_path)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_id = f"batch-{timestamp}"
    output_dir = input_path.parent
    output_path = str(output_dir / f"{input_path.stem}-response.jsonl")
    return batch_id, output_path


def setup_litellm_cache() -> None:
    """Configure LiteLLM Redis cache with 60 day TTL."""
    config = read_config()
    litellm.cache = Cache(  # type: ignore
        type="redis",
        host=config["REDIS_HOST"],
        port=config["REDIS_PORT"],
        ttl=60 * 24 * 60 * 60,  # 60 days in seconds
    )


def process_single_prompt(data: Dict) -> Dict:
    """Process a single prompt using LiteLLM."""
    try:
        time.sleep(0.5)  # Add delay between requests
        # add retry to request
        if "num_retries" not in data.keys():
            data["num_retries"] = 5
        response = litellm.completion(**data["body"])  # type: ignore

        # Format response like OpenAI batch API
        return {
            "custom_id": data.get("custom_id"),
            "status_code": 200,
            "content": response.choices[0].message.content,
            "error": None,
        }
    except Exception as e:
        # Handle errors like OpenAI batch API
        return {
            "custom_id": data.get("custom_id"),
            "status_code": 500,
            "content": None,
            "error": str(e),
        }


def process_batch_prompts(
    input_jsonl_path: str, num_processes: int = 1
) -> Optional[str]:
    """Process batch prompts using LiteLLM with multiprocessing."""
    logger = AppSingleton().get_logger()
    batch_id, output_path = get_batch_id_and_output_path(input_jsonl_path)

    try:
        setup_litellm_cache()

        # Read all prompts into memory
        with open(input_jsonl_path) as f:
            all_prompts = [json.loads(line) for line in f]

        # Process prompts using multiprocessing if enabled
        if num_processes > 1:
            with mp.Pool(processes=num_processes) as pool:
                results = pool.map(process_single_prompt, all_prompts)
        else:
            results = [process_single_prompt(prompt) for prompt in all_prompts]

        # Write all results to output file
        with open(output_path, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        return output_path

    except Exception as e:
        logger.error(f"Error processing batch prompts: {str(e)}")
        return None


def wait_for_batch_completion(batch_id: str, output_path: str) -> Optional[str]:
    """Wait for batch completion and return output path."""
    if os.path.exists(output_path):
        return output_path
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send JSONL prompts using LiteLLM")
    parser.add_argument(
        "jsonl_file", type=str, help="Path to the JSONL file containing prompts"
    )
    parser.add_argument(
        "--processes",
        type=int,
        default=1,
        help="Number of processes to use (default: 1)",
    )
    args = parser.parse_args()

    try:
        output_path = process_batch_prompts(args.jsonl_file, args.processes)
        if output_path:
            print(f"Results saved to: {output_path}")
        else:
            print("Failed to process batch")
    except Exception as e:
        logger.error(f"Error sending batch: {str(e)}")
        raise
