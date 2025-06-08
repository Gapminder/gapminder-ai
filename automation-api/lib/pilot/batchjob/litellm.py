"""LiteLLM batch processing implementation."""

import json
import multiprocessing as mp
import os
from typing import Any, Dict, List, Optional

import litellm
from litellm import Cache  # type: ignore

from lib.app_singleton import AppSingleton
from lib.config import read_config

from .base import BaseBatchJob
from .utils import post_process_response

logger = AppSingleton().get_logger()
config = read_config()

# Provider-specific configurations
_PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = {
    "alibaba": {
        "api_key": config.get("DASHSCOPE_API_KEY", ""),
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
}


class LiteLLMBatchJob(BaseBatchJob):
    """Class for managing LiteLLM batch jobs."""

    def __init__(self, jsonl_path: str, provider: Optional[str] = None, num_processes: int = 1):
        """
        Initialize a batch job.

        Args:
            jsonl_path: Path to JSONL file containing prompts
            provider: API provider (e.g., "alibaba")
            num_processes: Number of processes to use for parallel processing
        """
        super().__init__(jsonl_path)
        self._provider = provider
        self._num_processes = num_processes
        self._batch_id = jsonl_path

    def send(self) -> str:
        """
        Process all prompts in the JSONL file.

        Unlike other batch APIs, LiteLLM processes all prompts immediately.

        Returns:
            result: the output path, or empty string if failed to send prompts
        """
        try:
            # Check if response file already exists
            if self.should_skip_processing():
                return self._output_path

            # Process all prompts
            result_path = _process_batch_prompts(
                self.jsonl_path, self._output_path, self._num_processes, self._provider
            )

            if result_path:  # Check if a valid path was returned
                self._is_completed = True
                logger.info(f"Batch {self._batch_id} completed successfully.")
                logger.info(f"Results saved to {result_path}")
                return result_path
            else:
                # This case now covers both processing failure and interruption before completion
                logger.error(f"Batch {self._batch_id} processing failed or was interrupted before completion.")
                return ""
        except KeyboardInterrupt:
            logger.warning(f"Batch {self._batch_id} sending was interrupted by user (Ctrl+C).")
            # _process_batch_prompts is expected to handle its own cleanup of workers.
            # If _process_batch_prompts created a partial file and didn't clean it,
            # cleanup logic could be added here, but the proposed _process_batch_prompts
            # aims to avoid writing partial files on interrupt.
            raise  # Re-raise to allow application to terminate
        except Exception as e:
            logger.error(f"Error sending batch: {str(e)}")
            # If _process_batch_prompts terminated workers due to an error and re-raised,
            # it would be caught here.
            raise

    def check_status(self) -> str:
        """
        Check status of the batch job.

        For LiteLLM, this is either "completed" or unknown since processing
        happens synchronously in the send() method.

        Returns:
            status: Job status string ("completed" or "n/a")
        """
        if self.is_completed or os.path.exists(self._output_path):
            return "completed"
        else:
            return "n/a"

    def download_results(self) -> Optional[str]:
        """ """
        raise NotImplementedError("download_results for litellm is not available.")

    def wait_for_completion(self, poll_interval: int = 5) -> Optional[str]:
        """ """
        raise NotImplementedError("wait_for_completion for litellm is not available.")

    @property
    def output_path(self) -> str:
        """Get the output file path."""
        return self._output_path


def _setup_litellm_cache() -> None:
    """Configure LiteLLM Redis cache with 60 day TTL."""
    if "REDIS_HOST" in config and "REDIS_PORT" in config:
        litellm.cache = Cache(  # type: ignore
            type="redis",
            host=config["REDIS_HOST"],
            port=config["REDIS_PORT"],
            ttl=60 * 24 * 60 * 60,  # 60 days in seconds
        )


def _process_single_prompt(data: Dict, provider: Optional[str] = None) -> Dict:
    """Process a single prompt using LiteLLM."""
    try:
        # Add retry to request if not already specified
        if "num_retries" not in data.keys():
            data["num_retries"] = 10

        # Merge provider config with request body if provider exists
        request_body = data["body"].copy()
        if provider:
            if provider in _PROVIDER_CONFIGS:
                request_body.update(_PROVIDER_CONFIGS[provider])
            else:
                logger.error("provider not found: %s", provider)
                raise ValueError("provider not found")

        response = litellm.completion(**request_body)  # type: ignore
        content = response.choices[0].message.content

        # Post-process the response content
        content = post_process_response(content)

        try:  # when citations available, add them to the content.
            citation_str = "\n".join(f"[{n+1}]: {link}" for n, link in enumerate(response.citations))
            content = f"{content}\n\nCitations:\n\n{citation_str}"
        except AttributeError:
            pass

        # Format response like OpenAI batch API
        result = {
            "custom_id": data.get("custom_id"),
            "status_code": 200,
            "content": content,
            "error": None,
        }

        # Log that the prompt has been processed
        logger.info(f"Prompt with custom_id '{data.get('custom_id')}' has been processed")

        return result
    except Exception as e:
        # Handle errors like OpenAI batch API
        result = {
            "custom_id": data.get("custom_id"),
            "status_code": 500,
            "content": None,
            "error": str(e),
        }

        # Log that the prompt processing failed
        logger.error(f"Failed to process prompt with custom_id '{data.get('custom_id')}': {str(e)}")

        return result


def _process_batch_prompts(
    input_jsonl_path: str,
    output_path: str,
    num_processes: int = 1,
    provider: Optional[str] = None,
) -> Optional[str]:
    """Process batch prompts using LiteLLM with multiprocessing."""

    _setup_litellm_cache()

    with open(input_jsonl_path) as f:
        all_prompts = [json.loads(line) for line in f]

    total_prompts = len(all_prompts)
    logger.info(f"Starting to process {total_prompts} prompts with {num_processes} processes")

    processed_results: List[Dict] = []  # Initialize to an empty list

    if num_processes > 1:
        logger.info(f"Using multiprocessing with {num_processes} processes")
        pool = mp.Pool(processes=num_processes)
        try:
            # Use starmap_async for non-blocking behavior in the main thread
            async_task = pool.starmap_async(
                _process_single_prompt,
                [(prompt, provider) for prompt in all_prompts],
            )

            # Wait for tasks to complete, checking periodically to allow interrupts
            logger.info("Tasks submitted to pool. Waiting for completion... (Press Ctrl+C to interrupt)")
            while not async_task.ready():
                try:
                    # get() with a timeout allows KeyboardInterrupt to be caught by the main thread
                    async_task.get(timeout=1)  # Check every 1 second
                except mp.TimeoutError:
                    # This is expected if tasks are still running
                    continue
                # If KeyboardInterrupt occurs during get(), it will propagate to the outer handler

            processed_results = async_task.get()  # Retrieve all results once ready

            pool.close()  # No more tasks will be submitted
            pool.join()  # Wait for all worker processes to complete their current tasks and exit
            logger.info("All multiprocessing tasks completed and workers joined.")
        except KeyboardInterrupt:
            logger.warning("Keyboard interrupt received by main process. Terminating worker processes...")
            pool.terminate()  # Send SIGTERM to worker processes
            pool.join()  # Wait for worker processes to terminate
            logger.info("Worker processes terminated due to keyboard interrupt.")
            # processed_results will remain as they were (likely empty or incomplete)
            # Re-raising KeyboardInterrupt is crucial to stop the script.
            raise
        except Exception as e:
            logger.error(f"An error occurred during multiprocessing: {str(e)}")
            pool.terminate()
            pool.join()
            logger.info("Worker processes terminated due to an error.")
            # Re-raise the caught exception
            raise
    else:  # Sequential processing
        logger.info("Processing prompts sequentially")
        try:
            for prompt_data in all_prompts:
                # Process one by one to allow interruption between prompts
                if not isinstance(processed_results, list):  # Should not happen with init
                    processed_results = []
                processed_results.append(_process_single_prompt(prompt_data, provider))
            logger.info("Sequential processing completed.")
        except KeyboardInterrupt:
            logger.warning("Keyboard interrupt received during sequential processing.")
            # processed_results will contain items processed so far.
            # Re-raise to stop the script.
            raise
        # Other exceptions in sequential mode will propagate naturally.

    # Write results to output file only if processing wasn't interrupted before completion
    # and results were actually gathered.
    if processed_results:  # Check if list is not empty
        try:
            with open(output_path, "w") as f:
                for result_item in processed_results:
                    f.write(json.dumps(result_item) + "\n")
            logger.info(f"Successfully wrote {len(processed_results)} results to {output_path}")
            return output_path
        except IOError as e:
            logger.error(f"Failed to write results to {output_path}: {e}")
            return None  # Indicate failure
    else:
        logger.warning(
            "No results were processed or an interruption occurred before results could be gathered. Output file not written."
        )
        return None
