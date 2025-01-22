"""
A notebook to generate summarized results from experiments.
"""

import json
import polars as pl
from typing import Dict

# File paths - edit these to point to your data files
# REQUESTS_FILE = "./finished/mc044-question_prompts.jsonl"
RESPONSES_FILE = "./finished/mc043-question_response.jsonl"
EVAL1_FILE = "./finished/mc043-question_response-eval-prompts-gpt-4o-response.jsonl"
EVAL2_FILE = (
    "./finished/mc043-question_response-eval-prompts-gemini-1-5-pro-002-response.jsonl"
)
EVAL3_FILE = "./finished/mc043-question_response-eval-prompts-claude-3-5-sonnet-20241022-response.jsonl"  # noqa
OUTPUT_FILE = "./mc043_output.parquet"


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


responses = load_jsonl(RESPONSES_FILE)
len(responses)
responses[0]["custom_id"]

eval1 = load_jsonl(EVAL1_FILE)
eval1[0]


def get_model_config_id_from_filename(file_path: str) -> str:
    """Extract model_config_id from filename
    by splitting on '-' and taking first part
    """
    return file_path.split("/")[-1].split("-")[0]


def extract_custom_id_info(
    custom_id: str, expected_model_config_id: str
) -> Dict[str, str]:
    """Extract info from custom_id and validate model_config_id matches expected"""
    parts = custom_id.split("-")
    excludes = ["question", "q", "eval"]
    parts = [x for x in parts if x not in excludes]

    # First part should be model_config_id
    model_config_id = parts[0]
    if model_config_id != expected_model_config_id:
        raise ValueError(
            f"Model config ID mismatch: expected {expected_model_config_id}, "
            f"got {model_config_id} in custom_id {custom_id}"
        )

    if len(parts) == 3:  # question responses
        return dict(
            zip(["model_config_id", "question_id", "prompt_variation_id"], parts)
        )
    else:
        return dict(
            zip(
                ["model_config_id", "question_id", "prompt_variation_id", "metric_id"],
                parts,
            )
        )


# Get expected model_config_id from response filename
expected_model_config_id = get_model_config_id_from_filename(RESPONSES_FILE)

extract_custom_id_info(responses[0]["custom_id"], expected_model_config_id)
extract_custom_id_info(eval1[0]["custom_id"], expected_model_config_id)


# FIXME: this function is just a shortcut. We should use the data from ai_eval_sheet.
def extract_score(eval_text):
    mapping = {"A": 0, "B": 1, "C": 2, "D": 3}
    # get the last line
    last_line = eval_text.strip().split("\n")[-1]
    # be defensive, get the last word of this line, make it uppercase
    grade = last_line.split(" ")[-1].upper()
    try:
        return mapping[grade]
    except KeyError:
        print(f"ERROR getting score: \n ... {eval_text[-30:]}")
        return -1


eval1[0]["content"]
extract_score(eval1[0]["content"])


eval2 = load_jsonl(EVAL2_FILE)
eval2[0]["content"]
extract_score(eval2[0]["content"])

eval3 = load_jsonl(EVAL3_FILE)
eval3[0]["content"]
extract_score(eval3[0]["content"])

_ = [extract_score(x["content"]) for x in eval3]


def process_responses(
    responses: list[dict], expected_model_config_id: str
) -> list[dict]:
    """Process response records to extract key fields"""
    processed = []
    for resp in responses:
        info = extract_custom_id_info(resp["custom_id"], expected_model_config_id)
        processed.append(
            {
                "model_config_id": info["model_config_id"],
                "question_id": info["question_id"],
                "prompt_variation_id": info["prompt_variation_id"],
                "response": resp["content"],
            }
        )
    return processed


def process_evals(
    evals: list[dict], eval_name: str, expected_model_config_id: str
) -> list[dict]:
    """Process evaluation records to extract key fields and scores"""
    processed = []
    for eval in evals:
        info = extract_custom_id_info(eval["custom_id"], expected_model_config_id)
        processed.append(
            {
                "model_config_id": info["model_config_id"],
                "question_id": info["question_id"],
                "prompt_variation_id": info["prompt_variation_id"],
                "metric_id": info["metric_id"],
                f"{eval_name}_score": extract_score(eval["content"]),
            }
        )
    return processed


