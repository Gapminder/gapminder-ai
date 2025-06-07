"""Tests for batch job utility functions."""

import pytest

from lib.pilot.batchjob.utils import post_process_response

test_cases = [
    ("Hello <think>this should be removed</think> world", "Hello  world"),
    ("Hello world", "Hello world"),
    # Assuming only one <think> block, this case might be less relevant,
    # but re.sub would handle multiple non-overlapping blocks.
    ("<think>remove this</think>Hello <think>and this</think> world", "Hello  world"),
    ("No tags here", "No tags here"),
    ("", ""),
    (None, None),
    # If only one <think> block is guaranteed, a deeply nested scenario like the removed one is not expected.
    # The simple non-greedy regex will remove the content of a single <think>...</think> block.
    ("Text with <think> tag with spaces </think>!", "Text with !"),
    ("Text with <think>multi\nline\ncontent with <other_xml_tag/>\n</think> here", "Text with  here"),
]


@pytest.mark.parametrize("input_str, expected_output", test_cases)
def test_post_process_response(input_str, expected_output):
    """Test the post_process_response function."""
    assert post_process_response(input_str) == expected_output
