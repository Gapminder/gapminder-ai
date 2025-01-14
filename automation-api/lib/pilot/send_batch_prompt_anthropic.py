import argparse
import logging
import os
import time

from lib.app_singleton import AppSingleton
from lib.config import read_config
from lib.llm.anthropic_batch_api import (
    check_batch_job_status,
    download_batch_job_output,
    send_batch_file,
)

logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)

# Initialize config
read_config()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process batch prompts using Anthropic API"
    )
    parser.add_argument("input_jsonl", type=str, help="Path to input JSONL file")
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
        # Generate output path based on input filename
        base_name = os.path.splitext(os.path.basename(args.input_jsonl))[0]
        output_dir = os.path.dirname(args.input_jsonl)
        output_path = os.path.join(output_dir, f"{base_name}-response.jsonl")

        # Check for existing processing file
        processing_file = f"{output_path}.processing"
        if os.path.exists(processing_file):
            logger.info("Batch already being processed.")
            # Read the batch ID from the file
            with open(processing_file, "r") as f:
                batch_id = f.read().strip()
                print(f"Existing batch ID: {batch_id}")
        else:
            # Send batch
            batch_id = send_batch_file(args.input_jsonl)

            # Save batch ID to processing file
            with open(processing_file, "w") as f:
                f.write(batch_id)
            logger.info(f"Created processing file: {processing_file}")

        if args.wait:
            while True:
                status = check_batch_job_status(batch_id)
                logger.info(f"Batch status: {status}")

                if status == "ended":
                    # Download results
                    download_batch_job_output(batch_id, output_path)
                    print(f"Results saved to: {output_path}")
                    break
                else:
                    time.sleep(60)
        else:
            print(f"Batch ID: {batch_id}")

    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        raise
