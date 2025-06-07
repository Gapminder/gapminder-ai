"""LiteLLM batch processing implementation."""

import json
import multiprocessing as mp
import os
from typing import Any, Dict, Optional

import litellm
from litellm import Cache  # type: ignore

from lib.app_singleton import AppSingleton
from lib.config import read_config

from .base import BaseBatchJob

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
            result = _process_batch_prompts(self.jsonl_path, self._output_path, self._num_processes, self._provider)

            if result:
                self._is_completed = True
                logger.info(f"Batch {self._batch_id} completed successfully.")
                logger.info(f"Results saved to {result}")
                return result
            else:
                logger.error(f"Batch {self._batch_id} processing failed.")
                return ""

        except Exception as e:
            logger.error(f"Error sending batch: {str(e)}")
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


# helper functions
def _init_worker():
    """Initialize worker process to properly handle signals."""
    import signal

    signal.signal(signal.SIGINT, signal.SIG_IGN)


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
    try:
        _setup_litellm_cache()

        # Read all prompts into memory
        with open(input_jsonl_path) as f:
            all_prompts = [json.loads(line) for line in f]

        total_prompts = len(all_prompts)
        logger.info(f"Starting to process {total_prompts} prompts with {num_processes} processes")

        # Process prompts using multiprocessing if enabled
        if num_processes > 1:
            logger.info(f"Using multiprocessing with {num_processes} processes")
            try:
                with mp.Pool(processes=num_processes, initializer=_init_worker) as pool:
                    results = pool.starmap(
                        _process_single_prompt,
                        [(prompt, provider) for prompt in all_prompts],
                    )
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received. Terminating workers...")
                # Let the context manager handle cleanup
                raise
        else:
            logger.info("Processing prompts sequentially")
            results = [_process_single_prompt(prompt, provider) for prompt in all_prompts]

        # Write all results to output file
        with open(output_path, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        logger.info(f"Completed processing all {total_prompts} prompts")
        return output_path

    except KeyboardInterrupt:
        logger.info("Process was interrupted by user. Partial results may have been cached if you have redis running.")
        return None
    except Exception as e:
        logger.error(f"Error processing batch prompts: {str(e)}")
        return None
