import argparse
import json
import logging
import os
import re
import time
from typing import List

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from lib.app_singleton import AppSingleton
from lib.config import read_config

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)

# Initialize Anthropic client
read_config()
client = anthropic.Anthropic()


def read_jsonl_requests(jsonl_path: str) -> List[dict]:
    """Read JSONL file and return list of request objects."""
    requests = []
    with open(jsonl_path, "r") as f:
        for line in f:
            requests.append(json.loads(line))
    return requests


def convert_to_anthropic_requests(requests: List[dict]) -> List[Request]:
    """Convert OpenAI format requests to Anthropic Request objects."""
    anthropic_requests = []
    for req in requests:
        # Extract the message content and parameters from OpenAI format
        messages = req["body"]["messages"]
        content = messages[0]["content"]  # Assuming single user message
        model = req["body"]["model"]
        max_tokens = req["body"].get("max_tokens", 2048)
        temperature = req["body"].get("temperature", 0.01)

        # Create Anthropic Request object
        anthropic_requests.append(
            Request(
                custom_id=req["custom_id"],
                params=MessageCreateParamsNonStreaming(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": content}],
                ),
            )
        )
    return anthropic_requests


def process_batch(requests: List[Request]) -> str:
    """Send batch requests to Anthropic API."""
    batch = client.messages.batches.create(requests=requests)
    logger.info(f"Created batch with ID: {batch.id}")
    return batch.id


def get_batch_status(batch_id: str) -> str:
    """Get the current status of a batch."""
    batch = client.messages.batches.retrieve(batch_id)
    return batch.processing_status


def save_batch_results(batch_id: str, output_path: str) -> None:
    """Save batch results to JSONL file."""
    with open(output_path, "w") as f:
        for result in client.messages.batches.results(batch_id):
            result_dict = {
                "custom_id": result.custom_id,
                "result_type": result.result.type,
            }

            if result.result.type == "succeeded":
                result_dict["content"] = result.result.message.content[0].text
                result_dict["error"] = None
            elif result.result.type == "errored":
                result_dict["content"] = None
                result_dict["error"] = {
                    "type": result.result.error.type,
                    "message": str(result.result.error),
                }

            json_line = json.dumps(result_dict, ensure_ascii=False)
            f.write(f"{json_line}\n")

    logger.info(f"Saved batch results to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process batch prompts using Anthropic API"
    )
    parser.add_argument(
        "--input-jsonl", type=str, required=True, help="Path to input JSONL file"
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",
        help="Base directory containing ai_eval_sheets folder",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for batch completion and download results",
    )

    args = parser.parse_args()

    try:
        # Extract model_config_id from input filename first
        base_name = os.path.basename(args.input_jsonl)
        match = re.match(r"^(.*?)-question_prompts\.jsonl$", base_name)
        if not match:
            raise ValueError(
                f"Input filename {base_name} doesn't match expected pattern"
            )
        model_config_id = match.group(1)

        # Generate output path
        output_dir = os.path.dirname(args.input_jsonl)
        output_path = os.path.join(
            output_dir, f"{model_config_id}-question_response.jsonl"
        )

        # Check for existing processing file
        processing_file = f"{output_path}.processing"
        if os.path.exists(processing_file):
            logger.info("Batch already being processed.")
            # Read the batch ID from the file
            with open(processing_file, "r") as f:
                batch_id = f.read().strip()
                print(f"Existing batch ID: {batch_id}")
        else:
            # Read and convert requests
            openai_requests = read_jsonl_requests(args.input_jsonl)
            anthropic_requests = convert_to_anthropic_requests(openai_requests)

            # Process batch
            batch_id = process_batch(anthropic_requests)

            # Save batch ID to processing file
            with open(processing_file, "w") as f:
                f.write(batch_id)
            logger.info(f"Created processing file: {processing_file}")

        if args.wait:
            while True:
                status = get_batch_status(batch_id)
                logger.info(f"Batch status: {status}")

                if status == "ended":
                    save_batch_results(batch_id, output_path)
                    print(f"Results saved to: {output_path}")
                    break
                else:
                    time.sleep(60)
        else:
            print(f"Batch ID: {batch_id}")

    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        raise
