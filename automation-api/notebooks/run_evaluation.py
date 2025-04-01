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
# +
# helper function to make setting file paths easier
import os.path as osp

def get_file(experiment_dir, filename):
    return osp.join(experiment_dir, filename)


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

experiment_dir = "../../experiments/20250306/"

# +
import lib.pilot.generate_prompts as gp

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
    {"filepath": get_file(experiment_dir, 
                          'mc049-question_prompts.jsonl'), "method": "openai"},
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

    def _is_succeeded(req):
        status_code = req.get("status_code")
        status = req.get("status")
        if status_code == 200 or status == "succeeded":
            return True
        return False

    for file_path in response_files:
        responses = load_jsonl(file_path)
        # Filter successful responses
        successful_responses.extend(
            resp
            for resp in responses
            if _is_succeeded(resp)
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

    # Create a dict mapping custom_id to response  # FIXME: too complex
    response_dict = {resp["custom_id"]: resp for resp in responses}

    def _is_succeeded(req):
        status_code = response_dict.get(req["custom_id"], {}).get("status_code")
        status = response_dict.get(req["custom_id"], {}).get("status")
        if status_code == 200 or status == "succeeded":
            return True
        return False

    # Filter requests where corresponding response has error
    error_requests = [
        req
        for req in requests
        if not _is_succeeded(req)
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
    request_file_path=get_file(experiment_dir, "mc049-question_prompts.jsonl"),
    response_file_path=get_file(experiment_dir, "mc049-question_prompts-response.jsonl"),
    output_file_path=get_file(experiment_dir, "mc049-question_prompts-part2.jsonl")
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
response_files = [
    get_file(experiment_dir, "mc049-question_prompts-response.jsonl"),
    get_file(experiment_dir, "mc049-question_prompts-part2-response.jsonl")
]
output_file = get_file(experiment_dir, "mc049-question_prompts-response.jsonl")
merge_successful_responses(response_files, output_file)

# +
# finally remove the other files
import os

files_to_remove = [
    get_file(experiment_dir, "mc049-question_prompts-part2-response.jsonl"),
    get_file(experiment_dir, "mc049-question_prompts-part2.jsonl")
]

for f in files_to_remove:
    os.remove(f)
# -




# # 4. generate evaluator prompts, and send them

from lib.pilot.generate_eval_prompts import main as generate_eval_prompts

# +
base_path = "../../experiments/20250306/"
response_file = get_file(base_path, "mc049-question_prompts-response.jsonl")

# this module will generate all eval prompts using the information in the Evaluators sheet from AI Eval Sheet. 
generate_eval_prompts(base_path, response_file, send=True)  # send=True: send after creating the jsonl. 
# -







# ## 4.1 if errors...

# +
# follow what we do in 3.1
# filter_and_save_error_requests(
#     request_file_path=get_file(experiment_dir, "mc049-question_prompts.jsonl"),
#     response_file_path=get_file(experiment_dir, "mc049-question_prompts-response.jsonl"),
#     output_file_path=get_file(experiment_dir, "mc049-question_prompts-part2.jsonl")
# )
# +
# send part2
# jsonlfile = '../../experiments/20250306/mc049-question_prompts-part2.jsonl'

# process_batch(jsonlfile, "openai", False)

# +
# merge the results after we have all 
# response_files = [
#     get_file(experiment_dir, "mc049-question_prompts-response.jsonl"),
#     get_file(experiment_dir, "mc049-question_prompts-part2-response.jsonl")
# ]
# output_file = get_file(experiment_dir, "mc049-question_prompts-response.jsonl")
# merge_successful_responses(response_files, output_file)


# +
# remove part2 files
# files_to_remove = [
#     get_file(experiment_dir, "mc049-question_prompts-response-eval-prompts-claude-3-7-sonnet-20250219-part2.jsonl"),
#     get_file(experiment_dir, "mc049-question_prompts-response-eval-prompts-claude-3-7-sonnet-20250219-part2-response.jsonl")
# ]

# for f in files_to_remove:
#     os.remove(f)
# -



# # 5. create summarized output

from lib.pilot.summarize_results import main as summarize_results
from pathlib import Path

summarize_results(Path("../../experiments/20250306"))





# +
# checking the results

# +
import polars as pl

results = pl.read_parquet("../../experiments/20250306/mc049_output.parquet")
# -

results

results.filter(pl.col("response") == "", pl.col("final_correctness") != 0)

# +
# above shows some possible issues in the evaluation: some times the response is empty but evaluators aggreed it's correct.
# TODO: handle empty responses properly.
# -





# # 6. create a parquet containing all latest responses from the models

# +
from glob import glob

def create_combined_raw_output(output_folders: List[str]) -> pl.DataFrame:
    """Create a combined DataFrame from raw parquet files in multiple folders.

    Args:
        output_folders: List of folders containing raw parquet files

    Returns:
        Combined DataFrame with all raw data
    """
    # Find all parquet files in all folders
    parquet_files = []
    for folder in output_folders:
        parquet_files.extend(glob(f"{folder}/*parquet"))

    # Read and combine all parquet files
    dfs = [pl.read_parquet(file) for file in parquet_files]

    # make sure columns are in same order.
    cols = dfs[0].columns
    dfs = [df.select(cols) for df in dfs]
    
    return pl.concat(dfs)


# -

raw_outputs = create_combined_raw_output(
    [
        "../../experiments/20240921-20241205/", 
        "../../experiments/20250109/", 
        "../../experiments/20250120/", 
        "../../experiments/20250205", 
        "../../experiments/20250208",
        "../../experiments/20250306/"
    ]
)


raw_outputs





# +
# mc039 is no longer the latest
raw_outputs = raw_outputs.filter(pl.col("model_config_id") != "mc039")

raw_outputs["question_id"].unique()

raw_outputs.write_parquet("../../experiments/latest_model_responses.parquet")
# -




# # Misc


# +
# let's check some responses from mc049 - o3 mini 
# -

o3 = raw_outputs.filter(pl.col("model_config_id") == "mc049")

o3.filter(pl.col("final_correctness") != 3)[999].to_pandas().values


