import random
from typing import Any, List, Mapping, Optional

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM


class RandomAnswerLLM(LLM):
    """An LLM that will return from a list of answers randomly."""

    answer_list: List[str]

    @property
    def _llm_type(self) -> str:
        return "random_answer"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> str:
        if stop is not None:
            raise ValueError("stop kwargs are not permitted.")
        return random.choice(self.answer_list)

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {"answer_list": self.answer_list}
