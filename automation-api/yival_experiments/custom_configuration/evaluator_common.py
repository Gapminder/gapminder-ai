"""common functions for the evaluators"""

import copy
import logging
import string
from typing import Any, Dict, Iterable, List, Optional, Union

import litellm
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLASSIFY_STR = """
First, write out in a step by step manner your reasoning to be sure that your
conclusion is correct.
Avoid simply stating the correct answer at the outset.
Then print only a single choice from {choices} (without quotes or punctuation)
on its own line corresponding to the correct answer.
At the end, repeat just the answer by itself on a new line.
Reasoning:
"""

MATCH_FNS = {
    "include": lambda x, y: float(x in y),
    "exact": lambda x, y: float(x == y),
    "endswith": lambda x, y: x.endswith(y),
    "starts_or_endswith": lambda x, y: x.startswith(y) or x.endswith(y),
}


def extract_choice_from_response(response: str, choice_strings: Iterable[str]) -> str:
    """Extracts the choice from the response string."""
    lines = response.strip().split("\n")
    for line in lines[::-1]:
        sanitized_line = "".join(c for c in line if c not in string.punctuation).strip()
        if not sanitized_line:
            continue
        for choice in choice_strings:
            if MATCH_FNS["exact"](sanitized_line, choice):
                return choice
    return "invalid response"


def calculate_choice_score(
    choice: str, choice_scores: Optional[Dict[str, float]] = None
) -> Optional[float]:
    """Calculates the score for the given choice."""
    if choice_scores is None:
        return None
    if choice == "invalid response":
        return min(choice_scores.values())
    return choice_scores.get(choice)


def format_template(
    template: Union[str, List[Dict[str, str]]], content: Dict[str, Any]
) -> Union[str, List[Dict[str, str]]]:
    """Formats a string or list template with the provided content."""
    if isinstance(template, str):
        try:
            return template.format(**content)
        except KeyError as e:
            raise ValueError(f"Missing key {e} in content dictionary")

    res = []
    for t in template:
        formatted_msg = copy.deepcopy(t)
        try:
            if "content" in formatted_msg:
                formatted_msg["content"] = formatted_msg["content"].format(**content)
        except KeyError as e:
            raise ValueError(f"Missing key {e} in content dictionary")
        res.append(formatted_msg)
    return res


@retry(
    wait=wait_random(min=1, max=20),
    stop=stop_after_attempt(100),
    before_sleep=before_sleep_log(logger, logging.DEBUG),
)
def completion_with_backpff(**kwargs):
    # response = openai.ChatCompletion.create(**kwargs)
    response = litellm.completion(**kwargs)
    return response


def choices_to_string(choice_strings: Iterable[str]) -> str:
    """Converts a list of choices into a formatted string."""
    return " or ".join(f'"{choice}"' for choice in choice_strings)