def pivot_eval_df(df: pl.DataFrame, eval_name: str) -> pl.DataFrame:
    """Pivot evaluation dataframe to have metric_id values as columns"""
    pivoted = df.pivot(
        values=f"{eval_name}_score",
        index=["model_config_id", "question_id", "prompt_variation_id"],
        on="metric_id",
        aggregate_function="first",
    )

    # Rename columns to include evaluator name
    new_columns = []
    for col in pivoted.columns:
        if col in ["model_config_id", "question_id", "prompt_variation_id"]:
            new_columns.append(col)
        else:
            new_columns.append(f"{eval_name}_{col}")

    return pivoted.rename(dict(zip(pivoted.columns, new_columns)))


def create_combined_df(responses: list[dict], *evals: list[dict]) -> pl.DataFrame:
    """Create a combined dataframe from responses and evaluations"""
    # Get expected model_config_id from response filename
    expected_model_config_id = get_model_config_id_from_filename(RESPONSES_FILE)

    # Process all data
    resp_data = process_responses(responses, expected_model_config_id)
    eval_names = ["gpt4", "claude", "gemini"]
    eval_data = [
        process_evals(e, name, expected_model_config_id)
        for e, name in zip(evals, eval_names)
    ]

    # Create dataframes
    resp_df = pl.DataFrame(resp_data)
    eval_dfs = [pl.DataFrame(e) for e in eval_data]

    # Pivot each evaluation dataframe
    pivoted_dfs = [pivot_eval_df(df, name) for df, name in zip(eval_dfs, eval_names)]

    # Join all dataframes
    combined_df = resp_df
    for df in pivoted_dfs:
        combined_df = combined_df.join(
            df, on=["model_config_id", "question_id", "prompt_variation_id"], how="left"
        )

    # Fill null evaluation scores with -1
    # And fille null response with n/a
    # Identify evaluation columns by excluding the joining columns
    # and response column
    joining_columns = [
        "model_config_id",
        "question_id",
        "prompt_variation_id",
        "response",
    ]
    eval_columns = [col for col in combined_df.columns if col not in joining_columns]

    combined_df = combined_df.with_columns(
        [pl.col(col).fill_null(-1) for col in eval_columns]
    ).with_columns(pl.col("response").fill_null("NOT_ANSWERED"))

    return combined_df


def calculate_final_score(row: pl.Series) -> int:
    """Calculate final correctness score based on majority agreement"""
    scores = [
        row["gpt4_correctness"],
        row["claude_correctness"],
        row["gemini_correctness"],
    ]

    # Count occurrences of each score
    score_counts: Dict[int, int] = {}
    for score in scores:
        score_counts[score] = score_counts.get(score, 0) + 1

    # Find the score with highest count
    max_count = max(score_counts.values())
    if max_count >= 2:
        # Return the score that appears at least twice
        return next(
            score for score, count in score_counts.items() if count == max_count
        )
    else:
        # All scores different
        return 0


# Create the combined dataframe
responses = load_jsonl(RESPONSES_FILE)
eval1 = load_jsonl(EVAL1_FILE)
eval2 = load_jsonl(EVAL2_FILE)
eval3 = load_jsonl(EVAL3_FILE)
combined_df = create_combined_df(responses, eval1, eval2, eval3)

# check
combined_df.filter(pl.col("response") == "NOT_ANSWERED")


# Add final correctness score column
combined_df = combined_df.with_columns(
    final_correctness=pl.struct(
        ["gpt4_correctness", "claude_correctness", "gemini_correctness"]
    ).map_elements(calculate_final_score, return_dtype=pl.Int32)
)

# check
combined_df.filter(pl.col("final_correctness") == -1)

# Show the final dataframe
combined_df
# combined_df.write_csv(OUTPUT_FILE.replace('.parquet', '.csv'))
combined_df.write_parquet(OUTPUT_FILE)
