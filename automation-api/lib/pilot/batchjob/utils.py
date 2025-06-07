"""Utility functions for batch job processing."""

import re
from typing import Optional


def post_process_response(content: Optional[str]) -> Optional[str]:
    """Apply all post-processing steps to LLM responses."""
    if content:
        # Remove thinking tags
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    return content
