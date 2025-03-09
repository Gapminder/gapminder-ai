"""LiteLLM batch processing implementation."""

import json
import multiprocessing as mp
import os
from typing import Any, Dict, Optional

import litellm
from litellm import Cache  # type: ignore

from lib.app_singleton import AppSingleton
from lib.config import read_config

from ..utils import get_output_path
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

    def __init__(
        self, jsonl_path: str, provider: Optional[str] = None, num_processes: int = 1
    ):
        """
        Initialize a batch job.

        Args:
            jsonl_path: Path to JSONL file containing prompts
            provider: API provider (e.g., "alibaba")
            num_processes: Number of processes to use for parallel processing
        """
        self.jsonl_path = jsonl_path
        self._provider = provider
        self._num_processes = num_processes
        self._output_path = get_output_path(jsonl_path)
        self._batch_id = jsonl_path

        # Check if job is already completed
        if os.path.exists(self._output_path):
            self._is_completed = True
        else:
            self._is_completed = False

    def send(self) -> str:
        """
        Process all prompts in the JSONL file.

        Unlike other batch APIs, LiteLLM processes all prompts immediately.

        Returns:
            result: the output path, or empty string if failed to send prompts
        """
        try:
            # Check if already completed
            if self._is_completed and os.path.exists(self._output_path):
                logger.info(f"Batch {self._batch_id} already completed.")
                return self._output_path

            # Process all prompts
            result = _process_batch_prompts(
                self.jsonl_path, self._output_path, self._num_processes, self._provider
            )

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
        if self._is_completed or os.path.exists(self._output_path):
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
        if provider and provider in _PROVIDER_CONFIGS:
            request_body.update(_PROVIDER_CONFIGS[provider])

        response = litellm.completion(**request_body)  # type: ignore

        # Format response like OpenAI batch API
        # TODO: add citation data if available.
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

        # Process prompts using multiprocessing if enabled
        if num_processes > 1:
            with mp.Pool(processes=num_processes) as pool:
                results = pool.starmap(
                    _process_single_prompt,
                    [(prompt, provider) for prompt in all_prompts],
                )
        else:
            results = [
                _process_single_prompt(prompt, provider) for prompt in all_prompts
            ]

        # Write all results to output file
        with open(output_path, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        return output_path

    except Exception as e:
        logger.error(f"Error processing batch prompts: {str(e)}")
        return None
