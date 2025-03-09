# Makes edits in the included files available without restarting the kernel
# %reload_ext autoreload
# %autoreload 2

# +
# set up logger
import logging
from lib.app_singleton import AppSingleton

logger = AppSingleton().get_logger()
# change to logging.DEBUG to see DEBUG message
logger.setLevel(logging.INFO)
# -



# # 1. download ai eval spreadsheet to a local folder

# +
from lib.pilot.generate_experiment import save_sheets_as_csv

experiment_top_level_dir = "../../experiments/"

saved = save_sheets_as_csv(experiment_top_level_dir)

print("\nSaved the following files:")
for sheet_name, file_path in saved.items():
    print(f"{sheet_name}: {file_path}")
# -

# # 2. Generate experiment data for model(s)

# +
import lib.pilot.generate_prompts as gp

experiment_dir = "../../experiments/20250306/"

# TODO: maybe add a function to easily display all model name and model config id. 
# Make it easy to find the model config id

# 
gp.main(experiment_dir, model_config_id="mc049", jsonl_format="openai")
# add more if there are more models to do
# jsonl_format should be either openai or vertex
# gp.main(experiment_dir, "mc050", "vertex")
# -
# # 3. Send prompts and get back results

from lib.pilot.send_batch_prompt import process_batch

# +
jsonl_files = [
    {"filepath": '../../experiments/20250306/mc049-question_prompts.jsonl', "method": "openai"},
    # add more here if there are other jsonl files...
]

# first, just send all batches
for f in jsonl_files:
    process_batch(f["filepath"], f["method"], wait=False)
# -


# wait until all batch finished and download results
for f in jsonl_files:
    process_batch(f["filepath"], f["method"], wait=True)

# ## 3.1 Check if there are questions the chatbot failed to answer
#
# API issues, or insufficient fund etc would make the chatbot fail to answer some questions. 

# TODO: move utility functions to a module.
import json
from typing import List


# +
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


def merge_successful_responses(
    response_files: list[str], output_file_path: str
) -> None:
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
            resp
            for resp in responses
            if resp.get("status_code") == 200
        )

    # Save merged successful responses
    save_jsonl(successful_responses, output_file_path)
    print(
        f"Saved {len(successful_responses)} successful responses to {output_file_path}"
    )


def filter_and_save_error_requests(
    request_file_path: str, response_file_path: str, output_file_path: str
) -> None:
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
    error_requests = [
        req
        for req in requests
        if response_dict.get(req["custom_id"], {}).get("status_code") != 200
    ]

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


# -

filter_and_save_error_requests(
    request_file_path="../../experiments/20250306/mc049-question_prompts.jsonl",
    response_file_path="../../experiments/20250306/mc049-question_prompts-response.jsonl",
    output_file_path="../../experiments/20250306/mc049-question_prompts-part2.jsonl"
)

# +
# after step 3.2, we can test it again
# filter_and_save_error_requests(
#     request_file_path="../../experiments/20250306/mc049-question_prompts-part2.jsonl",
#     response_file_path="../../experiments/20250306/mc049-question_prompts-part2-response.jsonl",
#     output_file_path="../../experiments/20250306/mc049-question_prompts-part3.jsonl"
# )
# -



# ### if necessary. send the other prompts again

# +
jsonlfile = '../../experiments/20250306/mc049-question_prompts-part2.jsonl'

process_batch(jsonlfile, "openai", False)
# -


process_batch(jsonlfile, "openai", True)

# merge the results after we have all 
response_files = ["../../experiments/20250306/mc049-question_prompts-response.jsonl", "../../experiments/20250306/mc049-question_prompts-part2-response.jsonl"]
output_file = "../../experiments/20250306/mc049-question_prompts-response.jsonl"
merge_successful_responses(response_files, output_file)






# # 4. generate evaluator prompts, and send them

import lib.pilot.generate_eval_prompts as gep

# +
base_path = "../../experiments/20250306/"
response_file = "../../experiments/20250306/mc049-question_prompts-response.jsonl"

gep.main(base_path, response_file, send=True)
# -







# ## 4.1 if errors...

# +
# follow what we do in 3.1
# -



# # 5. create summarized output






