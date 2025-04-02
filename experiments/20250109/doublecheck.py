"""
check those responses with errors
"""

import json
from typing import List


def load_jsonl(file_path: str) -> list[dict]:
    """Load a jsonl file into a list of dictionaries.

    Args:
        file_path: Path to the .jsonl file

    Returns:
        List of dictionaries, one per line in the file
    """
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    return data


def save_jsonl(data: list[dict], file_path: str) -> None:
    """Save a list of dictionaries to a jsonl file.

    Args:
        data: List of dictionaries to save
        file_path: Path to save the .jsonl file
    """
    with open(file_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")


def merge_successful_responses(response_files: list[str], output_file_path: str) -> None:
    """Merge multiple response files, keeping only successful responses.

    Args:
        response_files: List of paths to response jsonl files
        output_file_path: Path to save merged successful responses
    """
    successful_responses: List[dict] = []

    for file_path in response_files:
        responses = load_jsonl(file_path)
        # Filter successful responses
        successful_responses.extend(
            resp for resp in responses if resp.get("status") == "succeeded" or resp.get("result_type") == "succeeded"
        )

    # Save merged successful responses
    save_jsonl(successful_responses, output_file_path)
    print(f"Saved {len(successful_responses)} successful responses to {output_file_path}")


def filter_and_save_error_requests(request_file_path: str, response_file_path: str, output_file_path: str) -> None:
    """Filter requests with error responses and save to output file.

    Args:
        request_file_path: Path to requests jsonl file
        response_file_path: Path to responses jsonl file
        output_file_path: Path to save errored requests
    """
    requests = load_jsonl(request_file_path)
    responses = load_jsonl(response_file_path)

    # Create a dict mapping custom_id to response
    response_dict = {resp["custom_id"]: resp for resp in responses}

    # Filter requests where corresponding response has error
    error_requests = [req for req in requests if response_dict.get(req["custom_id"], {}).get("status") != "succeeded"]

    print(f"Found {len(error_requests)} requests with errors")

    # Show first error request and response for debugging
    # if error_requests:
    #     req = error_requests[0]
    #     custom_id = req['custom_id']
    #     print(f"First error request (custom_id: {custom_id}):")
    #     print("Request:", req)
    #     print("Response:", response_dict[custom_id])
    #     print("\n" + "="*80 + "\n")

    # Save error requests to output file
    save_jsonl(error_requests, output_file_path)
    print(f"Saved {len(error_requests)} error requests to {output_file_path}")


# Example usage
filter_and_save_error_requests(
    request_file_path="./mc043-question_prompts.jsonl",
    response_file_path="./mc043-question_response.part1.jsonl",
    output_file_path="mc043-question_prompts-part2.jsonl",
)

filter_and_save_error_requests(
    "./mc043-question_response-eval-prompts-claude-3-5-sonnet-20241022.jsonl",
    "./mc043-question_response-eval-prompts-claude-3-5-sonnet-20241022-response.jsonl",
    "./mc043-question_response-eval-prompts-claude-3-5-sonnet-20241022-part2.jsonl",
)

# mc043
response_files = [
    "./mc043-question_response-eval-prompts-claude-3-5-sonnet-20241022-part1-response.jsonl",
    "./mc043-question_response-eval-prompts-claude-3-5-sonnet-20241022-part2-response.jsonl",
]

merge_successful_responses(
    response_files,
    "./mc043-question_response-eval-prompts-claude-3-5-sonnet-20241022-response.jsonl",
)

# mc041
response_files = [
    "./mc041-question_response-eval-prompts-claude-3-5-sonnet-20241022-part1-response.jsonl",
    "./mc041-question_response-eval-prompts-claude-3-5-sonnet-20241022-part2-response.jsonl",
]

merge_successful_responses(
    response_files,
    "./mc041-question_response-eval-prompts-claude-3-5-sonnet-20241022-response.jsonl",
)
